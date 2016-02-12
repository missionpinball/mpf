"""Mission Pinball Framework (mpf) setup.py"""

from setuptools import setup, find_packages

import mpf.core

setup(

    name='mpf',
    version=mpf.core.__version__,
    description='Mission Pinball Framework',
    long_description='''Let's build a pinball machine!

The Mission Pinball Framework (MPF) is an open source, cross-platform,
Python-based
software framework for powering real pinball machines.

MPF is written in Python. It can run on Windows, OS X, and Linux
with the same code and configurations.

MPF interacts with real, physical pinball machines via modern pinball
controller hardware such as the Multimorphic P-ROC or FAST Pinball
controller. You can use it to power your own custom-built machine or to
update the software in existing Williams, Bally, Stern, or Data East
machines.

MPF is a work-in-progress that is not yet complete, though we're actively
developing it and checking in several commits a week. It's MIT licensed,
actively developed by fun people, and supported by a vibrant pinball-loving
community.''',

    url='https://missionpinball.com/mpf',
    author='The Mission Pinball Framework Team',
    author_email='brian@missionpinball.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Artistic Software',
        'Topic :: Games/Entertainment :: Arcade'

    ],

    keywords='pinball',

    include_package_data=True,

    package_data={'': ['*.yaml', '*.png']},

    packages=find_packages(),

    zip_safe=True,

    install_requires=['ruamel.yaml', 'pyserial'],

    tests_require=['mock'],

    entry_points={
        'console_scripts': [
            'mpf = mpf.commands:run_from_command_line',
        ]
    }
)
