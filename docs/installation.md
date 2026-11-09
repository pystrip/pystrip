# Installation

pystrip is published on [PyPI](https://pypi.org/project/pystrip/) and requires
Python 3.11 or newer.

=== "pip"

    ```bash
    pip install pystrip
    ```

=== "pipx"

    ```bash
    pipx install pystrip
    ```

=== "uv"

    ```bash
    uv tool install pystrip
    ```

## Run without installing

Both `pipx` and `uv` can run pystrip in a one-off environment:

```bash
pipx run pystrip . --check
uvx pystrip . --check
```

## Verify the installation

```bash
pystrip --help
```

## Pinning a version

For reproducible CI, pin an exact version:

```bash
pip install "pystrip==1.5.0"
```

See the [changelog](changelog.md) for released versions.
