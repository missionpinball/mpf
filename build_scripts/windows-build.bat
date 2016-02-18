python -m pip install -U setuptools wheel pip mock
git clone file:///z/git/mpf c:\mpf
c:
cd /mpf
pip install .
python -m unittest discover -s mpf/tests
python setup.py bdist_wheel  --dist-dir=%~dp0%/wheels
