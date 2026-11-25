PROJ_ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

p ?= $(PROJ_ROOT)

.PHONY: tests coverage coverage-report complexity lint fmt typecheck pypi pre-commit docs

pre-commit:
	pre-commit run --all-files

tests: 
	pytest $(p)

coverage: 
	coverage run -m  pytest -q --disable-warnings . && coverage html -i

coverage-report:
	open ./htmlcov/index.html 

complexity:
	ruff check $(p) --select C90

lint:
	ruff check $(p)

fmt:
	ruff format $(p)

typecheck:
	mypy

pypi:
	rm -f dist/*
	python -m build
	twine upload dist/* --verbose

docs:
	# Check validity of docs
	ruff check ./asyncfix/ --select D

	# Builds markdown docs 
	lazydocs \
    --output-path="./docs/reference" \
    --overview-file="README.md" \
    --src-base-url="https://github.com/alexveden/asyncfix/blob/main/" \
    asyncfix
	
	# Finishing and pushing to GH
	mkdocs gh-deploy
