:: Tests installing mpf from the wheel. Assumes a blank system with nothing installed (except Python) to simulate a
:: fresh environment.

:: find the latest wheel
cd wheels
FOR /F "delims=|" %%I IN ('dir "mpf-*.whl" /b /o:-n ') DO SET mpf-wheel=%%I
pip install %mpf-wheel%
pip install mock
python -m unittest discover mpf
