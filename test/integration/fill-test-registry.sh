#!/bin/bash
set -eo pipefail

echo "fill registry with sample release vectors and roles"

cd testdata/vectors/simple
rm -f release.tar.gz
tar -czvf release.tar.gz release.yaml
digest=$(oras push localhost:5000/releases:simple \
    --artifact-type application/vnd.metal-stack.release-vector.v1 \
    release.tar.gz:application/vnd.metal-stack.release-vector.v1.tar+gzip \
    --format go-template \
    --template "{{ .digest }}")
cd -

cd testdata/vectors/nested
rm -f release.tar.gz
tar -czvf release.tar.gz release.yaml
digest=$(oras push localhost:5000/releases:nested \
    --artifact-type application/vnd.metal-stack.release-vector.v1 \
    release.tar.gz:application/vnd.metal-stack.release-vector.v1.tar+gzip \
    --format go-template \
    --template "{{ .digest }}")
cd -

cd testdata/roles
tar -cpvzf ansible-test.tar.gz ansible-test
digest=$(oras push localhost:5000/ansible-test:v1.0.0 \
    --artifact-type application/vnd.metal-stack.release-vector.v1 \
    ansible-test.tar.gz:application/vnd.metal-stack.ansible-role.v1.tar+gzip \
    --format go-template \
    --template "{{ .digest }}")
cd -
