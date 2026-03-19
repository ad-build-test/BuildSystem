#!/bin/bash
set -e  # Exit on error

##############################################################################
# llrf_firmware_build.sh - Build LLRF firmware with configurable firmware type and targets
# MUST RUN INSIDE BUILD POD WITH PROPER MOUNT
# OFFICIAL LATEST VERSION LIVES ON BuildSystem/llrf_temp/ for now.
# ** Please run clone_only.sh first to clone the repository and set up the submodules before running this build script.
#
# Usage: ./llrf_firmware_build.sh <FIRMWARE> <TARGET1> [TARGET2] ...
#
#   FIRMWARE: prc | resonance_control | injector
#
#   e.g., ./llrf_firmware_build.sh prc qf2_v07
#   e.g., ./llrf_firmware_build.sh prc qf2_v07 cmoc_qf2_v07 fiber_qf2_v07 marble fiber_marble
#   e.g., ./llrf_firmware_build.sh resonance_control qf2_v07 fiber_qf2_v07 marble fiber_marble marblepip
#   e.g., ./llrf_firmware_build.sh injector qf2_v07
#
# Note: injector uses Vivado 2018.3; prc and resonance_control use Vivado 2020.2
##############################################################################

##############################################################################
# Parse arguments
##############################################################################
# $1 = firmware type (e.g., prc, resonance_control, injector)
# $2+ = one or more build targets (e.g., qf2_v07, marble)
FIRMWARE="$1"
shift  # Remove first arg so "$@" now contains only the target list
TARGETS=("$@")

if [ -z "$FIRMWARE" ] || [ ${#TARGETS[@]} -eq 0 ]; then
    echo "Usage: $0 <FIRMWARE> <TARGET1> [TARGET2] ..."
    echo "  FIRMWARE: prc | resonance_control | injector"
    echo "  e.g., $0 prc qf2_v07 marble"
    echo "  e.g., $0 resonance_control qf2_v07 fiber_qf2_v07 marble fiber_marble marblepip"
    echo "  e.g., $0 injector qf2_v07"
    exit 1
fi

BIT_FILE="${FIRMWARE}.bit"
VIVADO_PROJECT_NAME="${FIRMWARE}"
echo "Firmware: ${FIRMWARE}"
echo "Targets: ${TARGETS[*]}"

##############################################################################
# Setup Vivado environment
##############################################################################
echo ""
echo "================================================"
echo "Setting up Vivado environment..."
echo "================================================"

REPO_DIR="lcls2_llrf"

# Injector uses Vivado 2018.3; everything else uses 2020.2
if [ "$FIRMWARE" = "injector" ]; then
    export XILINX_VIVADO=/mnt/eed/ad-build/llrf/vivado_2018_3_extracted
else
    export XILINX_VIVADO=/mnt/eed/ad-build/llrf/vivado_2020_2_extracted
fi
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

##############################################################################
# Setup git safe.directory (for containers with UID mismatch)
##############################################################################
cd "$REPO_DIR"

echo ""
echo "================================================"
echo "Configuring git safe.directory..."
echo "================================================"

git config --global --add safe.directory "$(pwd)"

echo "Git configuration complete."

##############################################################################
# Build firmware
##############################################################################
echo ""
echo "================================================"
echo "Building ${FIRMWARE} firmware..."
echo "================================================"

cd "firmware/${FIRMWARE}"

for target in "${TARGETS[@]}"; do
    echo ""
    echo "================================================"
    echo "Building ${FIRMWARE} for ${target}..."
    echo "================================================"
    time make CONFIG="${target}" "${BIT_FILE}" || {
        echo "ERROR: Build failed for target ${target}"
        exit 1
    }

    # Collect artifacts
    ARTIFACTS_DIR="build_artifacts_$(date +%Y_%m_%d_%H%M%S)/${target}"
    echo "Collecting ${FIRMWARE} artifacts..."
    mkdir -p "../../${ARTIFACTS_DIR}/${FIRMWARE}"
    mkdir -p "../../${ARTIFACTS_DIR}/${FIRMWARE}/impl_1"
    mkdir -p "../../${ARTIFACTS_DIR}/${FIRMWARE}/synth_1"
    cp -v *.bit "../../${ARTIFACTS_DIR}/${FIRMWARE}/" 2>/dev/null || true
    cp -v "vivado_project/${VIVADO_PROJECT_NAME}.runs/impl_1/*.rpt" "../../${ARTIFACTS_DIR}/${FIRMWARE}/impl_1/" 2>/dev/null || true
    cp -v "vivado_project/${VIVADO_PROJECT_NAME}.runs/impl_1/*.log" "../../${ARTIFACTS_DIR}/${FIRMWARE}/impl_1/" 2>/dev/null || true
    cp -v "vivado_project/${VIVADO_PROJECT_NAME}.runs/synth_1/*.rpt" "../../${ARTIFACTS_DIR}/${FIRMWARE}/synth_1/" 2>/dev/null || true
    cp -v "vivado_project/${VIVADO_PROJECT_NAME}.runs/synth_1/*.log" "../../${ARTIFACTS_DIR}/${FIRMWARE}/synth_1/" 2>/dev/null || true
done

cd ../..

##############################################################################
# Complete
##############################################################################
echo ""
echo "================================================"
echo "Build complete! Artifacts in: ${ARTIFACTS_DIR}"
echo "================================================"
ls -lh "${ARTIFACTS_DIR}/" || echo "No artifacts found"
