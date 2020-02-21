# helm-chart

Installs a helm chart.

## Requirements

- helm

## Variables

| Name                          | Mandatory | Description                                                                                            |
| ----------------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| helm_chart                    | yes       | The reference to the helm chart                                                                        |
| helm_target_namespace         | yes       | The target namespace to deploy the helm chart to                                                       |
| helm_release_name             | yes       | The release name of the helm deployment                                                                |
| helm_chart_version            |           | The version of the chart                                                                               |
| helm_value_file_template      |           | The path to a helm value file (e.g. from the role's templates folder)                                  |
| helm_config_params            |           | Values to pass to helm via the `--set` option                                                          |
| helm_kubeconfig               |           | Adds the `--kubeconfig` option to point helm to another than the default kubeconfig path               | 
| helm_force                    |           | Adds the `--force` option                                                                              |
| helm_repo                     |           | Adds the chart repository URL                                                                          |
| helm_wait                     |           | Adds the `--wait` option                                                                               |
| helm_timeout                  |           | Waits the given period of time before giving up when used in conjunction with `--wait`                 |
| helm_bin                      |           | Alternative path to the helm binary                                                                    |
| helm_chart_remote_temp        |           | The path on the target host where the values file is templated to                                      |
| helm_chart_custom_folder      |           | The path to a local helm chart                                                                         |
| helm_chart_inject_config_hash |           | Injects a hash over all config values to the `helm_config_params`, which can then be used in the chart |

## Examples

```
- name: Deploy metal control plane
  include_role:
    name: ansible-common/roles/helm-chart
  vars:
    helm_chart_custom_folder: "{{ playbook_dir }}/roles/metal/files/metal-control-plane"
    helm_chart: "./metal-control-plane"
    helm_release_name: metal-control-plane
    helm_target_namespace: "meta-control-plane"
    helm_value_file_template: metal-values.j2
    # deployment can take a while due to post install hooks, therefore increasing the timeout for this chart...
    helm_timeout: 600s
    helm_chart_inject_config_hash: yes
```
