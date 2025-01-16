"""
Desc: test Deployment controller, handles deployments

Usage: python3 test_deployment_controller_api.py
"""
import requests
import time
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Assuming the FastAPI app is defined in 'deployment_Controller.py'
# We need to run the FastAPI app first
from mock_deployment_controller import app

# Define the TestClient for FastAPI
client = TestClient(app)

# Define data models for requests
class BasicIoc(BaseModel):
    component_name: str

class IocDict(BaseModel):
    facilities: list = None  # Optional
    component_name: str
    tag: str
    ioc_list: list
    user: str

def run_fastapi_app():
    # Start the FastAPI app (this should ideally be done using Uvicorn)
    import subprocess
    # Assuming your FastAPI app is named "deployment_Controller.py" and you use Uvicorn to run it
    process = subprocess.Popen(["python3", "deployment_controller.py"])
    # process = subprocess.Popen(["uvicorn", "deployment_controller:app", "--reload", "--host", "127.0.0.1", "--port", "8000"])

    # Allow FastAPI app to start up
    time.sleep(5)  # Wait for the server to be ready
    return process


def send_get_root_request():
    response = client.get("/")
    if response.status_code == 200:
        print("GET / succeeded:", response.json())
    else:
        print("GET / failed:", response.status_code)


def send_get_ioc_info_request(component_name: str):
    ioc_request = BasicIoc(component_name=component_name)
    response = client.get("/ioc/info", params=ioc_request.dict())
    if response.status_code == 200:
        print(f"GET /ioc/info succeeded: {response.json()}")
    else:
        print(f"GET /ioc/info failed: {response.status_code}")


def send_put_deploy_ioc_request(ioc_dict: IocDict):
    response = client.put("/ioc/deployment", json=ioc_dict.dict())
    if response.status_code == 200:
        print("PUT /ioc/deployment succeeded:", response.json())
    else:
        print("PUT /ioc/deployment failed:", response.status_code)


def main():
    # Start the FastAPI app
    process = run_fastapi_app()

    try:
        # Sending GET request to "/"
        send_get_root_request()

        # Sending GET request to "/ioc/info"
        send_get_ioc_info_request(component_name="oscilloscope")

        # Sending PUT request to "/ioc/deployment"
        ioc_dict = IocDict(
            facilities=["S3DF"],
            component_name="oscilloscope",
            tag="oscilloscope-demo",
            ioc_list=["ALL"],
            user="admin"
        )
        send_put_deploy_ioc_request(ioc_dict)

    finally:
        # Terminate FastAPI server after requests
        process.terminate()


if __name__ == "__main__":
    main()
