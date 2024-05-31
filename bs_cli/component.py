import os
import git
from auto_complete import AutoComplete


class Component(object):
    def __init__(self, name=None, branch_name=None):
        self.name = name
        self.branch_name = branch_name

    def get_git_root(self, path):
        try:
            git_repo = git.Repo(path, search_parent_directories=True)
            return git_repo
        except:
            return None

    def set_cur_dir_component(self):
        print("Checking current directory if a component...")
        # Safe to assume that if the current directory is a git repo 
        # then that repo is a component in the component db
        git_repo = self.get_git_root(os.getcwd())
        if (git_repo == None):
            return False
        git_root = git_repo.git.rev_parse("--show-toplevel")
        repo_name = os.path.splitext(os.path.basename(git_root))[0]
        branch_name = git_repo.active_branch.name
        self.name = repo_name
        self.branch_name = branch_name
        return True

    def prompt_name(self):
        AutoComplete.set_auto_complete_vals("component")
        self.name = input('What is the component name? (<tab>-complete) ')

    def prompt_branch_name(self):
        AutoComplete.set_auto_complete_vals("branch")
        self.branch_name = input('What is the branch name? (<tab>-complete) ')

    def set_component_fields(self):
        # 1) If component options passed in, then use those
        if (self.name):
            if (self.branch_name == None):
                self.prompt_branch_name() 
        # 2) Else set working directory as the component
        else:
            if (self.set_cur_dir_component() == False):
                # 3) Else prompt user for component/branch
                self.prompt_name()
                self.prompt_branch_name()
