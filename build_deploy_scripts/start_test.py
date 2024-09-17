import os
import subprocess

# Scripts to run unit tests and integration tests
class Test(object):
    def __init__(self):
        self.registry_base_path = "/mnt/eed/ad-build/registry/"
        self.artifact_api_url = "http://artifact-api-service:8080/"

    def run_python_script(self, script: str):
        print("== ADBS == Running python script test " + script)
        try:
            output_bytes = subprocess.check_output(['python3', script], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output_bytes = e.output
        output = output_bytes.decode("utf-8")
        print(output)

    def run_bash_script(self, script: str):
        print("== ADBS == Running bash script test " + script)
        script = './' + script
        try:
            output_bytes = subprocess.check_output([script], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output_bytes = e.output
        output = output_bytes.decode("utf-8")
        print(output)

    def run_unit_tests(self, source_dir: str):
        """
        We can have a conventional folder like 'unit_tests' that the build_scripts/
          can just run bash/python scripts there. 
        Possible to add unit testing information to the test-ioc/configure/CONFIG.yaml at main
        · ad-build-test/test-ioc (github.com), with a field specifying which test files to run
        """
        print("== ADBS == Running unit tests")
        # 1) Enter build directory
        test_dir = source_dir + "/unit_tests"
        try:
            os.chdir(test_dir)
        except FileNotFoundError:
            print("== ADBS == Unit tests do not exist for this repo")
            return
            
        # 2) Run the bash/python scripts in the directory
        files = [f for f in os.listdir(".") if os.path.isfile(os.path.join(".", f))]
        for file in files:
            # Check if python
            if (file.endswith('.py')):
                self.run_python_script(file)
            # Otherwise run bash on it
            else:
                self.run_bash_script(file)


    def run_integration_tests(self):
        # TODO
        """
        We can have a conventional folder like 'integration_tests' that the build_scripts/ can 
        just run bash/python scripts there. Since this may involve external systems, 
        we may want user to specify it on the CONFIG.yaml. like external databases,
        apis, other IOCs, etc.
        """
        pass

