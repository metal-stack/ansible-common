#!/bin/bash
failed=0

for file in $(find . -name test -type d -not -path "./venv/*" -not -path "./test/integration/*"); do
    echo "Running tests in $(dirname $file)"
    python -m unittest discover -v -p '*_test.py' -s $(dirname $file) || failed=1
done

if [ $failed -eq 0 ]; then
    echo "All tests passed."
else
    echo "One or more tests have failed."
    exit 1
fi
