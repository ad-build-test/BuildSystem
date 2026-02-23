#!/bin/bash
set -e  # Exit on error

##############################################################################
# llrf_prc_build.sh - Build LLRF firmware with configurable targets
# MUST RUN INSIDE BUILD POD WITH PROPER MOUNT 
# OFFICIAL LATEST VERSION LIVES ON BuildSystem/llrf_temp/ for now.
# Usage: ./llrf_prc_build.sh [TARGET1] [TARGET2] ...
#   e.g., ./llrf_prc_build.sh qf2_v07
#   e.g., ./llrf_prc_build.sh qf2_v07 marble
#   If no targets specified, builds all known targets

# TODO: temporarily commented out the git cloning parts since it wont work for adbuild yet.
# And won't need to, since the cloning would be done from the github app backend.
##############################################################################

##############################################################################
# Setup Vivado environment
##############################################################################
echo ""
echo "================================================"
echo "Setting up Vivado environment..."
echo "================================================"

REPO_URL="https://github.com/slaclab/lcls2_llrf.git"
REPO_DIR="lcls2_llrf"
export XILINX_VIVADO=/mnt/eed/ad-build/llrf/vivado_2020_2_extracted
export PATH=$XILINX_VIVADO/bin:$PATH
# Set home directory (scratch space) where vivado will write to
export HOME="/mnt/eed/ad-build/llrf/.home"
mkdir -p "$HOME/.Xilinx"

# Set license for vivado
export XILINXD_LICENSE_FILE=2100@tidlic01.slac.stanford.edu
# Needed to fix vivado build bug
export LD_PRELOAD=/lib/x86_64-linux-gnu/libudev.so.1

echo "PATH: $PATH"
# Verify vivado is found
which vivado || { echo "ERROR: vivado not found in PATH"; exit 1; }
echo "Vivado found: $(which vivado)"

# ##############################################################################
# # Clone the repository
# ##############################################################################
# echo "================================================"
# echo "Cloning repository..."
# echo "================================================"

# if [ -d "$REPO_DIR" ]; then
#     echo "Directory $REPO_DIR already exists. Skipping clone."
#     echo "To start fresh, remove it first: rm -rf $REPO_DIR"
# else
#     git clone "$REPO_URL"
# fi

# cd "$REPO_DIR"

# ##############################################################################
# # Update .gitmodules with corrected URLs
# ##############################################################################
# echo ""
# echo "================================================"
# echo "Updating .gitmodules..."
# echo "================================================"

# cat > .gitmodules <<'EOF'
# [submodule "software/submodules/qf2_pre"]
# 	path = software/submodules/qf2_pre
# 	url = https://github.com/slaclab/qf2-pre-users.git
# [submodule "firmware/submodules/bedrock"]
# 	path = firmware/submodules/bedrock
# 	url = https://github.com/slaclab/bedrock.git
# [submodule "firmware/submodules/surf"]
# 	path = firmware/submodules/surf
# 	url = https://github.com/slaclab/surf.git
# [submodule "firmware/submodules/lcls2-llrf-bsa-mps-tx-core"]
# 	path = firmware/submodules/lcls2-llrf-bsa-mps-tx-core
# 	url = https://github.com/slaclab/lcls2-llrf-bsa-mps-tx-core.git
# [submodule "firmware/submodules/lcls-timing-core"]
# 	path = firmware/submodules/lcls-timing-core
# 	url = https://github.com/slaclab/lcls-timing-core.git
# [submodule "firmware/submodules/cavemu"]
# 	path = firmware/submodules/cavemu
# 	url = https://github.com/slaclab/cavemu.git
# [submodule "software/submodules/sa_rsa306b"]
# 	path = software/submodules/sa_rsa306b
# 	url = https://github.com/slaclab/sa_rsa306b.git
# [submodule "software/submodules/sa_ms2034a"]
# 	path = software/submodules/sa_ms2034a
# 	url = https://github.com/slaclab/sa_ms2034a.git
# EOF

# echo ".gitmodules updated."

# ##############################################################################
# # Fix cavemu nested submodule URL and initialize all submodules
# ##############################################################################
# echo ""
# echo "================================================"
# echo "Initializing submodules..."
# echo "================================================"

# # Sync the new URLs from .gitmodules
# git submodule sync --recursive

# # Initialize and update all submodules
# git submodule update --init --recursive || {
#     echo ""
#     echo "WARNING: Submodule update failed (likely cavemu nested bedrock issue)."
#     echo "Attempting to fix cavemu/bedrock URL..."
    
#     # Fix the nested bedrock URL in cavemu
#     if [ -f "firmware/submodules/cavemu/.gitmodules" ]; then
#         sed -i 's|../../hdl-libraries/bedrock.git|https://github.com/slaclab/bedrock.git|g' \
#             firmware/submodules/cavemu/.gitmodules
        
#         git submodule sync --recursive
#         git submodule update --init --recursive
#     else
#         echo "ERROR: Could not fix cavemu submodule."
#         exit 1
#     fi
# }

# echo "All submodules initialized successfully."

##############################################################################
# Setup git safe.directory (for containers with UID mismatch)
##############################################################################
cd "$REPO_DIR"

echo ""
echo "================================================"
echo "Configuring git safe.directory..."
echo "================================================"

# Add this repo to safe.directory
git config --global --add safe.directory "$(pwd)"

echo "Git configuration complete."

##############################################################################
# Build firmware
##############################################################################
echo ""
echo "================================================"
echo "Building firmware..."
echo "================================================"

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

# Default targets (all known configs)
ALL_TARGETS=(qf2_v07 cmoc_qf2_v07 fiber_qf2_v07 marble fiber_marble)

# Use command-line args if provided, otherwise use all targets
if [ $# -eq 0 ]; then
    TARGETS=("${ALL_TARGETS[@]}")
    echo "No targets specified; building all: ${TARGETS[*]}"
else
    TARGETS=("$@")
    echo "Building specified targets: ${TARGETS[*]}"
fi

echo "Building PRC..."
cd firmware/prc

for target in "${TARGETS[@]}"; do
    echo ""
    echo "================================================"
    echo "Building PRC for ${target}..."
    echo "================================================"
    time make CONFIG="${target}" prc.bit || {
        echo "ERROR: Build failed for target ${target}"
        exit 1
    }

    # Collect artifacts
    # Create artifacts directory
    ARTIFACTS_DIR="build_artifacts_$(date +%Y_%m_%d_%H%M%S)/${target}"
    echo "Collecting PRC artifacts..."
    mkdir -p "../../$ARTIFACTS_DIR/prc"
    cp -v *.bit "../../$ARTIFACTS_DIR/prc/" 2>/dev/null || true
    cp -v vivado_project/prc.runs/impl_1/*.rpt "../../$ARTIFACTS_DIR/prc/impl_1/" 2>/dev/null || true
    cp -v vivado_project/prc.runs/impl_1/*.log "../../$ARTIFACTS_DIR/prc/impl_1/" 2>/dev/null || true
    cp -v vivado_project/prc.runs/synth_1/*.rpt "../../$ARTIFACTS_DIR/prc/synth_1/" 2>/dev/null || true
    cp -v vivado_project/prc.runs/synth_1/*.log "../../$ARTIFACTS_DIR/prc/synth_1/" 2>/dev/null || true
done

cd ../..

##############################################################################
# Complete
##############################################################################
echo ""
echo "================================================"
echo "Build complete! Artifacts in: $ARTIFACTS_DIR"
echo "================================================"
ls -lh "$ARTIFACTS_DIR/" || echo "No artifacts found"