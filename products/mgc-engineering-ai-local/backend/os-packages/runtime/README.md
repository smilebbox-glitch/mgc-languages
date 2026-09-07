# Offline OS package bundle

This directory is intentionally empty in the source release.

For a strict reproducible/offline build, run `scripts/prepare_os_package_bundle.sh`
on an approved corporate build host after resolving `PYTHON_BASE_IMAGE` to an immutable
`repo@sha256:digest`. The script downloads the Debian runtime packages required by the
backend image and writes `OS_PACKAGE_MANIFEST.json` with SHA-256 hashes.

The strict Docker build installs only the `.deb` files from this directory via `dpkg -i`.
It does not execute `apt-get update` or contact a Debian mirror during the application build.
