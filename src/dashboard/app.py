import streamlit as st
import requests
import time

# --- CONFIG ---
OMNI_HOST = "http://100.94.47.77"
PORTS = {
    "DeepSeek (Main)": 8000,
    "Qwen (Fast)": 8002,
    "Lazarus (Blackwell)": 8004
}

st.set_page_config(page_title="Protocol Omni | Overseer", layout="wide")

st.title("👁️ Protocol Omni: Overseer Node")
st.markdown("---")

# --- SIDEBAR STATUS ---
st.sidebar.header("System Status")

for name, port in PORTS.items():
    url = f"{OMNI_HOST}:{port}/v1/models"
    status_col, name_col = st.sidebar.columns([1, 4])
    
    try:
        response = requests.get(url, timeout=1)
        if response.status_code == 200:
            status_col.success("●")
            name_col.write(f"**{name}** (Online)")
        else:
            status_col.warning("●")
            name_col.write(f"**{name}** ({response.status_code})")
    except:
        status_col.error("●")
        name_col.write(f"**{name}** (Offline)")

# --- MAIN DASHBOARD ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 Cortex Telemetry")
    st.info("Awaiting connection to Agent Event Bus...")

with col2:
    st.subheader("⚡ Hardware Stats")
    st.metric(label="System GPU", value="NVIDIA Blackwell B200", delta="Active")

st.caption(f"Connected via Tailscale Mesh to {OMNI_HOST}")
