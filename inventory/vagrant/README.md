# Vagrant Dynamic Inventory

This is a dynamic inventory, using `vagrant ssh-config` commands to build the inventory. Make sure you execute this from the folder where your `Vagrantfile` is located.

If you want to run it from elsewhere and just point to the Vagrant directory instead, you can define the path to the folder using the `ANSIBLE_VAGRANT_DIRECTORY` environment variable.

If you only need to put certain hosts into your inventory and you want to speed up performance by not parsing every ssh-config from the machines defined in your `Vagrantfile`, you can set the `ANSIBLE_VAGRANT_HOST_SELECTOR` environment variables. This is a comma-separated list of host names from your `Vagrantfile` to include into the inventory.
