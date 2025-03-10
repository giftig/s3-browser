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
	./setup.py sdist && twine check sdist/*

dist/release:
	twine upload sdist/*
