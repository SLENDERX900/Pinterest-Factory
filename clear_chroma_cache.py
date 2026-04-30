"""
Utility to clear ChromaDB cache when disk space errors occur.
Run this if you see: FILE_ERROR_NO_SPACE or similar ChromaDB errors.
"""

import shutil
import os
from pathlib import Path

DB_DIR = Path("data/chroma")
DATA_DIR = Path("data")

if __name__ == "__main__":
    cleared = False
    
    # Clear main ChromaDB directory
    if DB_DIR.exists():
        try:
            size_mb = sum(f.stat().st_size for f in DB_DIR.rglob('*') if f.is_file()) / (1024*1024)
            print(f"Clearing ChromaDB cache at: {DB_DIR} ({size_mb:.1f} MB)")
        except:
            print(f"Clearing ChromaDB cache at: {DB_DIR}")
        shutil.rmtree(DB_DIR, ignore_errors=True)
        cleared = True
    
    # Clear any stray .ldb files in current directory (LevelDB fragments)
    ldb_files = list(Path(".").glob("*.ldb"))
    if ldb_files:
        print(f"Found {len(ldb_files)} stray LevelDB files, removing...")
        for f in ldb_files:
            try:
                f.unlink()
            except:
                pass
        cleared = True
    
    # Clear any LOCK files
    lock_files = list(Path(".").glob("*.lock")) + list(Path(".").glob("LOCK"))
    if lock_files:
        for f in lock_files:
            try:
                f.unlink()
            except:
                pass
    
    if cleared:
        print("✅ ChromaDB cache cleared successfully")
        print("Restart your Streamlit app to recreate the database.")
        
        # Also suggest checking disk space
        try:
            import shutil as sh
            total, used, free = sh.disk_usage(".")
            print(f"\nDisk space: {free / (1024*1024):.0f} MB free / {total / (1024*1024):.0f} MB total")
            if free < 100 * 1024 * 1024:  # Less than 100MB
                print("⚠️  Warning: Low disk space detected!")
        except:
            pass
    else:
        print("No ChromaDB cache found to clear.")
