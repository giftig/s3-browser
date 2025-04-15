build: fmt
build: test

bootstrap:
	@scripts/bootstrap.sh

fmt:
	# Fix up imports
	ruff check --select I,F401 --fix
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
