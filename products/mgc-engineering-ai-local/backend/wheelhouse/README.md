# Approved Python wheelhouse

Populate profile subdirectories with `scripts/prepare_python_lock.py`. Production/reproducible builds use `--no-index --require-hashes` and fail closed if the lock or wheelhouse manifest is absent or mismatched.
