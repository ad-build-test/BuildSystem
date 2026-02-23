# Steps to build so far 

1. Go to ad-build-dev cluster 
2. Apply the testing_base_bookworm_deployment.yml (if deployment doesnt already exist)
3. kubectl exec --stdin --tty testing-base-bookworm-deployment-b79dccd4-b7s9q -- /bin/bash

### Automatic steps
3. as a user on dev-srv09 run ./clone_only.sh,
- so for made script for prc, will make seperate ones for others
4. in the container run ./llrf_prc_build.sh <target-archs>
5. done

### Manual steps (if didn't perform the automatic steps above)
4. export XILINXD_LICENSE_FILE=2100@tidlic01.slac.stanford.edu
5. export HOME=/mnt/eed/ad-build/llrf/.home
5. export LD_PRELOAD=/lib/x86_64-linux-gnu/libudev.so.1
(If repo already cloned and the submodules)
5. cd /mnt/eed/ad-build/llrf/

(If repo already cloned and the submodules, skip steps 5 -12)
5. git clone https://github.com/slaclab/lcls2_llrf.git
6. Change the .gitmodules files urls for the following
    - qf2_pre -> https://github.com/slaclab/qf2-pre-users.git
    - bedrock -> https://github.com/slaclab/bedrock.git
    - cavemu -> https://github.com/slaclab/cavemu.git
    - sa_rsa306b -> https://github.com/slaclab/sa_rsa306b.git
    - sa_ms2034a -> https://github.com/slaclab/sa_ms2034a.git

```
[submodule "software/submodules/qf2_pre"]
	path = software/submodules/qf2_pre
        url = https://github.com/slaclab/qf2-pre-users.git
[submodule "firmware/submodules/bedrock"]
	path = firmware/submodules/bedrock
        url = https://github.com/slaclab/bedrock.git
[submodule "firmware/submodules/surf"]
	path = firmware/submodules/surf
	url = https://github.com/slaclab/surf.git
[submodule "firmware/submodules/lcls2-llrf-bsa-mps-tx-core"]
	path = firmware/submodules/lcls2-llrf-bsa-mps-tx-core
	url = https://github.com/slaclab/lcls2-llrf-bsa-mps-tx-core.git
[submodule "firmware/submodules/lcls-timing-core"]
	path = firmware/submodules/lcls-timing-core
	url = https://github.com/slaclab/lcls-timing-core.git
[submodule "firmware/submodules/cavemu"]
	path = firmware/submodules/cavemu
	url = https://github.com/slaclab/cavemu.git
[submodule "software/submodules/sa_rsa306b"]
	path = software/submodules/sa_rsa306b
	url = https://github.com/slaclab/sa_rsa306b.git
[submodule "software/submodules/sa_ms2034a"]
	path = software/submodules/sa_ms2034a
	url = https://github.com/slaclab/sa_ms2034a.git

```


7. git submodule update --init --recursive
8. It may fail trying to clone the submodule bedrock within the submodule cavemu
so change the url of the .gitmodules in the firmware/submodules/cavemu/.gitmodules to https://github.com/slaclab/bedrock.git
9. git submodule sync --recursive
10. git submodule update --init --recursive
11. Make sure you can git status
12. if error then enter `git config --global --add safe.directory /mnt/eed/ad-build/llrf/lcls2_llrf`
13. time ./build_llrf.sh
14. done


Hit this error:
```
# add_files $flist_work
# set_property  top $app_name [current_fileset]
# set gitid_for_filename $git_status(short_id)$git_status(suffix)
# set gitid_v [get_git_id 8]
# set new_defs [list "GIT_32BIT_ID=32'h$gitid_v" "USE_FNAL_NCO=1" "REVC_1W"]
# set cur_list [get_property verilog_define [current_fileset]]
# set args [list {*}$new_defs {*}$cur_list]
# set_property verilog_define $args [current_fileset]
# puts "DEFINES:"
DEFINES:
# puts [get_property verilog_define [current_fileset]]
GIT_32BIT_ID=32'haaaaaaaa USE_FNAL_NCO=1 REVC_1W Q1_GT3_CPLL GT_TYPE__GTX Q1_GT3_8B10B_EN Q1_GT3_ENABLE Q1_GT2_CPLL Q1_GT2_ENABLE Q1_GT1_CPLL Q1_GT1_8B10B_EN Q1_GT1_ENABLE Q1_GT0_CPLL Q1_GT0_8B10B_EN Q1_GT0_ENABLE Q0_GT2_CPLL Q0_GT2_8B10B_EN Q0_GT2_ENABLE Q0_GT1_CPLL Q0_GT1_8B10B_EN Q0_GT1_ENABLE Q0_GT0_CPLL Q0_GT0_8B10B_EN Q0_GT0_ENABLE
# launch_runs synth_1 -verbose
realloc(): invalid old size
Abnormal program termination (6)
Please check '/mnt/eed/ad-build/llrf/lcls2_llrf/firmware/prc/hs_err_pid1490.log' for details
make: *** [Makefile:210: prc.bit] Error 134

real    1m42.300s
user    0m56.639s
sys     0m5.312s
I have no name!@testing-base-bookworm-deployment-b79dccd4-b7s9q:/mnt/eed/ad-build/llrf/lcls2_llrf$
```
