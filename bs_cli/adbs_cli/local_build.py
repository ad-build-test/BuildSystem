# Local build
import subprocess
import json
import os 
import sys

def run_ansible_playbook(inventory, playbook, host_pattern, extra_vars):
    os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
    command = [
        'ansible-playbook', 
        '-i', inventory,
        '-l', host_pattern,
        playbook
    ]

    if extra_vars:
        # Convert extra_vars dictionary to JSON string
        extra_vars_str = json.dumps(extra_vars)
        # extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
        command += ['--extra-vars', extra_vars_str]
    print(command)

    # Use subprocess.Popen to forward output directly
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Print output in real-time
    for line in iter(process.stdout.readline, ''):
        if sys.version_info >= (3, 6): # Python 3.6 or later
            print(line, end='')
        else:  # For Python 3.5 or earlier
            sys.stdout.write(line)  # Use sys.stdout.write to avoid newline

    # Ensure all stderr is also handled
    for line in iter(process.stderr.readline, ''):
        if sys.version_info >= (3, 6):  # Python 3.6 or later
            print(line, end='')
        else:  # For Python 3.5 or earlier
            sys.stdout.write(line)  # Use sys.stdout.write to avoid newline

    process.stdout.close()
    process.stderr.close()
    return_code = process.wait()
    return return_code

def local_build(manifest_data: dict, user_src_repo: str, component: str, branch: str):
    # Assuming the script exists at the $TOP of the repo
    print("== ADBS == Running Build:")
    if (manifest_data['build'].endswith('.sh')):
        build_script = './' + manifest_data['build']
        result = subprocess.run(['bash', build_script], capture_output=True, text=True)
    elif (manifest_data['build'].endswith('.py')):
        build_script = manifest_data['build']
        result = subprocess.run(['python', build_script], capture_output=True, text=True)
    else: # Run the command directly
        build_command = manifest_data['build']
        result = subprocess.run([build_command], capture_output=True, text=True)
    print('== ADBS == output:', result.stdout)
    print('== ADBS == errors:', result.stderr)
    playbook_args = f'{{"component": "{component}", "branch": "{branch}", \
        "user_src_repo": "{user_src_repo}"}}'
    # Convert the JSON-formatted string to a dictionary
    playbook_args_dict = json.loads(playbook_args)
    adbs_playbooks_dir = "/sdf/group/ad/eed/ad-build/registry/BuildSystem/" # TODO: Change this once official
    return_code = run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                            adbs_playbooks_dir + 'ioc_build.yml',
                            'S3DF',
                            playbook_args_dict)
    print("Playbook execution finished with return code:", return_code)

if __name__ == "__main__":
    if len(sys.argv) != 5:  # Ensure 4 arguments are passed
        print("Usage: python local_build.py <manifest_data> <user_src_repo> <component> <branch>")
        sys.exit(1)

    # Deserialize the JSON string back into a dictionary
    manifest_data = sys.argv[1]

    # Print raw argument for debugging (repr() shows invisible characters)
    print(f"Raw manifest_data: {repr(manifest_data)}")
    
    # Strip leading and trailing whitespace
    manifest_data = manifest_data.strip()
    print(manifest_data)
    
    try:
        manifest_data = json.loads(manifest_data)  # Deserialize JSON into a Python dictionary
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)

    user_src_repo = sys.argv[2]
    component = sys.argv[3]
    branch = sys.argv[4]
    local_build(manifest_data, user_src_repo, component, branch)