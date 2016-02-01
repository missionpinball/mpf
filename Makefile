unit:
	python3 -m unittest discover -s tests

unit-verbose:
	python3 -m unittest discover -v -s tests

coverage:
	coverage3 run -m unittest discover -s tests
	coverage3 html
