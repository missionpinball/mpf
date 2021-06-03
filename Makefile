unit:
	python3 -m unittest discover -s mpf/tests

unit-verbose:
	python3 -m unittest discover -v -s mpf/tests 2>&1

coverage:
	coverage3 run -m unittest discover -s mpf/tests
	coverage3 html

sphinx:
	cd docs/ && sphinx-build -b html -d _build/doctrees  -n -w BUILD_WARNINGS.txt . _build/html; cd ..

mypy:
	mypy -i mpf --exclude mpf/platforms/visual_pinball_engine/platform_pb2.py
