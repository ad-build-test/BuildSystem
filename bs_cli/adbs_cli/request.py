from adbs_cli.cli_configuration import cli_configuration, Api, ApiEndpoints
from adbs_cli.component import Component
import logging
import requests
import sys

class Request(object):
    def __init__(self, component: Component=None, api: str=Api.BACKEND):
        if (api == Api.BACKEND):
            self.url = cli_configuration["server_url"]
        elif (api == Api.DEPLOYMENT):
            self.url = cli_configuration["deployment_controller_url"]
        self.linux_uname = cli_configuration["linux_uname"]
        self.github_uname = cli_configuration["github_uname"]
        self.params = {}
        # X - meaning non-standard headers
        self.headers = {"X-adbs-linux-user": self.linux_uname,
                        "X-adbs-github-user": self.github_uname }
        self.payload = {}
        self.component = component
        self.response = {}
        self.endpoint = ""

    def set_endpoint(self, endpoint: str):
        self.endpoint = endpoint

    def set_endpoint(self, endpoint, **kwargs):
        """ Set the endpoint for the request. """
        if isinstance(endpoint, ApiEndpoints) and kwargs:
            self.endpoint = endpoint.format(**kwargs)
        else:
            self.endpoint = endpoint
        
        return self

    def add_to_payload(self, key: str, value: str):
        self.payload[key] = value

    def add_dict_to_payload(self, values: dict):
        self.payload.update(values)

    def add_to_params(self, key: str, value: str):
        self.params[key] = value

    def set_component_fields(self):
        self.set_component_name()
        self.set_component_branch_name()
    
    def set_component_name(self):
        self.component.set_component_field_logic("name")

    def set_component_branch_name(self):
        self.component.set_component_field_logic("branch")

    def log_request_response(self):
        try:
            logging.info(self.response.status_code)
            logging.info(self.response.json())
            logging.info(self.response.request.url)
            logging.info(self.response.request.body)
            logging.info(self.response.request.headers)
        except Exception as e:
            logging.info(f"Error printing response: {e}")

    def post_request(self, log: bool, msg: str=None)-> requests.Response:
        return self.send_request("POST", log, msg)
    
    def put_request(self, log: bool, msg: str=None)-> requests.Response:
        return self.send_request("PUT", log, msg)

    def get_request(self, log: bool, msg: str=None) -> requests.Response:
        return self.send_request("GET", log, msg)
    
    def delete_request(self, log: bool, msg: str=None) -> requests.Response:
        return self.send_request("DELETE", log, msg)
    
    def get_streaming_request(self, log: bool, msg: str=None) -> requests.Response:
        """Make a GET request with streaming enabled."""
        self.headers['Accept'] = 'application/x-ndjson'
        self.headers['Connection'] = 'keep-alive'

        self.log_request(log, msg)

        return requests.get(self.url + self.endpoint, 
                        params=self.params, 
                        headers=self.headers, 
                        stream=True)
    
    def send_request(self, request_type: str, log: bool, msg) -> requests.Response:
        """Generalized function for GET, POST, and PUT requests."""
        self.test_server_connection()
        try:
            # Determine the request method and send the corresponding request
            if request_type == 'GET':
                self.response = requests.get(self.url + self.endpoint, params=self.params, headers=self.headers, json=self.payload)
            elif request_type == 'POST':
                self.response = requests.post(self.url + self.endpoint, params=self.params, headers=self.headers, json=self.payload)
            elif request_type == 'PUT':
                self.response = requests.put(self.url + self.endpoint, params=self.params, headers=self.headers, json=self.payload)
            elif request_type == 'DELETE':
                self.response = requests.delete(self.url + self.endpoint, params=self.params, headers=self.headers, json=self.payload)

            self.log_request(log, msg)
            return self.response

        except requests.exceptions.ConnectionError:
            print("== ADBS == FAIL: The backend server could not be reached.")
        if (msg): print(f"== ADBS == FAIL: {msg}")
        return None
    
    def log_request(self, log: bool, msg: str):
        if (log):
            self.log_request_response()
        if (msg):
            self.log_request_status(msg)
            
    # Return component payload
    def get_component_from_db(self) -> dict:
        component_list = requests.get(cli_configuration["server_url"] + 'component')
        component_dict = component_list.json()
        payload = component_dict['payload']
        for component in payload:
            if (component['name'] == self.component.name):
                response = requests.get(cli_configuration["server_url"] + 'component/' + component['id'])
                return response.json()['payload']
            
    def log_request_status(self, msg: str):
        if (self.response.ok):
            print(f"== ADBS == SUCCESS: {msg} - {self.response.json()['payload']}")
        else:
            try:
                print(f"== ADBS == FAIL: {msg} - {self.response.json()}")
            except:
                print(f"== ADBS == Request failed: {msg} - {self.response} ")

    def test_server_connection(self):
        # Test to see if the backend is alive and well
        test_endpoint = "echo/test/valid"
        try:
            response = requests.get(cli_configuration["server_url"] + test_endpoint)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)

        if (response.status_code == 503):
            print("== ADBS == Software Factory server is down! Sorry - please contact admins.")
            print(response.content)
            sys.exit(1)

                

