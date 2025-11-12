#!/usr/bin/env bash
# ioc_build_test.sh - Static build checks (no runtime, no st.cmd)

set -e

ARCH="${EPICS_HOST_ARCH:-linux-x86_64}"
IOC_TOP="${1:-../}"

echo "=== IOC Build Test ==="
echo "Architecture: $ARCH"

# 1. Check build artifacts exist
echo -n "Build artifacts... "
for item in "bin/$ARCH" dbd db; do
  [ -e "$IOC_TOP/$item" ] || { echo "FAIL: Missing $item"; exit 1; }
done
echo "✓"

# 2. Check IOC binary exists
echo -n "IOC binary... "
IOC_BIN=$(find "$IOC_TOP/bin/$ARCH" -maxdepth 1 -type f -executable -print -quit 2>/dev/null)
[ -n "$IOC_BIN" ] || { echo "FAIL: No executable in bin/$ARCH/"; exit 1; }
echo "✓ $(basename "$IOC_BIN")"

# 3. Check shared library dependencies
echo -n "Shared libraries... "
if ldd "$IOC_BIN" 2>&1 | grep -q 'not found'; then
  echo "FAIL:"
  ldd "$IOC_BIN" | grep 'not found'
  exit 1
fi
echo "✓"

# 4. Check .dbd file exists
echo -n "DBD file... "
DBD=$(find "$IOC_TOP/dbd" -maxdepth 1 -name "*.dbd" -type f -print -quit 2>/dev/null)
[ -n "$DBD" ] || { echo "FAIL: No .dbd in dbd/"; exit 1; }
echo "✓ $(basename "$DBD")"

# 5. Check db files exist
echo -n "Database files... "
DB_COUNT=$(find "$IOC_TOP/db" -name "*.db" -o -name "*.template" 2>/dev/null | wc -l)
if [ "$DB_COUNT" -eq 0 ]; then
  echo "WARN: No .db or .template files (may be expected)"
else
  echo "✓ ($DB_COUNT files)"
fi

echo ""
echo "=== BUILD TEST PASSED ==="