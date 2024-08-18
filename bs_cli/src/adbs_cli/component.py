import os
from git import Repo, exc
from adbs_cli.auto_complete import AutoComplete

class Component(object):
    def __init__(self, name: str=None, branch_name: str=None):
        self.name = name
        self.branch_name = branch_name
        self.git_repo = self.git_get_root()

    def git_get_root(self):
        # Note - using git_repo.git.<action> allows usage of git like command line git
        try:
            git_repo = Repo(os.getcwd(), search_parent_directories=True)
            return git_repo
        except:
            return None
        
    def git_clone(self, url: str):
        # Clone repo from github url
        self.git_repo.git.clone(url)
        
    def git_create_branch(self, branch_point_type: str, branch_point_value: str, branch_name: str):
        # Create the branch
        # Tag is the only special case
        if (branch_point_type == 'tag'):
            branch_point_value = 'tags/' + branch_point_value
        self.git_repo.git.checkout('-b', branch_name, branch_point_value)

    def git_commit(self, branch_name: str):
        # Commit empty
        commit_msg = 'initial commit for ' + branch_name
        self.git_repo.git.commit("--allow-empty", '-m', commit_msg)

    def git_push(self, branch_name: str):
        # Commit and push to remote
        try:
            self.git_repo.git.push('-u', 'origin', branch_name)
            return True
        except exc.GitError as error:
            print(error)
            print("Deleting branch...")
            self.git_repo.git.branch('-D', branch_name)

    def git_get_branches(self):
        branches = self.git_repo.heads
        branch_names = [branch.name for branch in branches]
        return branch_names
        
    def git_get_tags(self):
        tags = self.git_repo.tags
        tag_names = [tag.name for tag in tags]
        return tag_names

    def git_get_commits(self):
        # TODO: we have to query the branch if we want to get the commits
        return None # TEMP
        commits = self.git_repo.commits
        commit_names = [commit.name for commit in commits]
        return commit_names

    def set_cur_dir_component(self):
        print("Checking current directory if a component...")
        # Safe to assume that if the current directory is a git repo 
        # then that repo is a component in the component db
        if (self.git_repo == None):
            return False
        git_root = self.git_repo.git.rev_parse("--show-toplevel")
        repo_name = os.path.splitext(os.path.basename(git_root))[0]
        branch_name = self.git_repo.active_branch.name
        self.name = repo_name
        self.branch_name = branch_name
        return True

    def prompt_name(self, prompt: str=None):
        AutoComplete.set_auto_complete_vals("component")
        if (not prompt):
            prompt = 'What is the component name? (<tab>-complete) '
        self.name = input(prompt)

    def prompt_branch_name(self, prompt: str=None):
        AutoComplete.set_auto_complete_vals("branch")
        if (not prompt):
            prompt = 'What is the branch name? (<tab>-complete) '
        self.branch_name = input(prompt)

    # logic does 3 seperate steps to set a field
    def set_component_field_logic(self, field: str):
        if (field == "name"):
            # 1) If component option passed in, then use that
            if (self.name):
                return
            # 2) Else set working directory as the component
            else:
                if (self.set_cur_dir_component() == False):
                    # 3) Else prompt user for component
                    self.prompt_name()
        elif (field == "branch"):
            # 1) If branch option passed in, then use thT
            if (self.branch_name):
                return
            # 2) Else set working directory as the branch
            else:
                if (self.set_cur_dir_component() == False):
                    # 3) Else prompt user for component
                    self.prompt_branch_name()
                    

                
