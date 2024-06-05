import time
import json
import os
print('Hello World')
while True:
    print('Print contents of build_config.json to avoid dying:')
    print(os.getcwd())
    os.chdir('/etc/build')
    print(os.getcwd())
    print(os.listdir(os.getcwd()))
    with open('/etc/build/build_config.json') as f:
        d = json.load(f)
        print(d)
    time.sleep(10)