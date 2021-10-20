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

## Example usage

![Usage example][usage-1]

## Development

### Running tests

Install the project into your virtualenv in development mode:

```bash
pip install -e .
```

Then install the test requirements:

```bash
pip install -r requirements_test.txt
```

and finally run `./build.sh` to run the full build.

[usage-1]: readme-resources/usage-1.png "Usage example"
