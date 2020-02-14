# Vagrant Dynamic Inventory

This is a dynamic inventory, using `vagrant ssh-config` commands to build the inventory.

## Configuration

You can parameterize the dynamic inventory by setting environment variables.

| Name                          | Default                                        | Description                                                                                                        |
| ----------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| ANSIBLE_VAGRANT_DIRECTORY     | `<current working directory>`                  | The folder that contains the Vagrantfile                                                                           |
| ANSIBLE_VAGRANT_HOST_SELECTOR |                                                | Only queries specific hosts, comma-separated, from your Vagrantfile for ssh-config (can be useful for performance) |
| ANSIBLE_VAGRANT_USE_CACHE     | false                                          | Whether to cache the inventory in a file or not                                                                    |
| ANSIBLE_VAGRANT_CACHE_MAX_AGE | 600                                            | Time in seconds until the cache expires, when set to zero the cache never expires                                  |
| ANSIBLE_VAGRANT_CACHE_FILE    | `<inventory directory>`/.ansible_vagrant_cache | Location of the cache file                                                                                         |
