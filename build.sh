#!/bin/bash
set -e  # Exit on error

# Define paths
ROOT_DIR="$(pwd)"
CLI_DIR="${ROOT_DIR}/bs_cli"
DIST_DIR="${CLI_DIR}/dist"
RESULTS_DIR="${ROOT_DIR}/build_results"

echo "Starting build process..."

# Check if build module is available, install dependencies only if needed
if ! python3 -c "import build" &>/dev/null; then
    echo "Installing build dependencies... (python3 -m pip install --upgrade pip setuptools wheel build)"
    python3 -m pip install --upgrade pip setuptools wheel build
else
    echo "Build dependencies already installed."
fi

# Navigate to CLI directory
cd "${CLI_DIR}"
echo "Changed to directory: $(pwd)"

# Clean up existing dist directory
if [ -d "${DIST_DIR}" ]; then
    echo "Cleaning up existing dist directory..."
    rm -rf "${DIST_DIR}"/*
else
    echo "Creating dist directory..."
    mkdir -p "${DIST_DIR}"
fi

# Build the package
echo "Building package..."
python3 -m build

# Create build_results directory if it doesn't exist
echo "Setting up build results directory..."
mkdir -p "${RESULTS_DIR}"

# Move built files to results directory
echo "Moving build artifacts to results directory..."
cp "${DIST_DIR}"/* "${RESULTS_DIR}/" || echo "No artifacts found to move."

echo "Build complete! Results are in: ${RESULTS_DIR}"