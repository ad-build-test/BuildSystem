import json
import os
print('Hello World')
print(os.getcwd())
print('Print contents of build_config.json:')
with open('build_config.json') as f:
    d = json.load(f)
    print(d)