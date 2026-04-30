"""
app.py — Pinterest Factory Dashboard
Main router. Initialises session state and renders all 4 tabs.
"""

import os
import sys
import shutil
from pathlib import Path

# Fix protobuf compatibility
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Clear corrupted ChromaDB cache on startup (prevents crash loops on Streamlit Cloud)
CHROMA_DIR = Path("data/chroma")
if CHROMA_DIR.exists():
    try:
        # Check if it's too large or potentially corrupted (LOWERED to 20MB)
        total_size = sum(f.stat().st_size for f in CHROMA_DIR.rglob('*') if f.is_file())
        if total_size > 20 * 1024 * 1024:  # > 20MB - more aggressive
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
            print("Cleared large ChromaDB cache (>20MB) on startup")
        # Also check for corrupted LevelDB files
        elif any(f.suffix == '.ldb' for f in CHROMA_DIR.rglob('*')):
            # LevelDB files present but DB might be corrupted
            if total_size > 5 * 1024 * 1024:  # If over 5MB with ldb files, could be corrupted
                shutil.rmtree(CHROMA_DIR, ignore_errors=True)
                print("Cleared potentially corrupted ChromaDB cache on startup")
    except Exception as e:
        print(f"Could not check ChromaDB: {e}")
        # Force clear if we can't even check
        try:
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
            print("Force-cleared ChromaDB after check failure")
        except:
            pass

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Install Playwright browsers on Streamlit Cloud startup
try:
    import playwright
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "playwright"])

@st.cache_resource
def install_playwright():
    """Install Chromium browser and dependencies for Streamlit Cloud."""
    import subprocess
    import sys
    
    try:
        print("Installing Playwright Chromium...")
        # Try installing chromium with more verbose output
        result = subprocess.run(
            ["python", "-m", "playwright", "install", "chromium"], 
            capture_output=True, 
            text=True, 
            timeout=180
        )
        
        if result.returncode == 0:
            print("Playwright Chromium installed successfully")
        else:
            print(f"Playwright install failed with code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
            # Try alternative approach - install all browsers
            print("Trying alternative: install all browsers...")
            result2 = subprocess.run(
                ["python", "-m", "playwright", "install"],
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result2.returncode == 0:
                print("Playwright browsers installed successfully")
            else:
                print(f"Alternative install failed: {result2.stderr}")
                
    except subprocess.TimeoutExpired:
        print("Playwright install timed out")
    except Exception as e:
        print(f"Error installing Playwright: {e}")

# Install on first run
install_playwright()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pinterest Factory · Recipe Content Tool",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global session state defaults ─────────────────────────────────────────────
DEFAULTS = {
    "batch_locked": False,
    "recipes": [],          # list of dicts from intake form
    "hooks": {},            # {recipe_name: {angle: hook_text}}
    "descriptions": {},     # {recipe_name: description_text}
    "notion_log": [],       # list of status strings
    "ai_generated": False,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px">
        <span style="font-size:26px;font-weight:600">📌 Pinterest Factory</span>
        <span style="font-size:14px;color:#888">Recipe Content Tool · batch pin production</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Status bar
col1, col2, col3, col4 = st.columns(4)
col1.metric("Recipes in batch", len(st.session_state.recipes))
col2.metric("Hooks generated", sum(len(v) for v in st.session_state.hooks.values()))
col3.metric("Pins ready to export", sum(len(v) for v in st.session_state.hooks.values()))
col4.metric("Synced to Notion", len([l for l in st.session_state.notion_log if "✅" in l]))

st.divider()

# ── Tab routing ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋  Step 1 · Batch Intake",
    "🤖  Step 2 · AI Copy Engine",
    "🎨  Step 3 · Pin Generation",
    "🗂️  Step 4 · Notion Sync",
])

from components.intake import render_intake
from components.ai_engine import render_ai_engine
from components.pin_generator import render_pin_generator
from components.notion_sync import render_notion_sync

with tab1:
    render_intake()

with tab2:
    render_ai_engine()

with tab3:
    render_pin_generator()

with tab4:
    render_notion_sync()
