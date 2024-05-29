import requests
import readline
from cli_configuration import cli_configuration

# Tab auto-complete
class AutoComplete(object):
    # https://pymotw.com/2/readline/
            
    def __init__(self, options):
        self.options = sorted(options)
        # self.default_payload = { "linux_username": cli_configuration["linux_uname"],
        #                 "github_username": cli_configuration["github_uname"] }
        return

    def complete(self, text, state):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s 
                                for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        
        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response
    
    def set_auto_complete_vals(type: str):
        # Send a GET request to component db to get list of components
        component_list = requests.get(cli_configuration["server_url"] + 'component')
        component_dict = component_list.json()
        payload = component_dict['payload']
        component_list = []
        if (type == "component"):
            for component in payload:
                component_list.append(component['name'])
        elif (type == "branch"):
            # TODO: Need to see how we can get the branch names from db
            for component in payload:
                component_list.append(component['name'])
        readline.set_completer(AutoComplete(component_list).complete)
