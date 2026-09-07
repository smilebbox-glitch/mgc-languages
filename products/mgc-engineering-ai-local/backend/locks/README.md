# Python production locks

These files are deliberately not fabricated in the source package. Generate `requirements-{core,ai,advanced}.lock.txt` against the approved corporate Python mirror with `scripts/prepare_python_lock.py`. Each locked requirement must be exact and hash-pinned; the matching profile wheelhouse is verified separately.
