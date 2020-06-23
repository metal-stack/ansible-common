#!/usr/bin/python
# -*- coding: utf-8 -*-

from traceback import format_exc
from yaml import safe_load

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

if __name__ == '__main__':
    module_args = dict(
        version=dict(type='str', required=True),
        smart=dict(type='bool', default=True),
        image_vector_url_template=dict(type='str',
                                       default="https://raw.githubusercontent.com/metal-stack/releases/%s/release.yaml")
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        url = module.params['image_vector_url_template'] % module.params['version']
        rsp, info = fetch_url(module, url)
        if info['status'] != 200:
            module.fail_json(msg="failed to download image vector at %s: %s" % (url, info['msg']))

        image_vector = safe_load(rsp.read())
    except Exception as e:
        module.fail_json(msg="error getting image vector from url: %s" % url, error=e, traceback=format_exc())

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
                gardener_extension_provider_metal_image_name = gardener["gardener-extension-provider-metal"]["name"],
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
        module.fail_json(msg="error reading image versions from release vector, key not found: %s" % e)

    result["ansible_facts"]["_metal_stack_releases_already_executed"] = True

    module.exit_json(**result)
