#!/bin/bash
set -e

# Configuration (Override via env vars)
BMC_IP=${BMC_IP:-"192.168.3.202"}
BMC_USER=${BMC_USER:-"admin"}
BMC_PASS=${BMC_PASS:-"Aa135610"}
TARGET_URI="https://${BMC_IP}/redfish/v1/Systems/Self/SecureBoot"

echo "=== Disabling Secure Boot via Redfish ==="

# 1. Fetch ETag
echo "-> Fetching ETag..."
ETAG=$(curl -f -s -k -I -u "${BMC_USER}:${BMC_PASS}" "${TARGET_URI}" | grep -i ETag | tr -d '\r' | awk '{print $2}')

if [ -z "$ETAG" ]; then
    echo "Error: Failed to retrieve ETag."
    exit 1
fi
echo "-> Got ETag: $ETAG"

# 2. Patch SecureBootEnable
echo "-> Patching SecureBootEnable=false..."
curl -f -s -k -X PATCH -u "${BMC_USER}:${BMC_PASS}" \
    -H "Content-Type: application/json" \
    -H "If-Match: $ETAG" \
    -d '{"SecureBootEnable": false}' \
    "${TARGET_URI}"

echo ""
echo "=== Success: Secure Boot Disabled (Pending Reboot) ==="
