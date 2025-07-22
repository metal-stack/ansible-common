#!/usr/bin/python
# -*- coding: utf-8 -*-

import tarfile
import tempfile
import json
import os

from io import BytesIO
from yaml import safe_load
from urllib.parse import urlparse
from traceback import format_exc

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native
from ansible.playbook.role import Role
from ansible.playbook.role.include import RoleInclude
from ansible.errors import AnsibleError
from ansible import constants as C


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
        result = dict()

        self._supports_check_mode = True

        vectors = self._task.args.get(
            'vectors', task_vars.get('metal_stack_release_vectors'))
        cache_enabled = boolean(self._task.args.get('cache', task_vars.get(
            'metal_stack_release_vector_cache', True)), strict=False)

        if not vectors:
            result["skipped"] = True
            result["msg"] = "no release vectors were provided"
            return result

        if cache_enabled and os.path.isfile(self._cache_file_path()):
            result["changed"] = False
            with open(self._cache_file_path(), 'r') as vector:
                result["ansible_facts"] = json.load(vector)
            display.vvv("- Returning cache from %s" % self._cache_file_path)
            return result

        if not isinstance(vectors, list):
            result["failed"] = True
            result["msg"] = "vectors must be a list"
            return result

        result["changed"] = False
        ansible_facts = {}

        for vector in vectors:
            kwargs = dict(
                oci_registry_username=vector.pop(
                    "oci_registry_username", None),
                oci_registry_password=vector.pop(
                    "oci_registry_password", None),
                oci_registry_scheme=vector.pop(
                    "oci_registry_scheme", 'https')
            )

            try:
                data = RemoteResolver(
                    module=self, task_vars=task_vars, args=vector).resolve(**kwargs)
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

        if cache_enabled:
            with open(self._cache_file_path(), 'w') as vector:
                vector.write(json.dumps(ansible_facts))
                display.vvv("- Written cache file to %s" %
                            self._cache_file_path)

        return result

    @staticmethod
    def _cache_file_path():
        return os.path.join(tempfile.gettempdir(), ActionModule.CACHE_FILE)


class RemoteResolver():
    _cached_role_defaults = dict()

    def __init__(self, module, task_vars, args):
        self._module = module
        self._task_vars = task_vars.copy()

        args = args.copy()

        self._url = module._templar.template(args.pop("url", None))
        if not self._url:
            raise Exception("url is required")

        self._mapping_path = args.pop("variable_mapping_path", None)
        if not self._mapping_path:
            raise Exception(
                "variable_mapping_path is required for %s" % self._url)

        self._replacements = args.pop("replace", self._task_vars.get(
            "metal_stack_release_vector_replacements", list()))

        self._nested = args.pop("nested", list())
        self._include_role_defaults = args.pop("include_role_defaults", None)
        self._role_aliases = args.pop("role_aliases", list())
        self._install_roles = args.pop('install_roles', self._task_vars.get(
            'metal_stack_release_vector_install_roles', True))
        self._ansible_roles_path = args.pop('ansible_roles_path', None)

        if args:
            raise Exception("unknown parameters used for %s: %s" %
                            (self._url, args.keys()))

    def resolve(self, **kwargs):
        # download release vector
        content = ContentLoader(self._url, **kwargs).load()

        # apply replacements
        for r in self._replacements:
            if r.get("key") is None or r.get("old") is None or r.get("new") is None:
                raise Exception(
                    "replace must contain and dict with the keys for 'key', 'old' and 'new'")
            self.replace_key_value(content, r.get(
                "key"), r.get("old"), r.get("new"))

        # setup ansible-roles of release vector
        if self._install_roles:
            if self._ansible_roles_path:
                try:
                    role_dict = self.dotted_path(
                        content, self._ansible_roles_path)
                except KeyError:
                    raise Exception("given ansible-roles path %s not found in %s" %
                                    (self._ansible_roles_path, self._url))
            else:
                role_dict = content.get("ansible-roles", {})

            self._install_ansible_roles(role_dict=role_dict, **kwargs)

        # find mapping_path in variable sources (task_vars and role default vars)
        try:
            mapping = self.dotted_path(
                self._task_vars | self._load_role_default_vars(), self._mapping_path)
        except KeyError:
            raise Exception(
                "no mapping not found in any variables at %s" % self._mapping_path)

        # map to variables
        result = dict()

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
                raise Exception("nested entries must contain an url_path")

            try:
                n["url"] = self.dotted_path(content, path)
            except KeyError as e:
                raise Exception(
                    """url_path "%s" does not exist in %s""" % (path, self._url))

            results = RemoteResolver(
                module=self._module, task_vars=self._task_vars, args=n).resolve(**kwargs)

            for k, v in results.items():
                if result.get(k) is not None:
                    continue

                result[k] = v

        return result

    def _install_ansible_roles(self, role_dict, **kwargs):
        for role_name, spec in role_dict.items():
            role_ref = spec.get("oci")
            role_repository = spec.get("repository")

            # lookup aliases
            for alias in self._role_aliases:
                if alias.get("repository") == role_repository:
                    role_name = alias.get("alias")

            role_version = spec.get("version")

            # check for overwritten role version
            role_version_overwrite = self._task_vars.get(
                role_name.replace("-", "_").lower() + "_version")
            if role_version_overwrite:
                role_version = role_version_overwrite

            if not role_version:
                raise Exception("no version specified for role " + role_name)

            if not C.DEFAULT_ROLES_PATH:
                raise Exception("no default roles path configured")
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
                          tar_dest=os.path.dirname(role_path), **kwargs).load()
            else:
                try:
                    self._module._execute_module(module_name='ansible.builtin.git', module_args={
                        'repo': role_repository,
                        'dest': role_path,
                        'depth': 1,
                    }, task_vars=self._task_vars, tmp=None)
                except Exception as e:
                    raise Exception(
                        "error cloning git repository: %s" % to_native(e))

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
        self._registry, self._namespace, self._version = self._parse_oci_ref(
            self._url, scheme=kwargs.pop("oci_registry_scheme", "https"))
        self._username = kwargs.pop("oci_registry_username", None)
        self._password = kwargs.pop("oci_registry_password", None)

        if kwargs:
            raise Exception("unknown parameters passed to oci loader: %s" %
                            kwargs.keys())

    def load(self):
        if not HAS_OPENCONTAINERS:
            raise ImportError(
                "opencontainers must be installed in order to resolve metal-stack oci release vectors")

        blob, media_type = self._download_blob()

        if media_type == self.ANSIBLE_ROLE_MEDIA_TYPE:
            if not self._dest:
                raise Exception("tar destination must be specified")
            return self._extract_tar_gzip(blob, dest=self._dest)
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
            raise Exception(
                "the download of the release vector raised an error: %s" % to_native(e))

        manifest = response.json()

        target = None
        for layer in manifest["layers"]:
            if layer["mediaType"] == self.RELEASE_VECTOR_MEDIA_TYPE or layer["mediaType"] == self.ANSIBLE_ROLE_MEDIA_TYPE:
                target = layer
                break

        if not target:
            raise Exception("no layer with media type %s or %s found in oci release vector" % (
                self.RELEASE_VECTOR_MEDIA_TYPE, self.ANSIBLE_ROLE_MEDIA_TYPE))

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
            raise Exception(
                "the download of the release vector layer raised an error: %s" % to_native(e))

        return blob.content, layer["mediaType"]

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
                    raise Exception(
                        "error extracting tar member from oci layer: %s" % to_native(e))

    @staticmethod
    def _extract_tar_gzip(bytes, dest):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            try:
                tar.extractall(dest, tar.getmembers())
            except Exception as e:
                raise Exception(
                    "error extracting tar from oci layer: %s" % to_native(e))
