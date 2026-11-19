# push-oci-image

Pulls an image on the ansible controller, then pushes it to the ansible host.

Useful for SONiC switches with active Management VRF, that may not always have a EVPN Underlay.

## Requirements

- docker installed on ansible controller
- [community.docker](https://galaxy.ansible.com/ui/repo/published/community/docker/) collection >= 5.2.0 installed on ansible controller
- docker installed on ansible host
- OCI image must be pullable or present from ansible controller

## Variables

| Name                     | Mandatory | Description                                                                      |
| ------------------------ | --------- | -------------------------------------------------------------------------------- |
| push_oci_image_name      | yes       | OCI image name                                                                   |
| push_oci_image_tag       | yes       | OCI image tag                                                                    |
| push_oci_image_skip_pull |           | Skips pulling the image on the controller                                        |
| push_oci_image_platform  |           | Image platform (e.g. `linux/amd64`), defaults to the platform of the target host |

## Examples

```
- name: Push metal-core image
  include_role:
    name: ansible-common/roles/push-oci-image
  vars:
    push_oci_image_name: "ghcr.io/metal-stack/metal-core"
    push_oci_image_tag: "latest"
```
