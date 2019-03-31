# S3 Browser

A small, interactive tool to browse s3 like a regular directory structure

Written in python.

## Features
  * Tab completion
  * Familiar interface for unix users (`cd`, `ls`, `file`, `pwd`, etc.)
  * Bookmarking (`bookmark add`, `bookmark ls`...)
  * Inspect key metadata (`file`)
  * Maintains command history
  * Lazy-loading and caching of paths (no scanning entire buckets on start up)

## Installation

`pip install s3_browser`

And then run with `s3-browser`.

## Development

### Running tests

Just install the test requirements into your virtualenv:

```bash
pip install -r requirements_test.txt
```

and then run `./build.sh`.
