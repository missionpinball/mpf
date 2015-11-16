unit:
	python -m unittest discover -s tests

unit-verbose:
	python -m unittest discover -v -s tests

coverage:
	coverage run -m unittest discover -s tests
	coverage html
