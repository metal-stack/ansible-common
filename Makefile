.PHONY: test
test:
	python3 -m pip install mock
	./test.sh

.PHONY: test-local
test-local:
	docker pull metalstack/metal-deployment-base:latest
	docker run --rm -it -v $(PWD):/work -w /work metalstack/metal-deployment-base:latest make test
