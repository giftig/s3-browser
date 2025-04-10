build: fmt
build: test

fmt:
	ruff format

test:
	uv run pytest --cov=s3_browser

install:
	uv sync

dist:
	uv build

dist/clean:
	rm -rf dist/

dist/release:
	uv publish
