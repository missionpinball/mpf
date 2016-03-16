python -m pip install -U setuptools wheel pip mock --retries 20 --timeout 60
git clone file:///z/git/mpf c:\mpf
c:
cd /mpf
pip install . --retries 20 --timeout 60
python -m unittest discover -s mpf/tests
python setup.py bdist_wheel --dist-dir=%~dp0%/dist
python setup.py sdist --dist-dir=%~dp0%/dist  --formats=gztar
