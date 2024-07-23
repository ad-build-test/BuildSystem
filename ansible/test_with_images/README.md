# Ansible Test

This uses containers rather than vm's or actual machines for testing.

## Prereqs
1. ```pip3 install ansible```
2. docker - https://docs.docker.com/engine/install/

## How to run
How to run ```./setup-container.sh```

To test your own playbooks, add them to this directory, and specify the, in setup-container.sh in ```function run_ansible_playbook()```

