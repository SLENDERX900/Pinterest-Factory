"""
Utility to clear ChromaDB cache when disk space errors occur.
Run this if you see: FILE_ERROR_NO_SPACE or similar ChromaDB errors.
"""

import shutil
from pathlib import Path

DB_DIR = Path("data/chroma")

if __name__ == "__main__":
    if DB_DIR.exists():
        print(f"Clearing ChromaDB cache at: {DB_DIR}")
        print(f"Current size: {sum(f.stat().st_size for f in DB_DIR.rglob('*') if f.is_file()) / (1024*1024):.1f} MB")
        shutil.rmtree(DB_DIR)
        print("✅ ChromaDB cache cleared successfully")
        print("Restart your Streamlit app to recreate the database.")
    else:
        print("No ChromaDB cache found to clear.")
