"""
STEP 2: Free RAG Memory (ChromaDB)
Local ChromaDB memory for Pinterest trend context with disk space management.
Uses Hugging Face all-MiniLM-L6-v2 model for embeddings.
"""

from __future__ import annotations

import hashlib
import shutil
import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DB_DIR = Path("data/chroma")
COLLECTION_NAME = "pinterest_trends"
EMBED_MODEL = "all-MiniLM-L6-v2"
MAX_COLLECTION_SIZE = 500  # Maximum number of items to prevent disk fill

_embedder = None
_collection = None
_client = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _get_db_size_mb() -> float:
    """Calculate current database size in MB."""
    if not DB_DIR.exists():
        return 0.0
    total_size = 0
    for item in DB_DIR.rglob('*'):
        if item.is_file():
            total_size += item.stat().st_size
    return total_size / (1024 * 1024)


def _cleanup_old_entries(collection, keep_count: int = MAX_COLLECTION_SIZE):
    """Remove oldest entries to keep collection under size limit."""
    try:
        # Get all items
        all_items = collection.get()
        if all_items and 'ids' in all_items:
            total_items = len(all_items['ids'])
            if total_items > keep_count:
                # Delete oldest items (assuming sequential IDs)
                items_to_delete = total_items - keep_count
                ids_to_delete = all_items['ids'][:items_to_delete]
                collection.delete(ids=ids_to_delete)
                logger.info(f"Cleaned up {items_to_delete} old entries from ChromaDB")
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")


def _reset_database():
    """Clear the entire database if it's corrupted or full."""
    global _collection, _client
    try:
        if DB_DIR.exists():
            shutil.rmtree(DB_DIR)
            logger.warning("Reset ChromaDB database due to disk space/corruption")
        _collection = None
        _client = None
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")


def _get_collection():
    global _collection, _client
    if _collection is None:
        try:
            DB_DIR.mkdir(parents=True, exist_ok=True)
            
            # Check available disk space (rough estimate)
            db_size = _get_db_size_mb()
            if db_size > 100:  # If DB is over 100MB, clear it
                logger.warning(f"ChromaDB size ({db_size:.1f}MB) exceeds limit, resetting")
                _reset_database()
            
            _client = chromadb.PersistentClient(path=str(DB_DIR))
            _collection = _client.get_or_create_collection(COLLECTION_NAME)
            
            # Clean up if too large
            _cleanup_old_entries(_collection)
            
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            # Fallback: try to reset and recreate
            _reset_database()
            try:
                DB_DIR.mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(path=str(DB_DIR))
                _collection = _client.get_or_create_collection(COLLECTION_NAME)
            except Exception as e2:
                logger.critical(f"ChromaDB completely failed: {e2}")
                raise
    return _collection


def store_trending_pins(pins: list[dict]) -> int:
    """Store pins in ChromaDB with disk space protection."""
    if not pins:
        return 0
    
    try:
        embedder = _get_embedder()
        collection = _get_collection()
        
        # Pre-cleanup if approaching limit
        try:
            current = collection.count()
            if current > MAX_COLLECTION_SIZE:
                _cleanup_old_entries(collection, MAX_COLLECTION_SIZE // 2)
        except Exception:
            pass

        texts = []
        ids = []
        metadatas = []
        for pin in pins:
            text = f"{pin.get('title', '')}\n{pin.get('description', '')}".strip()
            if not text:
                continue
            pid = hashlib.sha1(f"{text}|{pin.get('pin_url','')}".encode("utf-8")).hexdigest()
            texts.append(text)
            ids.append(pid)
            metadatas.append(
                {
                    "title": pin.get("title", ""),
                    "description": pin.get("description", ""),
                    "image_url": pin.get("image_url", ""),
                    "pin_url": pin.get("pin_url", ""),
                    "source": pin.get("source", ""),
                }
            )
        if not texts:
            return 0

        embeddings = embedder.encode(texts).tolist()
        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        return len(texts)
        
    except Exception as e:
        logger.error(f"Failed to store pins: {e}")
        # Try to reset and continue
        _reset_database()
        return 0


def query_similar_trends(query_text: str, top_k: int = 5) -> list[dict]:
    """Query similar trends with error handling for disk issues."""
    if not query_text.strip():
        return []
    
    try:
        embedder = _get_embedder()
        collection = _get_collection()
        query_embedding = embedder.encode([query_text]).tolist()[0]
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        items = []
        for i, doc in enumerate(results.get("documents", [[]])[0]):
            meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
            items.append({"text": doc, **(meta or {})})
        return items
    except Exception as e:
        logger.error(f"Query failed: {e}")
        # Reset and return empty on critical failure
        _reset_database()
        return []
