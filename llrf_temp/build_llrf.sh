#!/bin/bash
set -e

###
**********************
Do not run this, please refer to llrf_prc_build.sh and the other build scripts (in development)
##

#####

# DEVELOPER NOTES 
# - Must run this inside /sdf/group/ad/eed/ad-build/llrf/lcls2_llrf
# - there is a temporary relative path that points to the vivado installation
# - IF YOU MAKE CHANGES - copy them to /sdf/group/ad/eed/ad-build/llrf/lcls2_llrf/build_llrf.sh

####

# Set Vivado path (adjust to your installation)
# export XILINX_VIVADO=/non-free/Xilinx/Vivado/2018.3
export XILINX_VIVADO=/mnt/eed/ad-build/llrf/vivado_2020_2_extracted # must use absolute path
export PATH=$XILINX_VIVADO/bin:$PATH
echo $PATH

# Set home directory (scratch space) where vivado will write to
export HOME=/mnt/eed/ad-build/llrf/.home
mkdir -p "$HOME"
mkdir -p "$HOME/.Xilinx"

# Verify vivado is found
which vivado || { echo "ERROR: vivado not found in PATH"; exit 1; }

# Create artifacts directory (mimics GitLab CI artifact collection)
ARTIFACTS_DIR="build_artifacts_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARTIFACTS_DIR"

##############################################################################
# PRC builds
# From GitLab CI job: prc (extends .bitgen_prc)
#   before_script: ls /non-free && cd firmware/prc
#   script: PATH=$XILINX_VIVADO/bin:$PATH make CONFIG=${TARGET} prc.bit
#   parallel matrix TARGET: [qf2_v07, cmoc_qf2_v07, fiber_qf2_v07, marble, fiber_marble]
#
# Artifacts collected (.bitgen_prc):
#   - firmware/prc/*.bit
#   - firmware/prc/vivado_project/prc.runs/impl_1/*.rpt
#   - firmware/prc/vivado_project/prc.runs/impl_1/*.log
#   - firmware/prc/vivado_project/prc.runs/synth_1/*.rpt
#   - firmware/prc/vivado_project/prc.runs/synth_1/*.log
##############################################################################
echo "Building PRC..."
cd firmware/prc
for target in qf2_v07 cmoc_qf2_v07 fiber_qf2_v07 marble fiber_marble; do
  echo "Building PRC for ${target}..."
  make CONFIG=${target} prc.bit
done

# Collect artifacts (mimics GitLab CI artifact paths)
echo "Collecting PRC artifacts..."
mkdir -p "../../$ARTIFACTS_DIR/prc"
cp -v *.bit "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true
cp -v vivado_project/prc.runs/impl_1/*.rpt "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true
cp -v vivado_project/prc.runs/impl_1/*.log "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true
cp -v vivado_project/prc.runs/synth_1/*.rpt "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true
cp -v vivado_project/prc.runs/synth_1/*.log "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true

cd ../..

##############################################################################
# Resonance Control builds
# From GitLab CI job: resonance_control (extends .bitgen_resonance_control)
#   before_script: ls /non-free && cd firmware/resonance_control
#   script: PATH=$XILINX_VIVADO/bin:$PATH make CONFIG=${TARGET} resonance_control.bit
#   parallel matrix TARGET: [qf2_v07, fiber_qf2_v07, marble, fiber_marble, marblepip]
#
# Artifacts collected (.bitgen_resonance_control):
#   - firmware/resonance_control/*.bit
#   - firmware/resonance_control/vivado_project/resonance_control.runs/impl_1/*.rpt
#   - firmware/resonance_control/vivado_project/resonance_control.runs/impl_1/*.log
#   - firmware/resonance_control/vivado_project/resonance_control.runs/synth_1/*.rpt
#   - firmware/resonance_control/vivado_project/resonance_control.runs/synth_1/*.log
##############################################################################
echo "Building Resonance Control..."
cd firmware/resonance_control
for target in qf2_v07 fiber_qf2_v07 marble fiber_marble marblepip; do
  echo "Building Resonance Control for ${target}..."
  make CONFIG=${target} resonance_control.bit
done

# Collect artifacts
echo "Collecting Resonance Control artifacts..."
mkdir -p "../../$ARTIFACTS_DIR/resonance_control"
cp -v *.bit "../../$ARTIFACTS_DIR/resonance_control/" 2>/dev/null || true
cp -v vivado_project/resonance_control.runs/impl_1/*.rpt "../../$ARTIFACTS_DIR/resonance_control/" 2>/dev/null || true
cp -v vivado_project/resonance_control.runs/impl_1/*.log "../../$ARTIFACTS_DIR/resonance_control/" 2>/dev/null || true
cp -v vivado_project/resonance_control.runs/synth_1/*.rpt "../../$ARTIFACTS_DIR/resonance_control/" 2>/dev/null || true
cp -v vivado_project/resonance_control.runs/synth_1/*.log "../../$ARTIFACTS_DIR/resonance_control/" 2>/dev/null || true

cd ../..

##############################################################################
# Injector builds
# From GitLab CI job: injector (extends .bitgen_injector)
#   before_script: ls /non-free && cd firmware/injector
#   script: XILINX_VIVADO=/non-free/Xilinx/Vivado/2018.3 PATH=$XILINX_VIVADO/bin:$PATH make CONFIG=${TARGET} injector.bit
#   parallel matrix TARGET: [qf2_v07]
#   NOTE: Injector specifically uses Vivado 2018.3
#
# Artifacts collected (.bitgen_injector):
#   - firmware/injector/*.bit
#   - firmware/injector/vivado_project/injector.runs/impl_1/*.rpt
#   - firmware/injector/vivado_project/injector.runs/impl_1/*.log
#   - firmware/injector/vivado_project/injector.runs/synth_1/*.rpt
#   - firmware/injector/vivado_project/injector.runs/synth_1/*.log
##############################################################################
echo "Building Injector..."
cd firmware/injector
export XILINX_VIVADO=/non-free/Xilinx/Vivado/2018.3  # Injector uses 2018.3 specifically
export PATH=$XILINX_VIVADO/bin:$PATH
for target in qf2_v07; do
  echo "Building Injector for ${target}..."
  make CONFIG=${target} injector.bit
done

# Collect artifacts
echo "Collecting Injector artifacts..."
mkdir -p "../../$ARTIFACTS_DIR/injector"
cp -v *.bit "../../$ARTIFACTS_DIR/injector/" 2>/dev/null || true
cp -v vivado_project/injector.runs/impl_1/*.rpt "../../$ARTIFACTS_DIR/injector/" 2>/dev/null || true
cp -v vivado_project/injector.runs/impl_1/*.log "../../$ARTIFACTS_DIR/injector/" 2>/dev/null || true
cp -v vivado_project/injector.runs/synth_1/*.rpt "../../$ARTIFACTS_DIR/injector/" 2>/dev/null || true
cp -v vivado_project/injector.runs/synth_1/*.log "../../$ARTIFACTS_DIR/injector/" 2>/dev/null || true

cd ../..

echo "All builds complete!"
echo "Artifacts collected in: $ARTIFACTS_DIR"