# BuildSystem Command Line Interface
## Desc
0. Assuming you have the /dist, install package with ```pip install dist/adbs_cli-1.0.0-py3-none-any.whl```
1. Run with ```bs```
2. ex: ```bs run build```

## Dev
1. To install package in 'editable mode', just do a ```pip install -e .``` assuming you are the bs_cli/ directory (top of the source code dir)
2. To rebuild the package distribution, please update the `version` in setup.py
3. Then you can do ```python3 -m build``` assuming you are at the bs_cli/ directory (top of the source code dir)

