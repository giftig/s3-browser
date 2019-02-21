# S3 Browser

A small, interactive tool to browse s3 like a regular directory structure

Written in python.

## Features
  * Tab completion on `cd` and `ls`
  * Maintains command history
  * Lazy-loading and caching of paths (no scanning entire buckets on start up)

## Installation

`pip install s3_browser`

## Development

### Running tests

Just install the test requirements into your virtualenv:

```bash
pip install -r requirements_test.txt
```

and then run `nosetests`.
