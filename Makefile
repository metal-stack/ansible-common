TEST_IMAGE := $(or $(TEST_IMAGE),ghcr.io/metal-stack/metal-deployment-base:metal-stack-release-vector)

ifeq ($(CI),true)
  DOCKER_RUN_ARG=
else
  DOCKER_RUN_ARG=t
endif

.PHONY: test
test: pull test-units test-integration

.PHONY: pull
pull:
	docker pull $(TEST_IMAGE)

.PHONY: test-units
test-units:
	docker run --rm -i$(DOCKER_RUN_ARG) -v $(PWD):/work -w /work $(TEST_IMAGE) make test-local

.PHONY: test-integration
test-integration:
	docker stop ansible-common-test-registry || true
	docker run --rm -d -p 5000:5000 --name ansible-common-test-registry registry:3
	cd test/integration && ./fill-test-registry.sh
	docker run --rm -i$(DOCKER_RUN_ARG) -v $(PWD):/work -w /work --network host \
		-e ANSIBLE_LIBRARY=library \
		-e ANSIBLE_ACTION_PLUGINS=action_plugins \
		-e ANSIBLE_COLLECTIONS_PATH="" \
		-e ANSIBLE_COLLECTIONS_SCAN_SYS_PATH=false \
		-e ANSIBLE_INVENTORY=test/integration/inventory.yaml \
		$(TEST_IMAGE) bash -c \
			'ansible -m metal_stack_release_vector localhost && ansible-playbook test/integration/playbook.yaml -v'
	docker stop ansible-common-test-registry

.PHONY: test-local
test-local:
	python3 -m pip install mock
	./test.sh
