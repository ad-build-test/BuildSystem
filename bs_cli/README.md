# BuildSystem Command Line Interface
## Desc
0. Assuming you have the /dist, install package with ```pip install dist/adbs_cli-1.0.0-py3-none-any.whl```
1. Run with ```bs```
2. ex: ```bs run build```

## Dev
1. To install package in 'editable mode', just do a ```pip install -e .``` assuming you are the bs_cli/ directory (top of the source code dir)
2. To rebuild the package distribution, please update the `version` in setup.py
3. Please note - the build.sh will automatically build the cli and send to `build_results/`
4. Then you can do ```python3 -m build``` assuming you are at the bs_cli/ directory (top of the source code dir)

## Testing
1. Currently there is one testing module for the cli, which is for deployment commands
2. Please look at adbs_cli/test/test_entry_point_commands.py for more details on how to test

Sample test run output:
```
$ pytest -v -s test_entry_point_commands.py

===================================== test session starts ======================================
platform linux -- Python 3.10.12, pytest-8.3.4, pluggy-1.5.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/pnispero/BuildSystem/bs_cli
plugins: anyio-4.4.0, asyncio-0.25.3
asyncio: mode=strict, asyncio_default_fixture_loop_scope=None
collecting ... == ADBS == Warning: CLI pointed to dev cluster
collected 5 items

test_entry_point_commands.py::TestDeployCommand::test_deploy_new_tag_to_component_no_iocs Cloning into '/tmp/tmpw_e7xo52/oscilloscope'...
remote: Enumerating objects: 832, done.
remote: Counting objects: 100% (53/53), done.
remote: Compressing objects: 100% (36/36), done.
remote: Total 832 (delta 30), reused 29 (delta 17), pack-reused 779 (from 2)
Receiving objects: 100% (832/832), 112.50 KiB | 2.45 MiB/s, done.
Resolving deltas: 100% (432/432), done.
Command to invoke: bs deploy ['-f', 'S3DF', 'R1.3.0']
Command output:
== ADBS == Deploying to ['S3DF']... (This may take a minute)
== ADBS == Deployment finished, report will be downloaded at /home/pnispero/deployment-report-oscilloscope-R1.3.0-2025-05-20T17-04-08.log
[?] Confirm by 'enter', or specify alternate path:Report head:
#### Deployment report for oscilloscope - R1.3.0 ####
#### User: pnispero
#### IOCs deployed: {'S3DF': []}
#### Overall status: Success

== Deployment output for S3DF ==


Report downloaded successfully to /home/pnispero/deployment-report-oscilloscope-R1.3.0-2025-05-20T17-04-08.log

PASSED
test_entry_point_commands.py::TestDeployCommand::test_deploy_new_tag_to_new_iocs Command to invoke: bs deploy ['-i', 'sioc-b34-sc01,sioc-b34-sc02', '-f', 'S3DF', 'R1.3.0']
Command output:
== ADBS == Deploying to ['S3DF']... (This may take a minute)
== ADBS == Deployment finished, report will be downloaded at /home/pnispero/deployment-report-oscilloscope-R1.3.0-2025-05-20T17-04-30.log
[?] Confirm by 'enter', or specify alternate path:Report head:
#### Deployment report for oscilloscope - R1.3.0 ####
#### User: pnispero
#### IOCs deployed: {'S3DF': ['sioc-b34-sc01', 'sioc-b34-sc02']}
#### Overall status: Success

== Deployment output for S3DF ==


Report downloaded successfully to /home/pnispero/deployment-report-oscilloscope-R1.3.0-2025-05-20T17-04-30.log

PASSED
test_entry_point_commands.py::TestDeployCommand::test_deploy_new_tag_to_select_existing_iocs Command to invoke: bs deploy ['-i', 'sioc-b34-sc01,sioc-b34-sc02', 'R1.3.1']
Command output:
== ADBS == Deploying... (This may take a minute)
== ADBS == Deployment finished, report will be downloaded at /home/pnispero/deployment-report-oscilloscope-R1.3.1-2025-05-20T17-04-55.log
[?] Confirm by 'enter', or specify alternate path:Report head:
#### Deployment report for oscilloscope - R1.3.1 ####
#### User: pnispero
#### IOCs deployed: {'S3DF': ['sioc-b34-sc01', 'sioc-b34-sc02']}
#### Overall status: Success

== Deployment output for S3DF ==


Report downloaded successfully to /home/pnispero/deployment-report-oscilloscope-R1.3.1-2025-05-20T17-04-55.log

PASSED
test_entry_point_commands.py::TestDeployCommand::test_deploy_new_tag_to_all_existing_iocs Command to invoke: bs deploy ['-i', 'ALL', '-f', 'S3DF', 'R1.3.2']
Command output:
== ADBS == The following IOCs are not in the deployment database:
  - sioc-b34-sc03
  - sioc-b34-sc04
  - sioc-b15-sc01
Do you want to deploy ALL iocs *including* the new ones listed above? [y/N]: n
Do you want to deploy ALL iocs *excluding* the new ones listed above? [y/N]: y
== ADBS == Deploying to ['S3DF']... (This may take a minute)
== ADBS == Deployment finished, report will be downloaded at /home/pnispero/deployment-report-oscilloscope-R1.3.2-2025-05-20T17-05-13.log
[?] Confirm by 'enter', or specify alternate path:Report head:
#### Deployment report for oscilloscope - R1.3.2 ####
#### User: pnispero
#### IOCs deployed: {'S3DF': ['sioc-b34-sc02', 'sioc-b34-sc01']}
#### Overall status: Success

== Deployment output for S3DF ==


Report downloaded successfully to /home/pnispero/deployment-report-oscilloscope-R1.3.2-2025-05-20T17-05-13.log

PASSED
test_entry_point_commands.py::TestDeployCommand::test_deploy_new_tag_to_new_iocs_that_already_exist Command to invoke: bs deploy ['-i', 'sioc-as01-sc01,sioc-sys1-sc01', '-f', 'S3DF', 'R1.3.2']
Command output:
== ADBS == ERROR: IOCs you want to deploy already exist in another facility:
Facility: TESTFAC
- IOCs: ['sioc-as01-sc01']
Facility: FACET
- IOCs: ['sioc-sys1-sc01']
== ADBS == If you would like to delete/move IOCs from a facility, please contact software factory admins.

PASSED

**Tests finished** - PLEASE remove the following contents from mock dev on S3DF to test again:
        - iocTop/oscilloscope
        rm -rf /sdf/group/ad/eed/unofficial/lcls/epics/iocTop/oscilloscope
        - iocCommon/sioc-b34-sc01,sioc-b34-sc02
        rm -rf /sdf/group/ad/eed/unofficial/lcls/epics/iocCommon/sioc-b34-sc0*
        - iocData/sioc-b34-sc01,sioc-b34-sc02
        rm -rf iocCommon/sioc-b34-sc0* iocData/sioc-b34-sc0*

        And delete the oscilloscope entry for S3DF in the deployment database
        Now should be good to run test again. (May fully automate this sometime in future)



================================= 5 passed in 83.50s (0:01:23) =================================
```