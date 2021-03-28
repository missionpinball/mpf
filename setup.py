"""Mission Pinball Framework (mpf) setup.py."""
import re
from setuptools import setup

#  http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
VERSIONFILE = "mpf/_version.py"
VERSION_STRING_LONG = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
_MO = re.search(VSRE, VERSION_STRING_LONG, re.M)
if _MO:
    VERSION_STRING = _MO.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

pin2dmd_requires = [
    'pyusb==1.1.0'
]

linux_i2c_requires = [
    'smbus2_asyncio==0.0.5'
]

rpi_requires = [
    'apigpio-mpf==0.0.3'
]

cli_requires = [
    'prompt_toolkit==3.0.8',
    'asciimatics==1.12.0',
    'terminaltables==3.1.0',
]

osc_requires = [
    'python-osc==1.7.4'
]

irc_requires = [
    'irc==19.0.1'
]

vpe_requires = [
    'grpcio_tools==1.34.0',
    'grpcio==1.34.0',
    'protobuf==3.14.0',
]


all_requires = (pin2dmd_requires + cli_requires + linux_i2c_requires + rpi_requires + osc_requires + irc_requires +
                vpe_requires)

setup(

    name='mpf',
    version=VERSION_STRING,
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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

    install_requires=['ruamel.yaml==0.15.100',
                      'pyserial==3.5',
                      'pyserial-asyncio==0.4;platform_system=="Windows"',
                      'pyserial-asyncio==0.5;platform_system!="Windows"',
                      'sortedcontainers==2.3.0',
                      'psutil==5.7.3',
                      ],

    extras_require={
        'all': all_requires,
        'pin2dmd': pin2dmd_requires,
        'linux_i2c': linux_i2c_requires,
        'rpi': rpi_requires,
        'cli': cli_requires,
        'osc': osc_requires,
        'irc': irc_requires,
        'vpe': vpe_requires,
    },

    tests_require=[],
    test_suite="mpf.tests",

    entry_points={
        'console_scripts': [
            'mpf = mpf.commands:run_from_command_line',
        ]
    }
)
