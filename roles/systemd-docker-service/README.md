# systemd-docker-service

Renders a systemd unit file that runs an application within a docker container.

## Variables

| Name                              | Mandatory | Description                                                                           |
| --------------------------------- | --------- | ------------------------------------------------------------------------------------- |
| systemd_service_name              | yes       | The name of the systemd service                                                       |
| systemd_docker_image_name         | yes       | The name of the docker image to run                                                   |
| systemd_docker_image_tag          | yes       | The tag of the docker image to run                                                    |
| systemd_service_environment       |           | Environment variables to pass through to the docker container                         |
| systemd_docker_network            |           | The docker network to use                                                             |
| systemd_docker_command            |           | The command to tun the docker container with                                          |
| systemd_docker_volumes            |           | Volumes to mount into the docker container                                            |
| systemd_docker_dns                |           | DNS server IP addresses to use instead host configuration                             |
| systemd_docker_cap_add            |           | Additional capabilities of the docker container                                       |
| systemd_docker_ports              |           | Ports of the docker container to expose                                               |
| systemd_docker_host_to_ip_mapping |           | Adds additional hosts to the docker container                                         |
| systemd_docker_cpus               |           | The number of CPUs for the docker container to use                                    |
| systemd_docker_cpu_period         |           | The CPU time period for the docker container to use                                   |
| systemd_docker_cpu_quota          |           | The number of microseconds per period for the docker container to use                 |
| systemd_docker_memory             |           | The maximum amount of memory for the docker container to use                          |
| systemd_service_restart_sec       |           | The number of seconds to wait before restarting the systemd service                   |
| systemd_service_timeout_start_sec |           | The number of seconds to wait before starting the systemd service                     |
| systemd_service_timeout_stop_sec  |           | The number of seconds to wait for the systemd service to stop                         |
| systemd_service_after             |           | The systemd unit after dependencies                                                   |
| systemd_service_wants             |           | The systemd unit wants dependencies                                                   |
| systemd_start                     |           | Starts the systemd service after rendering the template                               |
| systemd_external_config_changed   |           | Indicates that the systemd should be restarted because external configuration changed |

## Examples

```
- name: deploy metal-core service
  include_role:
    name: systemd-docker-service
  vars:
    systemd_service_name: metal-core
    systemd_docker_image_name: "{{ metal_core_image_name }}"
    systemd_docker_image_tag: "{{ metal_core_image_tag }}"
    systemd_docker_cpu_period: 50000
    systemd_docker_cpu_quota: 10000
    systemd_docker_memory: 256m
    # metal-core needs to figure out the switch ports, this is only possible from host network
    systemd_docker_network: host
    systemd_docker_volumes:
      - /etc/network/:/etc/network
      - /etc/frr/:/etc/frr
      - /var/run/dbus:/var/run/dbus
      - /run/systemd/private:/run/systemd/private
      - /certs/nsq:/certs:ro
    systemd_docker_cap_add:
      - sys_admin
    systemd_service_environment:
      TZ: "{{ timezone }}"
      METAL_CORE_CIDR: "{{ metal_core_cidr }}"
      METAL_CORE_LOOPBACK_IP: "{{ lo }}"
      METAL_CORE_PARTITION_ID: "{{ partition_id }}"
      METAL_CORE_RACK_ID: "{{ partition_rack_id }}"
      METAL_CORE_BIND_ADDRESS: 0.0.0.0
      ...
```
