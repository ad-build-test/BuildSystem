"""
Desc: Deployment controller, handles deployments

Usage: python3 deployment_controller.py
note - this would have to run 24/7 as a service
"""
import os
import subprocess
import datetime
import yaml
import logging
import ansible_api
from artifact_api import ArtifactApi

import uvicorn
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import deployment_controller
import unittest
from datetime import datetime

def main_tests():
    ioc = ''
    component = 'test-ioc'
    # test 1
    print("Testing - deployment_controller.find_component_in_facility(facility='LCLS', app_type='ioc', component='test-ioc)" )
    print(deployment_controller.find_component_in_facility(facility='LCLS', app_type='ioc', component_to_find='test-ioc'))
    # test 2
    print("Testing - deployment_controller.find_facility_an_ioc_is_in(ioc='sioc-b34-test1', component='test-ioc')" )
    print(deployment_controller.find_facility_an_ioc_is_in(ioc_to_find='sioc-b34-test1', component_with_ioc='test-ioc'))
    # test 3

class TestDeploymentController(unittest.TestCase):
    def test_deploy_all(self):
        component_info = deployment_controller.find_component_in_facility('LCLS', 'ioc', 'test-ioc')
        results = [ioc['name'] for ioc in component_info['iocs']]
        print(results)
        self.assertIsNotNone(results)

    def test_find_component_in_facility(self):
        self.assertIsNotNone(deployment_controller.find_component_in_facility(facility='LCLS', app_type='ioc', component_to_find='test-ioc'),
                              msg="find_component_in_facility(facility='LCLS', app_type='ioc', component_to_find='test-ioc')")

    def test_find_facility_an_ioc_is_in(self):
        self.assertIsNotNone(deployment_controller.find_facility_an_ioc_is_in(ioc_to_find='sioc-b34-test1', component_with_ioc='test-ioc'),
                              msg="deployment_controller.find_facility_an_ioc_is_in(ioc_to_find='sioc-b34-test1', component_with_ioc='test-ioc')")

    def test_update_component_in_facility(self):
        timestamp = datetime.now().isoformat()
        self.assertIsNotNone(deployment_controller.update_component_in_facility(facility='LCLS', timestamp=timestamp, user='pnispero', app_type='ioc', component_to_update='test-ioc', tag='test-ioc-1.0.2', ioc_list=['sioc-b34-test1']),
                              msg="deployment_controller.update_component_in_facility(facility='LCLS', timestamp=timestamp, user='pnispero', app_type='ioc', component_to_update='test-ioc', tag='test-ioc-1.0.2', ioc_list=['sioc-b34-test1']")
        print("Updates test_deployment_destinations.yaml")

def test():

    # Data structure with 'apps' key containing a list of dictionaries
    data = {
        'apps': [
            {'name': 'app1', 'tag': 'app1.0'},
            {'name': 'app2', 'tag': 'app1.0'}
        ]
    }

    # Extract the 'name' from each dictionary in the list
    app_names = [app['name'] for app in data['apps']]

    # Output the result
    print(app_names)
    print(data['apps'])

    # List of dictionaries
    list_of_dicts = [
        {'facility': 'Facility1', 'app': 'App1'},
        {'facility': 'Facility2', 'app': 'App2'},
        {'app': 'App3'}
    ]

    # Key to check
    key_to_find = 'facility'

    # Initialize a flag to track if the key is found
    key_exists = False

    # Loop through the list of dictionaries
    for d in list_of_dicts:
        print(d)
        if key_to_find in d:
            print(d)

if __name__ == "__main__":
    # test()
    input("before continuing, ensure the config file is test_deployment_destinations.yml. (Enter to continue)")
    # main_tests()
    unittest.main()