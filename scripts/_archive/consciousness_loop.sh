#!/bin/bash
# =============================================================================
# Operation Consciousness Loop - Automated Introspection
# Protocol OMNI v16.2.5
#
# Runs hourly (async) to:
# 1. Generate sovereign status report
# 2. Inject status into Mem0 persistent memory (background, 10min timeout)
# =============================================================================

SCRIPT_DIR="$HOME/Protocol_Omni/scripts"
WORK_DIR="$HOME/Protocol_Omni"
MEM0_URL="http://localhost:8050/v1/memories/"
USER_ID="sovereign"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Consciousness Loop: Starting pulse..."

# Step 1: Generate status report
cd "$WORK_DIR"
python3 "$SCRIPT_DIR/generate_status.py" || {
    echo "[$TIMESTAMP] ERROR: Status generation failed"
    exit 1
}

# Step 2: Read the generated report
if [[ ! -f "$WORK_DIR/sovereign_status.md" ]]; then
    echo "[$TIMESTAMP] ERROR: sovereign_status.md not found"
    exit 1
fi

# Step 3: Use Python to construct and send the payload (async with timeout)
# Note: DeepSeek 671B fact extraction takes 5+ minutes
python3 << 'PYEOF'
import json
import urllib.request
import urllib.error
import sys
from datetime import datetime

timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
mem0_url = "http://localhost:8050/v1/memories/"
user_id = "sovereign"

with open("sovereign_status.md", "r") as f:
    status_content = f.read()

# Extract key metrics for Mem0 (shorter = faster LLM processing)
summary = f"""Remember these system facts from {timestamp}:
- GPU Blackwell has 92GB VRAM
- GPU RTX 5090 has 32GB VRAM  
- DeepSeek-V3.2 671B is the primary Oracle model
- System status is SOVEREIGN and OPERATIONAL
"""

payload = {
    "messages": [{"role": "user", "content": summary}],
    "user_id": user_id
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(mem0_url, data=data, method='POST')
req.add_header('Content-Type', 'application/json')

try:
    # 10 minute timeout for 671B model
    with urllib.request.urlopen(req, timeout=600) as response:
        result = response.read().decode()
        print(f"[{timestamp}] Mem0 Response: {result}")
except urllib.error.HTTPError as e:
    print(f"[{timestamp}] HTTP Error: {e.code} - {e.read().decode()}")
except urllib.error.URLError as e:
    print(f"[{timestamp}] URL Error: {e.reason}")
except Exception as e:
    print(f"[{timestamp}] Error: {e}")
PYEOF

echo "[$TIMESTAMP] Consciousness Loop: Pulse complete."
