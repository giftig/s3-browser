build: fmt
build: test

fmt:
	black . && flake8 . && isort .

test:
	pytest --cov=s3_browser


install:
	pip install -e .
	pip install -r requirements_test.txt

dist:
	./setup.py sdist && twine check dist/*

dist/clean:
	rm -rf dist/

dist/release:
	twine upload dist/* --repository s3_browser
