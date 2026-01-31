# Contributing

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev,pdf]'
```

## Run checks

```bash
ruff format .
ruff check .
pytest -q
```

## Notes

- Please do not commit PDFs (use `input_files/` locally; it is gitignored).

