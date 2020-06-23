#!/usr/bin/python
# -*- coding: utf-8 -*-

from traceback import format_exc
from yaml import safe_load

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


class ActionModule(ActionBase):
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

        version = self._task.args.get('version', None)
        image_vector_url_template = self._task.args.get('image_vector_url_template',
                                                        "https://raw.githubusercontent.com/metal-stack/releases/%s/release.yaml")
        smart = boolean(self._task.args.get('smart', True), strict=False)

        result["changed"] = False
        result['failed'] = True
        if not version:
            result['msg'] = 'src (or content) is required'
        else:
            del result['failed']

        if result.get('failed'):
            return self._ensure_invocation(result)

        if smart and task_vars.get('ansible_facts', {}).get('_metal_stack_releases_already_executed', False):
            result["skipped"] = True
            return self._ensure_invocation(result)

        url = image_vector_url_template % version
        try:
            rsp = open_url(url)
            image_vector = safe_load(rsp.read())
        except Exception as e:
            result["failed"] = True
            result["msg"] = "error getting image vector from url: %s" % url
            result["error"] = to_native(e)
            result["traceback"] = format_exc()
            return self._ensure_invocation(result)

        try:
            control_plane = image_vector["docker-images"]["metal-stack"]["control-plane"]
            partition = image_vector["docker-images"]["metal-stack"]["partition"]
            generic = image_vector["docker-images"]["metal-stack"]["generic"]
            gardener = image_vector["docker-images"]["metal-stack"]["gardener"]
            kubernetes = image_vector["docker-images"]["metal-stack"]["kubernetes"]

            third = image_vector["docker-images"]["third-party"]["control-plane"]

            result = dict(
                ansible_facts=dict(
                    metal_hammer_image_tag=image_vector["binaries"]["metal-stack"]["metal-hammer"]["version"],
                    metal_hammer_image_url=image_vector["binaries"]["metal-stack"]["metal-hammer"]["url"],

                    metal_api_image_tag=control_plane["metal-api"]["tag"],
                    metal_api_image_name=control_plane["metal-api"]["name"],
                    metal_metalctl_image_tag=control_plane["metalctl"]["tag"],
                    metal_metalctl_image_name=control_plane["metalctl"]["name"],
                    metal_masterdata_api_image_tag=control_plane["masterdata-api"]["tag"],
                    metal_masterdata_api_image_name=control_plane["masterdata-api"]["name"],
                    metal_console_image_tag=control_plane["metal-console"]["tag"],
                    metal_console_image_name=control_plane["metal-console"]["name"],

                    metal_core_image_tag=partition["metal-core"]["tag"],
                    metal_core_image_name=partition["metal-core"]["name"],
                    pixiecore_image_tag=partition["pixiecore"]["tag"],
                    pixiecore_image_name=partition["pixiecore"]["name"],

                    metal_db_backup_restore_sidecar_image_tag=generic["backup-restore-sidecar"]["tag"],
                    metal_db_backup_restore_sidecar_image_name=generic["backup-restore-sidecar"]["name"],
                    ipam_db_backup_restore_sidecar_image_tag=generic["backup-restore-sidecar"]["tag"],
                    ipam_db_backup_restore_sidecar_image_name=generic["backup-restore-sidecar"]["name"],
                    masterdata_db_backup_restore_sidecar_image_tag=generic["backup-restore-sidecar"]["tag"],
                    masterdata_db_backup_restore_sidecar_image_name=generic["backup-restore-sidecar"]["name"],

                    gardener_extension_provider_metal_image_tag=gardener["gardener-extension-provider-metal"]["tag"],
                    gardener_extension_provider_metal_image_name=gardener["gardener-extension-provider-metal"]["name"],
                    gardener_os_controller_image_tag=gardener["os-metal-extension"]["tag"],
                    gardener_os_controller_image_name=gardener["os-metal-extension"]["name"],

                    csi_lvm_image_tag=kubernetes["csi-lvm-controller"]["tag"],
                    csi_lvm_image_name=kubernetes["csi-lvm-controller"]["name"],
                    gardener_metal_cloud_controller_manager_image_tag=kubernetes["metal-ccm"]["tag"],
                    gardener_metal_cloud_controller_manager_image_name=kubernetes["metal-ccm"]["name"],

                    nsq_image_tag=third["nsq"]["tag"],
                    nsq_image_name=third["nsq"]["name"],
                    ipam_db_image_tag=third["ipam-db"]["tag"],
                    ipam_db_image_name=third["ipam-db"]["name"],
                    masterdata_db_image_tag=third["masterdata-db"]["tag"],
                    masterdata_db_image_name=third["masterdata-db"]["name"],
                    metal_db_image_tag=third["metal-db"]["tag"],
                    metal_db_image_name=third["metal-db"]["name"],
                )
            )
        except KeyError as e:
            result["failed"] = True
            result["msg"] = "error reading image versions from release vector, key not found: %s" % e
            return self._ensure_invocation(result)

        result["ansible_facts"]["_metal_stack_releases_already_executed"] = True

        return self._ensure_invocation(result)
