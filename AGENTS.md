# Agent Guidance

These instructions apply to the entire repository.

## Project Layout

- Runtime code lives in `src/mss`.
- Tests live in `src/tests`.
- Documentation lives in `docs/source`.
- `check.sh` and `check.ps1` are the maintainer-provided quality check entry points.

## Working Guidelines

- Keep changes focused on the issue or PR scope.
- Be careful with public API changes. Update docs and tests when behavior changes.
- Prefer the existing ctypes-based, dependency-free style for runtime code.
- Do not add runtime dependencies unless the issue explicitly calls for one.
- If AI assistance was used, disclose it in the pull request template and state which parts were AI-assisted.

## Validation

Install development dependencies:

```shell
python -m pip install -e ".[dev,tests]"
```

Run quality checks before submitting a PR:

```shell
./check.sh
```

On Windows:

```powershell
.\check.ps1
```

Run tests:

```shell
python -m pytest
```

On headless GNU/Linux environments, run tests with a virtual display:

```shell
xvfb-run python -m pytest
```

When documentation changes, install docs dependencies and build docs with warnings as errors:

```shell
python -m pip install -e ".[docs]"
sphinx-build -d docs docs/source docs_out --color -W -bhtml
```
