unit:
	python3 -m unittest discover -s tests

unit-verbose:
	python3 -m unittest discover -v -s tests 2>&1

coverage:
	coverage3 run -m unittest discover -s tests
	coverage3 html
