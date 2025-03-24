"""
Desc: TEST Deployment controller, handles deployments

SETUP: This test deployment controller needs the working
mongodb running on kubernetes, and would require your home directory
to be used ~/test-deployment-controller/
And make the following dirs:
1) cd ~/test-deployment-controller/ && mkdir scratch app 
2) git clone https://github.com/ad-build-test/build-system-playbooks
3) Then in mock_paths(), alter the paths to your local ~/test-deployment-controller/

Usage: pytest test_deployment_controller.py
or pytest -v test_deployment_controller.py -s

POST TEST: 
1) Even if tests say pass, check the database yourself to see if it added the right items
    1.1) There should be a new deployment with the following info:

    name: "test-ioc"
    facility: "test"
    tag: "1.0.58"
    type: "ioc"
    dependsOn: Array (2)
    0: Object
        name: "sioc-b34-gtest01"
        tag: "1.0.58"

    1: Object
        name: "sioc-b34-gtest02"
        tag: "1.0.58"
2) Please delete the new deployment you made which is test-ioc at facility 'test' then can
rerun test
TODO: We should make an api in backend to delete deployment, then we can run that as post test
Then we really have a self-contained test without any need for POST operations

"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
from deployment_controller import app, IocDict, BasicIoc
import os
from httpx import AsyncClient, ASGITransport
import asyncio
from fastapi.responses import FileResponse

client = TestClient(app)

@pytest.fixture(autouse=True)
def set_test_environment():
    os.environ['PYTHON_TESTING'] = 'True'
    yield
    os.environ.pop('PYTHON_TESTING', None)

@pytest.fixture
def mock_paths():
    with patch('deployment_controller.ANSIBLE_PLAYBOOKS_PATH', '/home/pnispero/test-deployment-controller/build-system-playbooks/'), \
         patch('deployment_controller.INVENTORY_FILE_PATH', '/home/pnispero/test-deployment-controller/build-system-playbooks/global_inventory.ini'), \
         patch('deployment_controller.CONFIG_FILE_PATH', '/home/pnispero/test-deployment-controller/build-system-playbooks/config.yaml'), \
         patch('deployment_controller.SCRATCH_FILEPATH', '/home/pnispero/test-deployment-controller/scratch/'), \
         patch('deployment_controller.BACKEND_URL', 'https://ad-build-dev.slac.stanford.edu/api/cbs/v1/'), \
         patch('deployment_controller.APP_PATH', '/home/pnispero/test-deployment-controller/app/'), \
         patch('deployment_controller.FACILITIES', ['test', 'LCLS', 'FACET', 'TESTFAC', 'DEV', 'S3DF']):
        yield

####### Tests for get_ioc_component_info
def test_get_ioc_component_info_success(mock_paths):
    response = client.request("GET", "/ioc/info", json={"component_name": "test-ioc"})
    
    assert response.status_code == 200
    print(f"payload: {response.json()['payload']}")

def test_get_ioc_component_info_not_found(mock_paths):
    
    response = client.request("GET", "/ioc/info", json={"component_name": "non_existent_ioc"})
    
    assert response.status_code == 404
    print(f"payload: {response.json()['payload']}")

####### Tests for deploy_ioc
@pytest.mark.asyncio
async def test_deploy_ioc_new_component_success(mock_paths):
    print("Starting test_deploy_ioc_new_component_success - add a new component entirely\n \
          bs deploy --facility test -i sioc-b34-gtest01 -t 1.0.57 -u")
    
    ioc_request = IocDict(
        facilities=["test"],
        component_name="test-ioc",
        tag="1.0.57",
        ioc_list=["sioc-b34-gtest01"],
        user="test_user",
        new=True
    )
    
    print("Sending request to /ioc/deployment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
    print(f"Received response with status code: {response.status_code}")
    
    assert response.status_code == 200
    assert "Deployment report" in response.text
    assert "Success" in response.text

@pytest.mark.asyncio
async def test_deploy_ioc_new_ioc_success(mock_paths):
    print("Starting test_deploy_ioc_new_ioc_success - add a new ioc to an existing component\n \
          bs deploy --facility test -i sioc-b34-gtest02 -t 1.0.57 -u")
    
    ioc_request = IocDict(
        facilities=["test"],
        component_name="test-ioc",
        tag="1.0.57",
        ioc_list=["sioc-b34-gtest02"],
        user="test_user",
        new=True
    )
    
    print("Sending request to /ioc/deployment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
    print(f"Received response with status code: {response.status_code}")
    
    assert response.status_code == 200
    assert "Deployment report" in response.text
    assert "Success" in response.text

@pytest.mark.asyncio
async def test_deploy_ioc_new_tag_all_success(mock_paths):
    print("Starting test_deploy_ioc_new_tag_all_success - deploy new tag to an existing component with ALL iocs\n \
          bs deploy --facility test -i ALL -t 1.0.58")
    
    test_facility = "test"
    test_component = "test-ioc"
    test_tag = "1.0.58"
    test_ioc_list = "ALL"
    test_user = "test_user"
    test_new = False

    ioc_request = IocDict(
        facilities=[test_facility],
        component_name=test_component,
        tag=test_tag,
        ioc_list=[test_ioc_list],
        user=test_user,
        new=test_new
    )
    
    print("Sending request to /ioc/deployment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
    print(f"Received response with status code: {response.status_code}")
    
    assert response.status_code == 200
    assert "Deployment report" in response.text
    assert "Success" in response.text

    print("Confirm deployment database contents are correct...")
    response = client.request("GET", "/ioc/info", json={"component_name": "test-ioc"})
    payload = response.json()['payload']
    print(f"payload: {payload}")
    details = []
    # Loop through the list of deployment entries (one for each facility if exists)
    for deployment in payload:
        # Extract the inner dictionary (assuming there's only one item at the top level)
        for facility, details in deployment.items():
            if (facility == test_facility):
                assert details['name'] == test_component
                assert details['tag'] == test_tag
                assert details['type'] == 'ioc'
            # # Loop through the 'dependsOn' list and print each entry
                dependencies = details['dependsOn']
     # Check if both entries exist
    assert any(dep['name'] == 'sioc-b34-gtest01' and dep['tag'] == test_tag for dep in dependencies), "sioc-b34-gtest01 not found or tag mismatch"
    assert any(dep['name'] == 'sioc-b34-gtest02' and dep['tag'] == test_tag for dep in dependencies), "sioc-b34-gtest02 not found or tag mismatch"

# @pytest.mark.asyncio
# async def test_deploy_ioc_failure(mock_external_dependencies, mock_paths):
#     print("Starting test_deploy_ioc_failure")
#     mock_get, mock_ansible, mock_find, mock_extract, mock_update, mock_log, mock_remove, mock_tarfile, mock_download, mock_write_file = mock_external_dependencies
    
#     # Mock failed ansible playbook execution
#     mock_ansible.return_value = ("", "Error output", 1)
    
#     ioc_request = IocDict(
#         facilities=["S3DF"],
#         component_name="test_ioc",
#         tag="v1.0.0",
#         ioc_list=["ALL"],
#         user="test_user",
#         new=False
#     )
    
#     print("Sending request to /ioc/deployment")
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
#         response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
#     print(f"Received response with status code: {response.status_code}")
    
#     assert response.status_code == 400
#     assert "Deployment report" in response.text
#     assert "Failure" in response.text
    
#     # Verify that necessary functions were called
#     print("Verifying function calls")
#     mock_get.assert_called()
#     mock_ansible.assert_called()
#     mock_find.assert_called()
#     mock_extract.assert_called()
#     mock_write_file.assert_called()
#     mock_remove.assert_called()
#     mock_tarfile.assert_called()
#     # Note: update and log might not be called in case of failure, depending on your implementation
#     print("Test completed successfully")