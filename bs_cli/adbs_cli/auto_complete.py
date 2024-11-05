import requests
import readline
from adbs_cli.cli_configuration import cli_configuration

# Tab auto-complete
class AutoComplete(object):
    # https://pymotw.com/2/readline/
            
    def __init__(self, options):
        self.options = sorted(options)
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
    
    def set_auto_complete_vals(type: str, auto_complete_vals: list=None):
        if (type == 'branch'): # TODO: Determine how we get branches
            # right now we get the branches from the repo
            pass
        elif (type == "component"):
            # Send a GET request to component db to get list of components
            if (auto_complete_vals == None):
                component_list = requests.get(cli_configuration["server_url"] + 'component')
                component_dict = component_list.json()
                payload = component_dict['payload']
                auto_complete_vals = []
                for component in payload:
                    auto_complete_vals.append(component['name'])
        readline.set_completer(AutoComplete(auto_complete_vals).complete)
