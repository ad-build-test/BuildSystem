from setuptools import setup

setup(
    name='bs_main',
    version='0.1.0',
    py_modules=['bs_main'],
    install_requires=[
        'Click',
        'requests',
        'gitpython'
    ],
    entry_points={
        'console_scripts': [
            'bs_main = bs_main.__main__:entry_point',
        ],
    },
)