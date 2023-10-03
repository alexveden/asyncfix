PROJ_ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

p ?= $(PROJ_ROOT)

.PHONY: tests coverage coverage-report complexity pypi pre-commit

pre-commit:
	pre-commit run --all-files

tests: 
	pytest $(p)

coverage: 
	coverage run -m  pytest -q --disable-warnings . && coverage html -i

coverage-report:
	open ./htmlcov/index.html 

complexity:
	flake8 $(p) --max-complexity 10

pypi:
	rm -f dist/*
	python -m build
	twine upload dist/* --verbose
