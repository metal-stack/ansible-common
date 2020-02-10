# gcp-destroy

Destroys a Kubernetes cluster at the GCP.

You can use the [gcp-auth](roles/gcp-auth) to authenticate before destroying the cluster.

## Requirements

- gcloud CLI (https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu?hl=de)

## Variables

| Name                      | Mandatory | Description                                                            |
| ------------------------- | --------- | ---------------------------------------------------------------------- |
| gcp_project               | yes       | the gcp project name to use for the invocation                         |
| gcp_cluster_name          | yes       | the name of the gcp cluster                                            |
| gcp_location              | yes       | the location to create the gcp cluster in                              |
| gcp_service_account       | yes       | the name of the account to use for the invocation                      |
