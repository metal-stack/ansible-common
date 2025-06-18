#!/usr/bin/python
# -*- coding: utf-8 -*-

from yaml import safe_load
import base64
from datetime import datetime, timedelta, timezone

from ansible.plugins.action import ActionBase
from ansible.module_utils._text import to_native
from ansible.module_utils.six import PY3

from kubernetes import client, config, dynamic
from kubernetes.client.rest import ApiException

HAS_JWT = True
try:
    import jwt # type: ignore[import]
except ImportError as ex:
    HAS_JWT = False


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


def b64decode(source):
    content = base64.b64decode(source)
    if PY3:
        content = content.decode('utf-8')
    return content


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()
        result = dict()

        kubeconfig = module_args.get('kubeconfig', None)
        garden_name = module_args.get('garden_name', 'local')
        token_secret_name = module_args.get('token_secret_name', 'shoot-access-virtual-garden')
        port = module_args.get('port', None)
        refresh_minutes = module_args.get('refresh_minutes', 30)

        # check token if already created and not expiring
        already_present = task_vars.get("ansible_facts", {}).get('virtual_garden_kubeconfig', None)
        expires_at = task_vars.get("ansible_facts", {}).get('virtual_garden_kubeconfig_expires_at', None)

        if already_present and expires_at:
            expires_in = datetime.fromtimestamp(expires_at, timezone.utc) - datetime.now(timezone.utc)
            display.vvv("virtual garden kubeconfig expires in " + to_native(expires_in))
            if expires_in > timedelta(minutes=refresh_minutes):
                result["skipped"] = True
                return result

        try:
            if kubeconfig:
                if isinstance(kubeconfig, str) or kubeconfig is None:
                    api_client = config.new_client_from_config(config_file=kubeconfig)
                elif isinstance(kubeconfig, dict):
                    api_client = config.new_client_from_config_dict(config_dict=kubeconfig)
                else:
                    result["failed"] = True
                    result["msg"] = "error while reading kubeconfig parameter: a string or dict expected, but got %s instead" % type(kubeconfig)
                    return result
            else:
                api_client = config.new_client_from_config()
        except Exception as e:
            result["failed"] = True
            result["msg"] = "unable to create kubernetes client: " + to_native(e)
            return result

        token_secret = client.CoreV1Api(api_client).read_namespaced_secret(name=token_secret_name, namespace='garden')
        if not token_secret.data:
            result["failed"] = True
            result["msg"] = "token secret shoot-access-virtual-garden does not contain data (yet?)"
            return result

        token = b64decode(token_secret.data.get('token'))
        expires_at = None

        if HAS_JWT:
            claims = jwt.decode(
                token,
                "",
                options={"require": ["exp"], "verify_exp": False, "verify_signature": False},
                algorithms=["RS256"],
            )

            expires_at = claims['exp']

        garden = dynamic.DynamicClient(client=api_client).resources.get(api_version='operator.gardener.cloud/v1alpha1', kind='Garden').get(name=garden_name)
        server = 'api.' + garden.spec.virtualCluster.dns.domains[0].name

        if port is None:
            port = 443 # default port for exposal is 443

            try:
                # assume mini-lab in case the virtual garden was exposed through ingress-nginx
                client.NetworkingV1Api(api_client).read_namespaced_ingress(name='apiserver-ingress', namespace='virtual-garden-istio-ingress')
                port = 4443
            except ApiException as e:
                if e.status == 404:
                    pass
                else:
                    result["failed"] = True
                    result["msg"] = "error determining port for access kubeconfig: " + to_native(e)
                    return result

        generic_kubeconfig_secrets = client.CoreV1Api(api_client).list_namespaced_secret(namespace='garden', label_selector='managed-by=secrets-manager,manager-identity=gardener-operator,name=generic-token-kubeconfig')

        generic_kubeconfig_secret = self._get_latest_secret(generic_kubeconfig_secrets)
        if not generic_kubeconfig_secret:
            result["failed"] = True
            result["msg"] = "no latest generic-token-kubeconfig secret found"
            return result

        generic_kubeconfig = safe_load(b64decode(generic_kubeconfig_secret.data.get("kubeconfig"))).get("clusters")[0].get("cluster")

        virtual_garden_kubeconfig = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [
                {
                    "name": "default-cluster",
                    "cluster": {
                        "certificate-authority-data": generic_kubeconfig.get("certificate-authority-data"),
                        "server": "https://" + server + ":" + str(port),
                    }
                }
            ],
            "current-context": "default-context",
            "contexts": [
                {
                    "name": "default-context",
                    "context": {
                        "cluster": "default-cluster",
                        "user": "default-user",
                    }
                }
            ],
            "users": [
                {
                    "name": "default-user",
                    "user": {
                        "token": safe_load(token),
                    }
                }
            ],
        }

        result['virtual_garden_kubeconfig'] = virtual_garden_kubeconfig
        if expires_at:
            result['virtual_garden_kubeconfig_expires_at'] = expires_at

        return dict(ansible_facts=dict(result))


    @staticmethod
    def _get_latest_secret(secrets):
        latest = None
        for secret in secrets.items:
            issued_time = int(secret.metadata.labels.get('issued-at-time'))
            if latest is None or int(secret.metadata.labels.get('issued-at-time')) < issued_time:
                latest = secret
        return latest
