#!/bin/bash
# This is a temporary script for cloning the lcls2_llrf repository and fixing submodule URLs, especially the cavemu nested bedrock issue.
# TODO: Will eventually make the adbuild user be able to clone, or just the backend clone and the submodules

set -e  # Exit on error

REPO_URL="https://github.com/slaclab/lcls2_llrf.git"
REPO_DIR="lcls2_llrf"
##############################################################################
# Clone the repository
##############################################################################
echo "================================================"
echo "Cloning repository..."
echo "================================================"

if [ -d "$REPO_DIR" ]; then
    echo "Directory $REPO_DIR already exists. Skipping clone."
    echo "To start fresh, remove it first: rm -rf $REPO_DIR"
    return
else
    git clone "$REPO_URL"
fi

cd "$REPO_DIR"

##############################################################################
# Update .gitmodules with corrected URLs
##############################################################################
echo ""
echo "================================================"
echo "Updating .gitmodules..."
echo "================================================"

cat > .gitmodules <<'EOF'
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
EOF

echo ".gitmodules updated."

##############################################################################
# Fix cavemu nested submodule URL and initialize all submodules
##############################################################################
echo ""
echo "================================================"
echo "Initializing submodules..."
echo "================================================"

# Sync the new URLs from .gitmodules
git submodule sync --recursive

# Initialize and update all submodules
git submodule update --init --recursive || {
    echo ""
    echo "WARNING: Submodule update failed (likely cavemu nested bedrock issue)."
    echo "Attempting to fix cavemu/bedrock URL..."
    
    # Fix the nested bedrock URL in cavemu
    if [ -f "firmware/submodules/cavemu/.gitmodules" ]; then
        sed -i 's|../../hdl-libraries/bedrock.git|https://github.com/slaclab/bedrock.git|g' \
            firmware/submodules/cavemu/.gitmodules
        
        git submodule sync --recursive
        git submodule update --init --recursive
    else
        echo "ERROR: Could not fix cavemu submodule."
        exit 1
    fi
}

echo "All submodules initialized successfully."

##############################################################################
# Setup git safe.directory (for containers with UID mismatch)
##############################################################################
echo ""
echo "================================================"
echo "Configuring git safe.directory..."
echo "================================================"

# Add this repo to safe.directory
git config --global --add safe.directory "$(pwd)"

echo "Git configuration complete."