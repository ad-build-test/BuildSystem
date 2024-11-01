import os
import subprocess
import sys
import logging

logger = logging.getLogger('my_logger')

def run_ansible_playbook(inventory, playbook, host_pattern, extra_vars, custom_env):
        os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
        command = []
        if (custom_env['ADBS_OS_ENVIRONMENT'].lower() == 'rhel7'): # Special case for rhel7
            command += ['python3', '-m', 'ansible', 'playbook']
        else:
             command += ['ansible-playbook']
        command += [
            '-i', inventory,
            '-l', host_pattern,
            playbook
        ]

        if extra_vars:
            # Convert extra_vars dictionary to JSON string
            # extra_vars_str = json.dumps(extra_vars)
            # extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
            command += ['--extra-vars', extra_vars]

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
        logger.info("Running ansible playbook...")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **text,
            env=custom_env
        )

        # logger.info output in real-time
        for line in iter(process.stdout.readline, ''):
            logger.debug(line.strip())  # Print each line as it is output

        # Ensure all stderr is also handled
        for line in iter(process.stderr.readline, ''):
            logger.debug(line.strip())

        process.stdout.close()
        process.stderr.close()
        return_code = process.wait()
        return return_code