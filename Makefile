unit:
	python3 -m unittest discover -s tests

unit-verbose:
	python3 -m unittest discover -v -s tests

coverage:
	python3-coverage run -m unittest discover -s tests
	python3-coverage html
