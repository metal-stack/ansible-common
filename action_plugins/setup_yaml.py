#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tarfile

from io import BytesIO
from yaml import safe_load
from urllib.parse import urlparse

from traceback import format_exc
from yaml import safe_load
from abc import ABC

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native
from ansible.playbook.role import Role
from ansible.playbook.role.include import RoleInclude


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


class ActionModule(ActionBase):
    ALREADY_RESOLVED_MARKER = "_yaml_files_already_resolved"


    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        super(ActionModule, self).run(tmp, task_vars)
        result = dict()

        self._supports_check_mode = True

        files = self._task.args.get('files', task_vars.get('setup_yaml'))
        smart = boolean(self._task.args.get('smart', task_vars.get('setup_yaml_smart', True)), strict=False)

        if not files:
            result["skipped"] = True
            return result

        if smart and task_vars.get("ansible_facts", {}).get(self.ALREADY_RESOLVED_MARKER, False):
            result["skipped"] = True
            return result

        if not isinstance(files, list):
            result["failed"] = True
            result["msg"] = "files must be a list"
            return result

        result["changed"] = False
        ansible_facts = {
            self.ALREADY_RESOLVED_MARKER: True,
        }

        for f in files:
            resolver = RemoteResolver(module=self, args=f)

            kwargs = dict()
            if f.get("oci_registry_username"):
                kwargs["oci_registry_username"] = f.get("oci_registry_username")
            if f.get("oci_registry_password"):
                kwargs["oci_registry_password"] = f.get("oci_registry_password")
            if f.get("oci_registry_scheme"):
                kwargs["oci_registry_scheme"] = f.get("oci_registry_scheme")

            try:
                data = resolver.resolve(**kwargs)
            except Exception as e:
                result["failed"] = True
                result["msg"] = "error resolving yaml"
                result["error"] = to_native(e)
                result["traceback"] = format_exc()
                return result

            for k, v in data.items():
                if task_vars.get(k) is not None or ansible_facts.get(k) is not None:
                    # skip when already defined
                    continue

                ansible_facts[k] = v

        result["ansible_facts"] = ansible_facts

        return result


class RemoteResolver():
    def __init__(self, module, args):
        for _, defaults in args.get("_cached_role_defaults", dict()).items():
            args = args | defaults

        for role_name in args.get("from_role_defaults", list()):
            if not hasattr(self, '_cached_role_defaults'):
                self._cached_role_defaults = dict()
            elif role_name in self._cached_role_defaults:
                continue

            res = self.load_role_default_vars(module=module, role_name=role_name)

            args = args | res

            self._cached_role_defaults[role_name] = res

        meta_var = module._templar.template(args.get("meta_var"))

        if meta_var:
            meta_args = args.get(meta_var)
            if not meta_args:
                raise Exception("""the meta variable with name "%s" specified for the setup_yaml is not defined, please provide it through inventory, role defaults or module args""" % meta_var)

            args = args | meta_args

        self._module = module
        self._url = module._templar.template(args.get("url"))
        self._mapping = args.get("mapping")
        self._nested = args.get("nested", list()) if args.get("recursive", True) else list()
        self._replacements = args.get("replace", list())

        if not self._url:
            raise Exception("url is required")

        if not self._mapping:
            raise Exception("mapping is required for %s" % self._url)


    def resolve(self, **kwargs):

        content = ContentLoader(self._url, **kwargs).load()

        for r in self._replacements:
            if r.get("key") is None or r.get("old") is None or r.get("new") is None:
                raise Exception("replace must contain and dict with the keys for 'key', 'old' and 'new'")
            self.replace_key_value(content, r.get("key"), r.get("old"), r.get("new"))

        result = dict()
        for k, path in self._mapping.items():
            try:
                value = self.dotted_path(content, path)
            except KeyError as e:
                display.warning(
                    """mapping path %s does not exist in %s: %s""" % (
                        path, self._url, to_native(e)))
                continue

            result[k] = value

        for n in self._nested:
            path = n.get("url_path")
            if not path:
                raise Exception("nested entries must contain an url_path")

            n["replace"] = n.get("replace", list()) + self._replacements
            n["url"] = self.dotted_path(content, path)
            n["_cached_role_defaults"] = self._cached_role_defaults

            resolver = RemoteResolver(module=self._module, args=n)
            for k, v in resolver.resolve(**kwargs).items():
                result[k] = v

        return result


    @staticmethod
    def load_role_default_vars(module, role_name):
        i = RoleInclude.load(role_name, play=module._task.get_play(),
                             current_role_path=module._task.get_path(),
                             variable_manager=module._task.get_variable_manager(),
                             loader=module._task.get_loader(), collection_list=None)

        return Role().load(role_include=i, play=module._task.get_play()).get_default_vars()


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

        for _, v in data.items():
            if isinstance(v, dict):
                RemoteResolver.replace_key_value(v, key, old, new)


class ContentLoader(ABC):
    def __init__(self, url, **kwargs):
        if url.startswith(OciLoader.OCI_PREFIX):
            self._loader = OciLoader(url, **kwargs)
        else:
            self._loader = UrlLoader(url)

    def load(self) -> dict:
        raw = self._loader.load()
        return safe_load(raw)


class UrlLoader():
    def __init__(self, url, **_):
        self._url = url

    def load(self):
        return open_url(self._url).read()


class OciLoader():
    OCI_PREFIX = "oci://"
    RELEASE_VECTOR_MEDIA_TYPE = "application/vnd.metal-stack.release-vector.v1.tar+gzip"

    def __init__(self, url, **kwargs):
        self._url = url[len(OciLoader.OCI_PREFIX):]
        self._member = kwargs.get("tar_member_file_name", "release.yaml")
        self._layer_media_type = kwargs.get("layer_media_type", OciLoader.RELEASE_VECTOR_MEDIA_TYPE)
        self._registry, self._namespace, self._version = self._parse_oci_ref(self._url, scheme=kwargs.get("oci_registry_scheme", "https"))
        self._username = kwargs.get("oci_registry_username")
        self._password = kwargs.get("oci_registry_password")


    def load(self):
        if not HAS_OPENCONTAINERS:
            raise ImportError("opencontainers must be installed in order to resolve metal-stack oci release vectors")

        blob = self._download_blob()

        return self._extract_tar_gzip_file(blob.content, member=self._member)

    def _download_blob(self):
        opts = [WithDefaultName(self._namespace)]
        if self._username and self._password:
            opts.append(WithUsernamePassword(username=self._username, password=self._password))

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
            raise Exception("the download of the release vector raised an error: %s" % to_native(e))

        manifest = response.json()

        target = None
        for layer in manifest["layers"]:
            if layer["mediaType"] == self._layer_media_type:
                target = layer
                break

        if not target:
            raise Exception("no layer with media type %s found in oci release vector" % OciLoader.RELEASE_VECTOR_MEDIA_TYPE)

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
        if tag is None:
            raise Exception("oci ref %s needs to specify a tag" % full_ref)
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
