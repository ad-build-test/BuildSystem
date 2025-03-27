from setuptools import setup, find_packages
# Avoided using pyproject.toml, becuase can't get an editable version installed (pip install -e .)
setup(
    name='adbs_cli',
    version='1.0.1',
    description="Command line interface for the accelerator directorate build system (software factory)",
    author="Patrick Nisperos, Jerry Katzung, Claudio Bisegni",
    author_email="pnispero@slac.stanford.edu, katzung@slac.stanford.edu, bisegni@slac.stanford.edu",
    url="https://github.com/ad-build-test/BuildSystem",
    packages=find_packages(),
    install_requires=[
        "click==8.1.7",
        "requests==2.31.0",
        "pyyaml==6.0.1",
        "inquirer==3.2.4",
        "ansible_runner==2.4.0",
        "ansible-core==2.17.1",
        "GitPython==3.1.43"
    ],
    entry_points={
        'console_scripts': [
            'bs=adbs_cli.bs_main:main'
        ],
    },
)
