from cli_configuration import cli_configuration
from component import Component
import requests


class Request(object):
    def __init__(self, component: Component):
        self.url = cli_configuration["server_url"]
        self.headers = {"linux_username": cli_configuration["linux_uname"],
                            "github_username": cli_configuration["github_uname"] }
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
        self.component.set_component_field("name")
        self.add_to_payload("component", self.component.name)

    def set_component_branch_name(self):
        self.component.set_component_field("branch")
        self.add_to_payload("branch", self.component.branch_name)

    def post_request(self):
        return requests.post(self.url, self.headers, self.payload)


