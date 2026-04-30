"""
app.py — Pinterest Factory Dashboard
Main router. Initialises session state and renders all 4 tabs.
"""

import os
# Silence transformers warnings before any imports
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from dotenv import load_dotenv
import importlib
import sys
import warnings

# Suppress transformers path access warnings
warnings.filterwarnings("ignore", message=".*Accessing `__path__` from.*")
warnings.filterwarnings("ignore", message=".*Behavior may be different and this alias will be removed.*")

# Force reload of modules to see changes
modules_to_reload = ['utils.groq_client', 'utils.rag_memory', 'utils.web_scraper']
for module in modules_to_reload:
    if module in sys.modules:
        importlib.reload(sys.modules[module])

load_dotenv()

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

# Debug controls (only in development)
if st.sidebar.button("🔄 Clear Session State"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    for key, val in DEFAULTS.items():
        st.session_state[key] = val
    st.success("Session state cleared!")
    st.rerun()

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
