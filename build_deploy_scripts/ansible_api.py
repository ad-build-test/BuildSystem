import os
import subprocess
import sys

def run_ansible_playbook(inventory, playbook, host_pattern, extra_vars, custom_env=None):
        os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
        command = [
            'ansible-playbook', 
            '-i', inventory,
            '-l', host_pattern,
            playbook
        ]

        if extra_vars:
            # Convert extra_vars dictionary to JSON string
            # extra_vars_str = json.dumps(extra_vars)
            # extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
            command += ['--extra-vars', extra_vars]
        # logging.info(command)
        print(command)

        # Determine the appropriate arguments based on the Python version
        if sys.version_info >= (3, 7):
            # For Python 3.7 and above
            text = {
                'text': True
            }
        else:
            # For Python 3.6 and below
            text = {
                'universal_newlines': True
            }

        # Use subprocess.Popen to forward output directly
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **text,
            env=custom_env
        )

        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')  # Print each line as it is output

        # Ensure all stderr is also handled
        for line in iter(process.stderr.readline, ''):
            print(line, end='')

        process.stdout.close()
        process.stderr.close()
        return_code = process.wait()
        return return_code