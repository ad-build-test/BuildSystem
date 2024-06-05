import time
import json
import os
print('Hello World')
while True:
    print('Print contents of build_config.json to avoid dying:')
    print(os.getcwd())
    with open('build_config.json') as f:
        d = json.load(f)
        print(d)
    time.sleep(10)
