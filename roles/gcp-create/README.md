# gcp-create

Creates a Kubernetes cluster at the GCP.

You can use the [gcp-auth](roles/gcp-auth) to authenticate before creating the cluster.

## Requirements

- gcloud CLI (https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu?hl=de)

## Variables

| Name                      | Mandatory | Description                                                            |
| ------------------------- | --------- | ---------------------------------------------------------------------- |
| gcp_project               | yes       | the gcp project name to use for the invocation                         |
| gcp_cluster_name          | yes       | the name of the gcp cluster                                            |
| gcp_location              | yes       | the location to create the gcp cluster in                              |
| gcp_k8s_version           |           | the k8s version of the gcp cluster                                     |
| gcp_machine_type          | yes       | the machine type to use for the gcp cluster worker nodes               |
| gcp_disk_size_gb          | yes       | the disk size to use for the gcp cluster worker nodes                  |
| gcp_initial_node_count    | yes       | the initial worker node count of the gcp cluster                       |
| gcp_autoscaling_min_nodes |           | the minimum number of worker nodes for the gcp cluster node autoscaler |
| gcp_autoscaling_max_nodes |           | the maximum number of worker nodes for the gcp cluster node autoscaler |
| gcp_service_account       | yes       | the name of the account to use for the invocation                      |
