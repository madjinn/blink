#!/bin/bash
set -e

(
    cd xcfs
    swift package resolve
)

python3 scripts/patch_openssl_deployment_target.py

echo "done"
