from adbs_cli.cli_configuration import cli_configuration, Api
from adbs_cli.component import Component
import logging
import requests


class Request(object):
    def __init__(self, component: Component=None, api: str=Api.BACKEND):
        if (api == Api.BACKEND):
            self.url = cli_configuration["server_url"]
        elif (api == Api.DEPLOYMENT):
            self.url = cli_configuration["deployment_controller_url"]
        self.linux_uname = cli_configuration["linux_uname"]
        self.github_uname = cli_configuration["github_uname"]
        self.params = {}
        self.headers = {"linux_username": self.linux_uname,
                            "github_username": self.github_uname }
        self.payload = {}
        self.component = component

    def set_endpoint(self, endpoint: str):
        self.url += endpoint

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

    def log_api_response(self, response):
        logging.info(response.status_code)
        logging.info(response.json())
        logging.info(response.request.url)
        logging.info(response.request.body)
        logging.info(response.request.headers)

    def post_request(self, log: bool=False)-> requests.Response:
        response = requests.post(self.url, params=self.params, headers=self.headers, json=self.payload)
        if (log):
            self.log_api_response(response)
        return response
    
    def put_request(self, log: bool=False)-> requests.Response:
        response = requests.put(self.url, params=self.params, headers=self.headers, json=self.payload)
        if (log):
            self.log_api_response(response)
        return response

    def get_request(self, log: bool=False) -> requests.Response:
        response = requests.get(self.url, params=self.params, headers=self.headers, json=self.payload)
        if (log):
            self.log_api_response(response)
        return response
            
    # Return component payload
    def get_component_from_db(self) -> dict:
        component_list = requests.get(cli_configuration["server_url"] + 'component')
        component_dict = component_list.json()
        payload = component_dict['payload']
        for component in payload:
            if (component['name'] == self.component.name):
                response = requests.get(cli_configuration["server_url"] + 'component/' + component['id'])
                return response.json()['payload']

                

