"""
Local ChromaDB memory for Pinterest trend context.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DB_DIR = Path("data/chroma")
COLLECTION_NAME = "pinterest_trends"
EMBED_MODEL = "all-MiniLM-L6-v2"

_embedder = None
_collection = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _get_collection():
    global _collection
    if _collection is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = client.get_or_create_collection(COLLECTION_NAME)
    return _collection


def store_trending_pins(pins: list[dict]) -> int:
    if not pins:
        return 0
    embedder = _get_embedder()
    collection = _get_collection()

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


def query_similar_trends(query_text: str, top_k: int = 5) -> list[dict]:
    if not query_text.strip():
        return []
    embedder = _get_embedder()
    collection = _get_collection()
    query_embedding = embedder.encode([query_text]).tolist()[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    items = []
    for i, doc in enumerate(results.get("documents", [[]])[0]):
        meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
        items.append({"text": doc, **(meta or {})})
    return items
