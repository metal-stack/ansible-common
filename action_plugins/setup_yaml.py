#!/usr/bin/python
# -*- coding: utf-8 -*-

import tarfile

from io import BytesIO
from yaml import safe_load
from urllib.parse import urlparse

from traceback import format_exc
from yaml import safe_load

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native


HAS_OPENCONTAINERS = True
try:
    from opencontainers.distribution.reggie import NewClient, WithReference, WithDigest, WithDefaultName, WithUsernamePassword # type: ignore[import]
    import opencontainers.image.v1 as opencontainersv1 # type: ignore[import]
except ImportError as ex:
    HAS_OPENCONTAINERS = False


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


RELEASE_VECTOR_MEDIA_TYPE = "application/vnd.metal-stack.release-vector.v1.tar+gzip"


class ActionModule(ActionBase):
    ALREADY_RESOLVED_MARKER = "_yaml_files_already_resolved"

    def _ensure_invocation(self, result):
        # NOTE: adding invocation arguments here needs to be kept in sync with
        # any no_log specified in the argument_spec in the module.
        # This is not automatic.
        if 'invocation' not in result:
            if self._play_context.no_log:
                result['invocation'] = "CENSORED: no_log is set"
            else:
                # NOTE: Should be removed in the future. For now keep this broken
                # behaviour, have a look in the PR 51582
                result['invocation'] = self._task.args.copy()
                result['invocation']['module_args'] = self._task.args.copy()

        return result

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        self._supports_check_mode = True

        files = self._task.args.get('files', task_vars.get('setup_yaml'))
        smart = boolean(self._task.args.get('smart', task_vars.get('setup_yaml_smart', True)), strict=False)
        if not files:
            result["skipped"] = True
            return result

        result["failed"] = True
        if not isinstance(files, list):
            result["msg"] = "files must be a list"
        else:
            del result["failed"]

        if result.get("failed"):
            return result

        if smart and task_vars.get("ansible_facts", {}).get(self.ALREADY_RESOLVED_MARKER, False):
            result["skipped"] = True
            return self._ensure_invocation(result)

        result["changed"] = False

        for f in files:
            url = self._templar.template(f.get("url"))
            oci_ref = self._templar.template(f.get("oci"))
            recursive = f.get("recursive", True)
            replace = f.get("replace", [])
            var = self._templar.template(f.get("meta_var"))
            mapping = f.get("mapping", task_vars.get(var, dict()).get("mapping"))
            nested = f.get("nested", task_vars.get(var, dict()).get("nested", list())) if recursive else list()

            result = self.resolve(oci_ref, url, replace, mapping, nested, task_vars, result)
            if result.get("failed"):
                return result

        return self._ensure_invocation(result)

    def resolve(self, oci_ref, url, replace, mapping, nested, task_vars, result):
        result["failed"] = True

        if not url and not oci_ref:
            result["msg"] = "url or oci ref is required"
        elif not mapping:
            result["msg"] = "mapping is required"
        else:
            del result["failed"]

        if result.get("failed"):
            return result

        try:
            if oci_ref:
                if not HAS_OPENCONTAINERS:
                    raise ImportError("opencontainers must be installed in order to resolve metal-stack oci release vectors")

                # TODO: make registry scheme and tar member file configurable by the user
                registry, namespace, version = self._parse_oci_ref(oci_ref)

                blob = self._download_blob(
                    registry,
                    namespace,
                    version,
                    RELEASE_VECTOR_MEDIA_TYPE,
                )

                f = safe_load(self._extract_tar_gzip_file(blob.content, "release.yaml"))
            else:
                rsp = open_url(url)
                f = safe_load(rsp.read())
        except Exception as e:
            result["failed"] = True
            result["msg"] = "error getting image vector from url: %s" % url
            result["error"] = to_native(e)
            result["traceback"] = format_exc()
            return result

        for r in replace:
            if r.get("key") is None or r.get("old") is None or r.get("new") is None:
                result["msg"] = "replace must contain and dict with the keys for 'key', 'old' and 'new'"
                result["failed"] = True
                return result
            ActionModule.replace_key_value(f, r.get("key"), r.get("old"), r.get("new"))

        for n in nested:
            oci_path = self._templar.template(n.get("oci_path"))
            url_path = self._templar.template(n.get("url_path"))
            recursive = n.get("recursive", True)
            var = self._templar.template(n.get("meta_var"))
            nested_mapping = n.get("mapping", task_vars.get(var, dict()).get("mapping"))
            next_nested = n.get("nested", task_vars.get(var, dict()).get("nested", list())) if recursive else list()

            result["failed"] = True
            if not url_path and not oci_path:
                result["msg"] = "url_path or oci_path is required in nested"
            elif not nested_mapping:
                result["msg"] = "mapping is required in nested"
            else:
                del result["failed"]

            if result.get("failed"):
                return result

            u = None
            o = None

            try:
                if url_path:
                    u = self.resolve_path(f, url_path)
                if oci_path:
                    o = self.resolve_path(f, oci_path)
            except KeyError as e:
                result["failed"] = True
                result["msg"] = "error resolving path in nested"
                result["error"] = to_native(e)
                result["traceback"] = format_exc()
                return result

            result = self.resolve(o, u, replace, nested_mapping, next_nested, task_vars, result)
            if result.get("failed"):
                return result

        ansible_facts = dict()
        for k, path in mapping.items():
            if task_vars.get(k) is not None:
                # skip when already defined
                continue

            try:
                value = self.resolve_path(f, path)
            except KeyError as e:
                display.warning(
                    """error reading variable from file, variable %s not found in path: %s

                    (is the mapping appropriate for %s?)""" % (
                        to_native(e), path, url))
                continue

            ansible_facts[k] = value

        result["ansible_facts"] = result.get("ansible_facts", {self.ALREADY_RESOLVED_MARKER: True})
        result["ansible_facts"].update(ansible_facts)
        return result

    @staticmethod
    def resolve_path(vector, path):
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

        for k, v in data.items():
            if isinstance(v, dict):
                ActionModule.replace_key_value(v, key, old, new)

    @staticmethod
    def _download_blob(self, address, default_name, reference, layer_media_type):
        opts = [WithDefaultName(default_name)]
        if self._registry_username and self._registry_password:
            opts.append(WithUsernamePassword(username=self._registry_username, password=self._registry_password))

        client = NewClient(address,
            *opts
        )

        req = client.NewRequest(
            "GET",
            "/v2/<name>/manifests/<reference>",
            WithReference(reference),
        ).SetHeader("Accept", opencontainersv1.MediaTypeImageManifest)

        try:
            response = client.Do(req)
            response.raise_for_status()
        except Exception as e:
            raise Exception("the download of the release vector raised an error: %s" % to_native(e))

        manifest = response.json()

        for layer in manifest["layers"]:
            if layer["mediaType"] == layer_media_type:
                target = layer
                break

        if not target:
            raise Exception("no layer with media type %s found in oci release vector" % layer_media_type)

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
            raise Exception("the download of the release vector layer raised an error: %s" % to_native(e))

        return blob


    @staticmethod
    def _parse_oci_ref(full_ref, scheme='https'):
        ref, *tag = full_ref.split(":", 1)
        tag = tag[0] if tag else None
        url = urlparse("%s://%s" % (scheme, ref))
        return "%s://%s" % (scheme, url.netloc), url.path.removeprefix('/'), tag


    @staticmethod
    def _extract_tar_gzip_file(bytes, member):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            with tar.extractfile(tar.getmember(member)) as f:
                try:
                    return f.read().decode('utf-8')
                except Exception as e:
                    raise Exception("error extracting tar member from oci layer: %s" % to_native(e))
