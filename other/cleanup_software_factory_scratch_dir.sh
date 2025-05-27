#!/bin/bash

# Simple script to remove old builds from the filesystem.
# This is ran as a cron job by "adbuild" every 7 days.

# Configure base directories
BASE_DIR="/sdf/group/ad/eed/ad-build/scratch"
LOG_FILE="${BASE_DIR}/cleanup.log"
NUM_DAYS_ALLOWED="+7"

# Log the start of the cleanup
echo "--------------------------------------------------------------" >> "$LOG_FILE"
echo "=== Build Cleanup Started: $(date) ===" >> "$LOG_FILE"

# Find build directories older than 7 days (at the 5th level) and move them to backup
echo "Removing build directories older than 7 days:" >> "$LOG_FILE"

find "$BASE_DIR" -mindepth 5 -maxdepth 5 -type d -mtime "$NUM_DAYS_ALLOWED" | while read dir_path; do
    relative_path="${dir_path#${BASE_DIR}/}"
    echo "Removing: $relative_path" >> "$LOG_FILE"
    rm -rf "$dir_path"

done

# Clean up empty directories in source location
# mindepth=2 because that is the /scratch/user. Don't want to delete the user dir even if its empty.
# But need to delete the actual repo dirs if they are empty
find "$BASE_DIR" -mindepth 2 -type d -empty -delete

# Log completion
echo "=== Build Cleanup Completed: $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"