#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: my_test

short_description: This is my test module

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This is my longer description explaining my test module.

options:
    name:
        description: This is the message to send to the test module.
        required: true
        type: str
    new:
        description:
            - Control to demo if the result of this module is changed or not.
            - Parameter description can be a list as well.
        required: false
        type: bool
# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
# extends_documentation_fragment:
#     - my_namespace.my_collection.my_doc_fragment_name

author:
    - Your Name (@yourGitHubHandle)
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''

from ansible.module_utils.basic import AnsibleModule

def deploy_registry():
    # TODO: make a registry-deployment/ directory
    # Cloning BuildSystem already done from artifact_api
    # 1) kubectl apply -k BuildSystem/artifact_storage/registry-deployment/
    pass
def deploy_artifact_api():
    # 1) git clone https://github.com/ad-build-test/BuildSystem.git
    # 2) kubectl apply -k BuildSystem/artifact_storage/artifact-deployment/
    pass
def deploy_core_build_system():
    # 1) git clone https://github.com/eed-web-application/core-build-system-deployment.git
    # 2) kubectl apply -k core-build-system-deployment/test/
    pass
def deploy_percona_mongodb():
    # 1) git clone https://github.com/eed-web-application/eed-accel-webapp-clusters-wide-setup.git
    # 2) kubectl apply --server-side -f eed-accel-webapp-clusters-wide-setup/test/mongodb-operator/resource-1.15.0.yaml
    pass

def deploy_build_system() -> dict:
    output = {"msg1": "msg1", "msg2": "msg2"}
    print("deploy_ioc() called")
    
    # 1) mkdir temp/ && cd temp/

    # 2) Deploy mongodb percona server
    deploy_percona_mongodb()
    # 3) Deploy core-build-system
    deploy_core_build_system()
    # 4) Deploy artifact-api
    deploy_artifact_api()
    # 5) Deploy registry
    deploy_registry()
    # 6) Nuke temp folder: rm -rf temp/

    return output

def ansible_run_module():
    """
    This is the default ansible module boilerplate code + some custom args
    In order to run it through a playbook
    """
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type='str', required=True),
        dev=dict(type='bool', required=False, default=False),
        prod=dict(type='bool', required=False, default=False),
        new=dict(type='bool', required=False, default=False)
    )
    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        original_message='',
        message='',
        custom_output=dict
    )
    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result['custom_output'] = deploy_build_system()
    
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)
    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    result['original_message'] = module.params['name']
    result['message'] = 'goodbye'
    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    if module.params['new']:
        result['changed'] = True
    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    if module.params['name'] == 'fail me':
        module.fail_json(msg='You requested this to fail', **result)
    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    ansible_run_module()


if __name__ == '__main__':
    main()