from cli_configuration import cli_configuration
from component import Component
import requests


class Request(object):
    def __init__(self, component: Component):
        self.url = cli_configuration["server_url"]
        self.linux_uname = cli_configuration["linux_uname"]
        self.github_uname = cli_configuration["github_uname"]
        self.headers = {"linux_username": self.linux_uname,
                            "github_username": self.github_uname }
        self.payload = {}
        self.component = component

    def set_endpoint(self, endpoint: str):
        self.url += endpoint

    def add_to_payload(self, key: str, value: str):
        self.payload[key] = value

    def set_component_fields(self):
        self.set_component_name()
        self.set_component_branch_name()
    
    def set_component_name(self):
        self.component.set_component_field_logic("name")

    def set_component_branch_name(self):
        self.component.set_component_field_logic("branch")

    def post_request(self):
        return requests.post(self.url, headers=self.headers, json=self.payload)
    
    def put_request(self):
        return requests.put(self.url, headers=self.headers, json=self.payload)


