# systemd-docker-service-cleanup

Stops a systemd unit and deletes its service definition.

## Variables

| Name                              | Mandatory | Description                                                                           |
| --------------------------------- | --------- | ------------------------------------------------------------------------------------- |
| systemd_service_name              | yes       | The name of the systemd service                                                       |

## Examples

```
- name: cleanup metal-core service
  include_role:
    name: systemd-docker-service-cleanup
  vars:
    systemd_service_name: metal-core
```
