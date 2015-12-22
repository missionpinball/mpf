unit:
	python3 -m unittest discover -s tests

unit-verbose:
	python3 -m unittest discover -v -s tests

coverage:
	coverage run -m unittest discover -s tests
	coverage html
