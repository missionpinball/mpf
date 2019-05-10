"""Mission Pinball Framework (mpf) setup.py."""

import re

from setuptools import setup

#  http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
VERSIONFILE = "mpf/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

setup(

    name='mpf',
    version=verstr,
    description='Mission Pinball Framework',
    long_description='''Let's build a pinball machine!

The Mission Pinball Framework (MPF) is an open source, cross-platform,
Python-based software framework for powering real pinball machines.

MPF is written in Python. It can run on Windows, OS X, and Linux
with the same code and configurations.

MPF interacts with real, physical pinball machines via modern pinball
controller hardware such as a Multimorphic P-ROC or P3-ROC, a FAST Pinball
controller, or Open Pinball Project hardware controllers. You can use MPF to
power your own custom-built machine or to update the software in existing
Williams, Bally, Stern, or Data East machines.

MPF is a work-in-progress that is not yet complete, though we're actively
developing it and checking in several commits a week. It's MIT licensed,
actively developed by fun people, and supported by a vibrant, pinball-loving
community.''',

    url='http://missionpinball.org',
    author='The Mission Pinball Framework Team',
    author_email='brian@missionpinball.org',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Artistic Software',
        'Topic :: Games/Entertainment :: Arcade'

    ],

    keywords='pinball',

    include_package_data=True,

    package_data={'': ['*.yaml', '*.png', '*.so', '*.pyd', '*.ogg', '*.wav']},

    # MANIFEST.in picks up the rest
    packages=['mpf'],

    zip_safe=False,


    install_requires=['ruamel.yaml==0.15.37',
                      'pyserial>=3.2.0',
                      'pyserial-asyncio>=0.3',
                      'sortedcontainers',
                      'typing',
                      'asciimatics>=1.11.0',
                      'terminaltables',
                      'psutil',
                      # asciimatic depends on pypiwin32 but newer version will not install
                      'pypiwin32>=223;platform_system=="Windows" and python_version>"3.4"',
                      'pypiwin32<=219;platform_system=="Windows" and python_version=="3.4"'],

    tests_require=[],
    test_suite="mpf.tests",

    entry_points={
        'console_scripts': [
            'mpf = mpf.commands:run_from_command_line',
        ]
    }
)
