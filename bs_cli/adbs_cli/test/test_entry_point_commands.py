import os
import tempfile
import shutil
import pytest
from click.testing import CliRunner

# Import your module that contains the deploy command
# Adjust the import path based on your actual project structure
from adbs_cli.entry_point_commands import deploy

"""
Test module for deployment command using click.testing
Tests against real repositories and services on development server
This tests end-to-end

Pre-reqs:
1. be on development server and point your cli to dev cluster.
2. make sure build system backend is running
3. ensure oscilloscope deployment entry does not exist

How to run:
pytest -v -s test_entry_point_commands.py
-v : verbose
-s : Disable output capturing
"""

class TestDeployCommand:
    @pytest.fixture(scope="class")
    def runner(self):
        """Create a Click CLI runner for testing commands"""
        return CliRunner()
    
    @pytest.fixture(scope="class")  # Change from "function" to "module"
    def setup_test_repo(self):  # Remove 'self' parameter since it's a module fixture, not a class fixture
        """Set up a test repository environment once for all tests in this module"""
        # Save current directory
        original_dir = os.getcwd()
        
        # Create a temporary working directory
        temp_dir = tempfile.mkdtemp()
        
        # Clone a real test repository - oscilloscope
        repo_url = "https://github.com/ad-build-test/oscilloscope.git"
        repo_dir = os.path.join(temp_dir, "oscilloscope")
        
        try:
            # Clone the repo
            os.system(f"git clone {repo_url} {repo_dir}")
            
            # Change to the repo directory
            os.chdir(repo_dir)
            
            yield repo_dir
            
        finally:
            # Clean up - return to original directory and remove temp dir
            os.chdir(original_dir)
            shutil.rmtree(temp_dir)
            test_finished_cleanup_task = """
    \n**Tests finished** - PLEASE remove the following contents from mock dev on S3DF to test again: 
        - iocTop/oscilloscope 
        rm -rf /sdf/group/ad/eed/unofficial/lcls/epics/iocTop/oscilloscope
        - iocCommon/sioc-b34-sc01,sioc-b34-sc02
        rm -rf /sdf/group/ad/eed/unofficial/lcls/epics/iocCommon/sioc-b34-sc0*
        - iocData/sioc-b34-sc01,sioc-b34-sc02
        rm -rf iocCommon/sioc-b34-sc0* iocData/sioc-b34-sc0*

        And delete the oscilloscope entry for S3DF in the deployment database 
        Now should be good to run test again. (May fully automate this sometime in future)
    """
            print(test_finished_cleanup_task)
    
    def test_deploy_new_tag_to_component_no_iocs(self, runner: CliRunner, setup_test_repo):
        """
        Test Case 1: Deploy a new tag to component (No IOCs specified)
        $ bs deploy -f S3DF R1.3.0
        """
        # Execute the command
        result = runner.invoke(deploy, ["-f", "S3DF", "R1.3.0"], input='\n')
        
        # Print output for debugging
        print(f"Command output:\n{result.output}")
        
        # Assertions
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Deploying to ['S3DF']" in result.output
        assert "Deployment finished" in result.output
        assert "Overall status: Success" in result.output
    
    def test_deploy_new_tag_to_new_iocs(self, runner: CliRunner, setup_test_repo):
        """
        Test Case 2: Deploy a new tag to new IOCs
        $ bs deploy -i sioc-b34-sc01,sioc-b34-sc02 -f S3DF R1.3.0
        """
        # Execute the command
        result = runner.invoke(deploy, ["-i", "sioc-b34-sc01,sioc-b34-sc02", "-f", "S3DF", "R1.3.0"], input='\n')
        
        # Print output for debugging
        print(f"Command output:\n{result.output}")

        # Assertions
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Deploying to ['S3DF']" in result.output
        assert "Deployment finished" in result.output
        assert "Overall status: Success" in result.output
    
    def test_deploy_new_tag_to_select_existing_iocs(self, runner: CliRunner, setup_test_repo):
        """
        Test Case 3: Deploy a new tag to select (existing) IOCs
        $ bs deploy -i sioc-b34-sc01,sioc-b34-sc02 R1.3.1
        """
        # Execute the command
        result = runner.invoke(deploy, ["-i", "sioc-b34-sc01,sioc-b34-sc02", "R1.3.1"], input='\n')
        
        # Print output for debugging
        print(f"Command output:\n{result.output}")

        # Assertions
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Deployment finished" in result.output
        assert "Overall status: Success" in result.output
    
    def test_deploy_new_tag_to_all_existing_iocs(self, runner: CliRunner, setup_test_repo):
        """
        Test Case 4: Deploy a new tag to ALL (existing) IOCs
        $ bs deploy -i ALL -f S3DF R1.3.2
        """
        # Execute the command
        result = runner.invoke(deploy, ["-i", "ALL", "-f", "S3DF", "R1.3.2"], input='n\ny\n\n')
        
        # Print output for debugging
        print(f"Command output:\n{result.output}")

        # Assertions
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Deploying to ['S3DF']" in result.output
        assert "Deployment finished" in result.output
        assert "Overall status: Success" in result.output