# S3 Browser

![Latest tag](https://img.shields.io/github/v/tag/giftig/s3-browser)
![Build status](https://github.com/giftig/s3-browser/actions/workflows/build.yml/badge.svg)
![MIT License](https://img.shields.io/github/license/giftig/s3-browser)

A small, interactive tool to browse s3 like a regular directory structure

Written in python.

## Features
  * Autocompletion and command history, powered by [prompt toolkit][prompt-toolkit]
  * Familiar interface for unix users (`cd`, `ls`, `file`, `pwd`, etc.)
  * Bookmarking (`bookmark add`, `bookmark ls`...)
  * Inspect key metadata (`file`) or contents (`cat`)
  * Download or upload individual keys to/from local files (`put` or `get`)
  * Lazy-loading and caching of paths (no scanning entire buckets on start up)

## Installation

`pip install s3_browser`

And then run with `s3-browser`.

## Example usage

![Usage example][usage-1]

## Development

You'll need `uv` and `ruff` to work with this project.

### Running tests

This project uses `make` for ease of use. You can run tests by simply running:

```bash
make test
```

Use `make` to run the full build, including tests with `pytest` and formatting and
linting with `ruff`.

### Testing against minio

You can test against [minio](https://github.com/minio/minio) by running `make bootstrap` to start
a minio container and create a test bucket. You can then connect to it with:

```bash
export AWS_ACCESS_KEY_ID=minio
export AWS_SECRET_ACCESS_KEY=minio123
uv run s3-browser --endpoint http://localhost:19000
```

## Releasing

Create a source distribution with setup.py and upload it to pypi with twine:

`make dist && make dist/release`

[prompt-toolkit]: https://python-prompt-toolkit.readthedocs.io/en/master/
[usage-1]: readme-resources/usage-1.png "Usage example"
