# S3 Browser

![Latest tag](https://img.shields.io/github/v/tag/giftig/s3-browser)
![Build status](https://github.com/giftig/s3-browser/actions/workflows/build.yml/badge.svg)
![MIT License](https://img.shields.io/github/license/giftig/s3-browser)

A small, interactive tool to browse s3 like a regular directory structure

Written in python.

## Features
  * Tab completion
  * Familiar interface for unix users (`cd`, `ls`, `file`, `pwd`, etc.)
  * Bookmarking (`bookmark add`, `bookmark ls`...)
  * Inspect key metadata (`file`) or contents (`cat`)
  * Download or upload individual keys to/from local files (`put` or `get`)
  * Maintains command history
  * Lazy-loading and caching of paths (no scanning entire buckets on start up)

## Installation

`pip install s3_browser`

And then run with `s3-browser`.

## Example usage

![Usage example][usage-1]

## Development

### Running tests

This project uses `make` for ease of use. You can install the project in development mode,
and install the test requirements, using the `install` target:

```bash
make install
```

It's recommended to create and activate a virtual environment first. There are a number of ways
to do that; I like [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/).

Use `make` to run the full build.

[usage-1]: readme-resources/usage-1.png "Usage example"

## Releasing

Create a source distribution with setup.py and upload it to pypi with twine:

`make dist && make dist/release`
