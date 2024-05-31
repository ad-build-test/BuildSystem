from cli_configuration import cli_configuration


class Payload(object):
    def __init__(self, component):
        self.url = cli_configuration["server_url"]
        self.send_payload = {"linux_username": cli_configuration["linux_uname"],
                            "github_username": cli_configuration["github_uname"] }
        self.component = component

    def add_to_payload(self, key, value):
        self.send_payload[key] = value

    def set_component_fields(self):
        self.component.set_component_fields()
        self.add_to_payload("component", self.component.name)
        self.add_to_payload("branch_name", self.component.branch_name)

