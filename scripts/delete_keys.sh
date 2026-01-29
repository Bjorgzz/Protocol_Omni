#!/bin/bash
set -e

# Configuration (Override via env vars)
BMC_IP=${BMC_IP:-"192.168.3.202"}
BMC_USER=${BMC_USER:-"admin"}
BMC_PASS=${BMC_PASS:-"Aa135610"}
ACTION_URI="https://${BMC_IP}/redfish/v1/Systems/Self/SecureBoot/Actions/SecureBoot.ResetKeys"

echo "=== Deleting Secure Boot Keys ==="

# Execute Action
curl -f -s -k -X POST -u "${BMC_USER}:${BMC_PASS}" \
    -H "Content-Type: application/json" \
    -d '{"ResetKeysType": "DeleteAllKeys"}' \
    "${ACTION_URI}"

echo ""
echo "=== Success: All Secure Boot Keys Deleted ==="
