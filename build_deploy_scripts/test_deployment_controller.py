"""
Desc: TEST Deployment controller, handles deployments

Usage: pytest deployment_controller.py
or pytest -v deployment_controller.py

TODO:
1) Right now this is a working test module. But many of the functions are mocked, 
specificially the database ones so we don't need an actual database to test the fastapi
We can make this more realistic by essentially removing the patches, and let the 
fastapi use the real functions and call to the backend database. 
1.1) in that case, we would need to use a real database and change the test arguments.
And we could create tests for more cases instead of just general tests.
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
def mock_external_dependencies():
    with patch('deployment_controller.requests.get') as mock_get, \
         patch('deployment_controller.ansible_api.run_ansible_playbook') as mock_ansible, \
         patch('deployment_controller.find_component_in_facility') as mock_find, \
         patch('deployment_controller.extract_ioc_cpu_shebang_info') as mock_extract, \
         patch('deployment_controller.update_component_in_facility') as mock_update, \
         patch('deployment_controller.add_log_to_component') as mock_log, \
         patch('deployment_controller.write_file') as mock_write_file, \
         patch('os.remove') as mock_remove, \
         patch('tarfile.open') as mock_tarfile, \
         patch('deployment_controller.download_file_response') as mock_download:
        
        # Mock successful API response
        mock_get.return_value.status_code = 200
        
        # Mock component found
        mock_find.return_value = {
            'name': 'test_ioc',
            'facility': 'S3DF',
            'dependsOn': [{'name': 'sub_ioc1'}, {'name': 'sub_ioc2'}]
        }
        
        # Mock extracted IOC info
        mock_extract.return_value = [
            {'folder_name': 'sub_ioc1', 'architecture': 'linuxrt-x86_64', 'binary': 'ioc'},
            {'folder_name': 'sub_ioc2', 'architecture': 'rhel7-x86_64', 'binary': 'ioc'}
        ]
        
        # Mock successful component update and log addition
        mock_update.return_value = True
        mock_log.return_value = True
        
        # Mock tarfile operations
        mock_tarfile_instance = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tarfile_instance
        
        yield mock_get, mock_ansible, mock_find, mock_extract, mock_update, mock_log, mock_write_file, mock_remove, mock_tarfile, mock_download

# Tests for get_ioc_component_info
@patch('deployment_controller.find_component_in_facility')
@patch('deployment_controller.get_facilities_list')
def test_get_ioc_component_info_success(mock_get_facilities_list, mock_find_component_in_facility):
    mock_get_facilities_list.return_value = ['LCLS', 'FACET', 'TESTFAC', 'DEV', 'S3DF']
    mock_find_component_in_facility.side_effect = [
        None,
        None,
        None,
        None,
        {'name': 'test_ioc', 'facility': 'S3DF'}
    ]
    
    response = client.request("GET", "/ioc/info", json={"component_name": "test_ioc"})
    
    assert response.status_code == 200
    assert len(response.json()['payload']) == 1
    assert 'S3DF' in response.json()['payload'][0]

@patch('deployment_controller.find_component_in_facility')
@patch('deployment_controller.get_facilities_list')
def test_get_ioc_component_info_not_found(mock_get_facilities_list, mock_find_component_in_facility):
    mock_get_facilities_list.return_value = ['LCLS', 'FACET', 'TESTFAC', 'DEV', 'S3DF']
    mock_find_component_in_facility.return_value = None
    
    response = client.request("GET", "/ioc/info", json={"component_name": "non_existent_ioc"})
    
    assert response.status_code == 404
    assert "ERROR - ioc not found" in response.json()['payload']

# Tests for deploy_ioc
@pytest.mark.asyncio
async def test_deploy_ioc_success(mock_external_dependencies):
    print("Starting test_deploy_ioc_success")
    mock_get, mock_ansible, mock_find, mock_extract, mock_update, mock_log, mock_remove, mock_tarfile, mock_download, mock_write_file = mock_external_dependencies
    
    # Mock successful ansible playbook execution
    mock_ansible.return_value = ("Success output", "", 0)
    
    ioc_request = IocDict(
        facilities=["S3DF"],
        component_name="test_ioc",
        tag="v1.0.0",
        ioc_list=["ALL"],
        user="test_user",
        new=False
    )
    
    print("Sending request to /ioc/deployment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
    print(f"Received response with status code: {response.status_code}")
    
    assert response.status_code == 200
    assert "Deployment report" in response.text
    assert "Success" in response.text
    
    # Verify that necessary functions were called
    print("Verifying function calls")
    mock_get.assert_called()
    mock_ansible.assert_called()
    mock_find.assert_called()
    mock_extract.assert_called()
    mock_update.assert_called()
    mock_log.assert_called()
    mock_write_file.assert_called()
    mock_remove.assert_called()
    mock_tarfile.assert_called()
    print("Test completed successfully")

@pytest.mark.asyncio
async def test_deploy_ioc_failure(mock_external_dependencies):
    print("Starting test_deploy_ioc_failure")
    mock_get, mock_ansible, mock_find, mock_extract, mock_update, mock_log, mock_remove, mock_tarfile, mock_download, mock_write_file = mock_external_dependencies
    
    # Mock failed ansible playbook execution
    mock_ansible.return_value = ("", "Error output", 1)
    
    ioc_request = IocDict(
        facilities=["S3DF"],
        component_name="test_ioc",
        tag="v1.0.0",
        ioc_list=["ALL"],
        user="test_user",
        new=False
    )
    
    print("Sending request to /ioc/deployment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/ioc/deployment", json=ioc_request.model_dump())
    
    print(f"Received response with status code: {response.status_code}")
    
    assert response.status_code == 400
    assert "Deployment report" in response.text
    assert "Failure" in response.text
    
    # Verify that necessary functions were called
    print("Verifying function calls")
    mock_get.assert_called()
    mock_ansible.assert_called()
    mock_find.assert_called()
    mock_extract.assert_called()
    mock_write_file.assert_called()
    mock_remove.assert_called()
    mock_tarfile.assert_called()
    # Note: update and log might not be called in case of failure, depending on your implementation
    print("Test completed successfully")