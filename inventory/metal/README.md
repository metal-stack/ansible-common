### Metal Dynamic Inventory

Dynamic inventory for metal-stack. It uses `metalctl`, which needs to be configured properly in order to work.

There is also a configuration file `metal_inventory_config.yaml`, to which the path can be set via environment variable `METAL_ANSIBLE_INVENTORY_CONFIG`. The configuration file can be used to provide a mapping for machine IPs, which is sometimes useful when an IP address was not auto-configured in Metal.
