build: fmt
build: test

fmt:
	ruff format

test:
	uv run pytest --cov=s3_browser

install:
	uv sync

dist:
	uv run ./setup.py sdist && uv run twine check dist/*

dist/clean:
	rm -rf dist/

dist/release:
	uv run twine upload dist/* --repository s3_browser
