#!/usr/bin/python
# -*- coding: utf-8 -*-

import tarfile
import tempfile
import json
import os
import subprocess

from io import BytesIO
from yaml import safe_load
from urllib.parse import urlparse
from traceback import format_exc

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError
from ansible.module_utils._text import to_native
from ansible.playbook.role import Role
from ansible.playbook.role.include import RoleInclude
from ansible import constants as C
from ansible.module_utils.common import process

HAS_OPENCONTAINERS = True
try:
    # type: ignore[import]
    from opencontainers.distribution.reggie import NewClient, WithReference, WithDigest, WithDefaultName, WithUsernamePassword
    import opencontainers.image.v1 as opencontainersv1  # type: ignore[import]
except ImportError as ex:
    HAS_OPENCONTAINERS = False


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


class ActionModule(ActionBase):
    CACHE_FILE = "metal-stack-release-vector-cache.json"

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        self._task.args.setdefault('vectors', task_vars.get(
            'metal_stack_release_vectors', None))

        validation_result, task_args = self._validate_module_args()
        result = dict()

        if validation_result.error_messages:
            result["failed"] = True
            result["msg"] = str(validation_result.error_messages)
            return result

        # as we can pick up the module inputs from task_vars,
        # we have to run this through the templar to allow using
        # variables in the module inputs
        task_args = self._templar.template(task_args)

        self._supports_check_mode = True

        if task_args.get('cache') and os.path.isfile(self._cache_file_path()):
            result["changed"] = False
            with open(self._cache_file_path(), 'r') as vector:
                result["ansible_facts"] = json.load(vector)
            display.vvv("- Returning cache from %s" % self._cache_file_path)
            return result

        result["changed"] = False
        ansible_facts = {}

        for vector in task_args.get('vectors'):
            try:
                data = RemoteResolver(
                    module=self, task_vars=task_vars, task_args=vector).resolve()
            except Exception as e:
                result["failed"] = True
                result["msg"] = "error resolving yaml"
                result["error"] = to_native(e)
                result["traceback"] = format_exc()
                return result

            for k, v in data.items():
                if task_vars.get(k) is not None:
                    # skip if already defined, this allows users to provide overwrites
                    continue

                if ansible_facts.get(k) is not None:
                    display.warning(
                        "variable %s was resolved more than once, using first defined value (%s)" % (k, ansible_facts.get(k)))
                    continue

                ansible_facts[k] = v

        result["ansible_facts"] = ansible_facts

        if task_args.get('cache'):
            with open(self._cache_file_path(), 'w') as vector:
                vector.write(json.dumps(ansible_facts))
                display.vvv("- Written cache file to %s" %
                            self._cache_file_path)

        return result

    def _validate_module_args(self):
        common_vectors_argument_spec = dict(
            variable_mapping_path=dict(type='str', required=False),
            include_role_defaults=dict(type='str', required=False),
            install_roles=dict(type='bool', required=False, default=True),
            ansible_roles_path=dict(
                type='str', required=False, default="ansible-roles"),
            role_aliases=dict(type='list', elements='dict', required=False, default=list(), options=dict(
                name=dict(type='str', required=True),
                alias=dict(type='str', required=True),
            )),
            replace=dict(type='list', elements='dict', required=False, default=list(), options=dict(
                key=dict(type='str', required=True),
                old=dict(type='str', required=True),
                new=dict(type='str', required=True),
            )),
            oci_registry_username=dict(type='str', required=False),
            oci_registry_password=dict(type='str', required=False),
            oci_registry_scheme=dict(
                type='str', required=False, default='https'),
            oci_cosign_verify_certificate_identity=dict(
                type='str', required=False),
            oci_cosign_verify_certificate_oidc_issuer=dict(
                type='str', required=False),
            oci_cosign_verify_key=dict(type='str', required=False),
        )

        nested_vectors_argument_spec = dict(
            url_path=dict(type='str', required=True),
            # we do not go into further depths here
            nested=dict(type='list', elements='dict',
                        required=False, default=list()),
        )
        nested_vectors_argument_spec.update(common_vectors_argument_spec)

        vectors_options = dict(
            url=dict(type='str', required=True),
            nested=dict(type='list', elements='dict', required=False, default=list(),
                        options=nested_vectors_argument_spec),
        )
        vectors_options.update(common_vectors_argument_spec)

        return self.validate_argument_spec(
            argument_spec=dict(
                cache=dict(type='bool', required=False, default=True),
                vectors=dict(type='list', elements='dict',
                             required=False, default=list(), options=vectors_options),
            ))

    @staticmethod
    def _cache_file_path():
        return os.path.join(tempfile.gettempdir(), ActionModule.CACHE_FILE)


class RemoteResolver():
    _cached_role_defaults = dict()

    def __init__(self, module, task_vars, task_args):
        self._module = module
        self._task_vars = task_vars.copy()

        task_args = task_args.copy()

        self._url = task_args.pop("url", None)
        if not self._url:
            raise ValueError("url is required")

        self._mapping_path = task_args.pop("variable_mapping_path", None)
        self._replacements = task_args.pop("replace", self._task_vars.get(
            "metal_stack_release_vector_replacements", list()))

        self._nested = task_args.pop("nested", list())
        self._include_role_defaults = task_args.pop(
            "include_role_defaults", None)
        self._role_aliases = task_args.pop("role_aliases", list())
        self._install_roles = task_args.pop('install_roles', self._task_vars.get(
            'metal_stack_release_vector_install_roles', True))
        self._ansible_roles_path = task_args.pop(
            'ansible_roles_path', "ansible-roles")

        self._loader_args = dict(
            oci_registry_username=task_args.pop(
                "oci_registry_username", None),
            oci_registry_password=task_args.pop(
                "oci_registry_password", None),
            oci_registry_scheme=task_args.pop(
                "oci_registry_scheme", 'https'),
            oci_cosign_verify_certificate_identity=task_args.pop(
                "oci_cosign_verify_certificate_identity", None),
            oci_cosign_verify_certificate_oidc_issuer=task_args.pop(
                "oci_cosign_verify_certificate_oidc_issuer", None),
            oci_cosign_verify_key=task_args.pop(
                "oci_cosign_verify_key", None),
        )

        if task_args:
            raise ValueError("unknown parameters used for %s: %s" %
                             (self._url, task_args.keys()))

    def resolve(self):
        # download release vector
        content = ContentLoader(self._url, **self._loader_args).load()

        # apply replacements
        for r in self._replacements:
            if r.get("key") is None or r.get("old") is None or r.get("new") is None:
                raise ValueError(
                    "replace must contain and dict with the keys for 'key', 'old' and 'new'")
            self.replace_key_value(content, r.get(
                "key"), r.get("old"), r.get("new"))

        # setup ansible-roles of release vector
        if self._install_roles:
            try:
                role_dict = self.dotted_path(
                    content, self._ansible_roles_path)
            except KeyError as e:
                raise AnsibleError("given ansible-roles path %s not found in %s" %
                                   (self._ansible_roles_path, self._url)) from e

            self._install_ansible_roles(
                role_dict=role_dict, **self._loader_args)

        # map to variables
        result = dict()

        if self._mapping_path:
            # find mapping_path in variable sources (task_vars and role default vars)
            try:
                mapping = self.dotted_path(
                    self._task_vars | self._load_role_default_vars(), self._mapping_path)
            except KeyError as e:
                raise KeyError(
                    "no mapping found in any variables at %s" % self._mapping_path) from e

            for k, path in mapping.items():
                try:
                    value = self.dotted_path(content, path)
                except KeyError:
                    display.warning(
                        """path %s provided by mapping does not exist in %s""" % (path, self._url))
                    continue

                result[k] = value

        # resolve nested vectors
        for n in self._nested:
            path = n.pop("url_path", None)
            if not path:
                raise ValueError("nested entries must contain an url_path")

            try:
                n["url"] = self.dotted_path(content, path)
            except KeyError as e:
                raise KeyError(
                    """url_path "%s" does not exist in %s""" % (path, self._url)) from e

            results = RemoteResolver(
                module=self._module, task_vars=self._task_vars, task_args=n).resolve()

            for k, v in results.items():
                if result.get(k) is not None:
                    continue

                result[k] = v

        return result

    def _install_ansible_roles(self, role_dict, **kwargs):
        for role_name, spec in role_dict.items():
            role_ref = spec.get("oci")
            role_repository = spec.get("repository")
            prefix_filter = None

            # lookup aliases
            for alias in self._role_aliases:
                if alias.get("name") == role_name:
                    new_role_name = alias.get("alias")
                    prefix_filter = OciLoader.prefix_filter(
                        role_name, new_role_name)
                    role_name = new_role_name
                    break

            role_version = spec.get("version")

            # check for overwritten role version
            role_version_overwrite = self._task_vars.get(
                role_name.replace("-", "_").lower() + "_version")
            if role_version_overwrite:
                role_version = role_version_overwrite

            if not role_version:
                raise ValueError("no version specified for role " + role_name)

            if not C.DEFAULT_ROLES_PATH:
                raise AnsibleError("no default roles path configured")
            role_path = os.path.join(C.DEFAULT_ROLES_PATH[0], role_name)

            if not role_ref and not role_repository:
                display.display(
                    "- %s has no oci ref nor repository defined, skipping" % (role_name), color=C.COLOR_SKIP)
                continue

            if os.path.isdir(role_path):
                display.display("- %s already installed in %s, skipping" %
                                (role_name, role_path), color=C.COLOR_SKIP)
                continue

            display.display("- Installing %s (%s) from %s to %s" % (role_name, role_version,
                            role_ref if role_ref else role_repository, role_path), color=C.COLOR_CHANGED)

            if role_ref:
                OciLoader(url=role_ref + ":" + role_version,
                          media_type=OciLoader.ANSIBLE_ROLE_MEDIA_TYPE,
                          tar_dest=os.path.dirname(role_path), dest_filter=prefix_filter, **kwargs).load()
            else:
                module_result = self._module._execute_module(module_name='ansible.builtin.git', module_args={
                    'repo': role_repository,
                    'dest': role_path,
                    'depth': 1,
                    'version': role_version,
                }, task_vars=self._task_vars, tmp=None)

                if module_result.get('failed'):
                    msg = module_result.get('module_stderr')
                    if not msg:
                        msg = module_result.get('module_stdout')
                    if not msg:
                        msg = module_result.get('msg')
                    raise AnsibleError(msg)

    def _load_role_default_vars(self):
        defaults = dict()

        cached_roles = RemoteResolver._cached_role_defaults

        for role_name, cached_defaults in cached_roles.items():
            defaults = defaults | cached_defaults

        role_name = self._include_role_defaults

        if not role_name or role_name in cached_roles:
            return defaults

        i = RoleInclude.load(role_name, play=self._module._task.get_play(),
                             current_role_path=self._module._task.get_path(),
                             variable_manager=self._module._task.get_variable_manager(),
                             loader=self._module._task.get_loader(), collection_list=None)

        included_defaults = Role().load(
            role_include=i, play=self._module._task.get_play()).get_default_vars()

        cached_roles[role_name] = included_defaults
        defaults = defaults | included_defaults

        RemoteResolver._cached_role_defaults = cached_roles

        return defaults

    @staticmethod
    def dotted_path(vector, path):
        value = vector
        for p in path.split("."):
            value = value[p]
        return value

    @staticmethod
    def replace_key_value(data, key, old, new):
        if not isinstance(data, dict):
            return

        if key in data:
            to_replace = data[key]
            if isinstance(to_replace, str):
                data[key] = to_replace.replace(old, new)
                if data[key] != to_replace:
                    display.vvv("- Replaced value %s with %s" %
                                (to_replace, data[key]))

        for _, v in data.items():
            if isinstance(v, dict):
                RemoteResolver.replace_key_value(v, key, old, new)


class ContentLoader():
    OCI_PREFIX = "oci://"

    def __init__(self, url, **kwargs):
        if url.startswith(self.OCI_PREFIX):
            self._loader = OciLoader(url[len(self.OCI_PREFIX):], **kwargs)
        else:
            self._loader = UrlLoader(url, **kwargs)

    def load(self) -> dict:
        display.display("- Loading remote content from %s" %
                        self._loader._url, color=C.COLOR_OK)
        raw = self._loader.load()
        return safe_load(raw)


class UrlLoader():
    def __init__(self, url, **_):
        self._url = url

    def load(self):
        return open_url(self._url).read()


class OciLoader():
    RELEASE_VECTOR_MEDIA_TYPE = "application/vnd.metal-stack.release-vector.v1.tar+gzip"
    ANSIBLE_ROLE_MEDIA_TYPE = "application/vnd.metal-stack.ansible-role.v1.tar+gzip"

    def __init__(self, url, **kwargs):
        self._url = url
        self._member = kwargs.pop("tar_member_file_name", "release.yaml")
        self._dest = kwargs.pop("tar_dest", None)
        self._dest_filter = kwargs.pop("dest_filter", None)
        self._media_type = kwargs.pop(
            "media_type", OciLoader.RELEASE_VECTOR_MEDIA_TYPE)
        self._registry, self._namespace, self._version = self._parse_oci_ref(
            self._url, scheme=kwargs.pop("oci_registry_scheme", "https"))
        self._username = kwargs.pop("oci_registry_username", None)
        self._password = kwargs.pop("oci_registry_password", None)

        self._cosign_identity = kwargs.pop(
            "oci_cosign_verify_certificate_identity", None)
        self._cosign_issuer = kwargs.pop(
            "oci_cosign_verify_certificate_oidc_issuer", None)
        self._cosign_key = kwargs.pop("oci_cosign_verify_key", None)

        if kwargs:
            raise ValueError("unknown parameters passed to oci loader: %s" %
                             kwargs.keys())

    def load(self):
        if not HAS_OPENCONTAINERS:
            raise ImportError(
                "opencontainers must be installed in order to resolve metal-stack oci release vectors")

        if self._cosign_key or self._cosign_identity or self._cosign_issuer:
            try:
                bin_path = process.get_bin_path(
                    "cosign", required=True, opt_dirs=None)

                if self._username and self._password:
                    subprocess.run(args=[bin_path, "login", "--username",  self._username, "--password-stdin=true"],
                                   input=self._password, check=True, capture_output=True)

                if self._cosign_key:
                    subprocess.run(args=[bin_path, "verify", "--key", "env://PUBKEY", self._url],
                                   env=dict(PUBKEY=self._cosign_key), check=True, capture_output=True)
                    display.display(
                        "- %s was verified successfully by public key through cosign" % self._url, color=C.COLOR_OK)
                elif self._cosign_identity or self._cosign_issuer:
                    subprocess.run(args=[bin_path, "verify", "--certificate-oidc-issuer", self._cosign_issuer,
                                         "--certificate-identity", self._cosign_identity, self._url],
                                   check=True, capture_output=True)
                    display.display(
                        "- %s was verified successfully by oidc-issuer through cosign" % self._url, color=C.COLOR_OK)
            except ValueError as e:
                raise FileNotFoundError("cosign needs to be installed: %s" %
                                        to_native(e.message)) from e
            except subprocess.CalledProcessError as e:
                raise RuntimeError("cosign verification returned with exit code %s: %s" % (
                    e.returncode, to_native(e.stderr))) from e

        blob = self._download_blob()

        if self._media_type == OciLoader.ANSIBLE_ROLE_MEDIA_TYPE:
            if not self._dest:
                raise ValueError("tar destination must be specified")
            return self._extract_tar_gzip(blob, dest=self._dest, filter=self._dest_filter)
        else:
            return self._extract_tar_gzip_file(blob, member=self._member)

    def _download_blob(self):
        opts = [WithDefaultName(self._namespace)]
        if self._username and self._password:
            opts.append(WithUsernamePassword(
                username=self._username, password=self._password))

        client = NewClient(self._registry,
                           *opts
                           )

        req = client.NewRequest(
            "GET",
            "/v2/<name>/manifests/<reference>",
            WithReference(self._version),
        ).SetHeader("Accept", opencontainersv1.MediaTypeImageManifest)

        try:
            response = client.Do(req)
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                "the download of the release vector raised an error: %s" % to_native(e)) from e

        manifest = response.json()

        target = None
        for layer in manifest["layers"]:
            if layer["mediaType"] == self._media_type:
                target = layer
                break

        if not target:
            raise RuntimeError("no layer with media type %s found in oci artifact %s" % (
                self._media_type,  self._url))

        req = client.NewRequest(
            "GET",
            "/v2/<name>/blobs/<digest>",
            WithDigest(target['digest']),
        )

        req.stream = True

        try:
            blob = client.Do(req)
            blob.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                "the download of the release vector layer raised an error: %s" % to_native(e)) from e

        return blob.content

    @staticmethod
    def _parse_oci_ref(full_ref, scheme='https'):
        ref, *tag = full_ref.rsplit(":", maxsplit=1)
        tag = tag[0] if tag else None
        if tag is None:
            raise ValueError("oci ref %s needs to specify a tag" % full_ref)
        url = urlparse("%s://%s" % (scheme, ref))
        return "%s://%s" % (scheme, url.netloc), url.path.removeprefix('/'), tag

    @staticmethod
    def _extract_tar_gzip_file(bytes, member):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            with tar.extractfile(tar.getmember(member)) as f:
                try:
                    return f.read().decode('utf-8')
                except Exception as e:
                    raise RuntimeError(
                        "error extracting tar member from oci layer: %s" % to_native(e)) from e

    @staticmethod
    def _extract_tar_gzip(bytes, dest, filter=None):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            try:
                tar.extractall(
                    path=dest, members=tar.getmembers(), filter=filter)
            except Exception as e:
                raise RuntimeError(
                    "error extracting tar from oci layer: %s" % to_native(e)) from e

    @staticmethod
    def prefix_filter(old: str, new: str):
        def filter(member: tarfile.TarInfo, _: str, /) -> tarfile.TarInfo | None:
            parts = member.name.split("/")
            base = parts[0].replace(old, new)
            member.name = os.path.join(base, *parts[1:])
            return member
        return filter
