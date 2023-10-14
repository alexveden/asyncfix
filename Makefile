PROJ_ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

p ?= $(PROJ_ROOT)

.PHONY: tests coverage coverage-report complexity pypi pre-commit docs

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

docs:
	lazydocs \
    --output-path="./docs/reference" \
    --overview-file="README.md" \
    --src-base-url="https://github.com/alexveden/asyncfix/blob/main/" \
    asyncfix
	
	# Check validity of docs
	pydocstyle --convention=google ./asyncfix/

