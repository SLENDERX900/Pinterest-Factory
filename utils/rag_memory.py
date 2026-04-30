"""
Local ChromaDB memory for Pinterest trend context.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    import os
    QDRANT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Qdrant not available: {e}")
    print("Falling back to simple in-memory storage")
    QDRANT_AVAILABLE = False

from sentence_transformers import SentenceTransformer

DB_DIR = Path("data/qdrant")
COLLECTION_NAME = "pinterest-trends"
DIMENSION = 384  # all-MiniLM-L6-v2 embedding dimension
EMBED_MODEL = "all-MiniLM-L6-v2"

_embedder = None
_qdrant_client = None
_fallback_storage = {}


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        if globals().get('QDRANT_AVAILABLE', False):
            try:
                # Initialize Qdrant client (local mode for free usage)
                DB_DIR.mkdir(parents=True, exist_ok=True)
                _qdrant_client = QdrantClient(path=str(DB_DIR))
                
                # Create collection if it doesn't exist
                collections = _qdrant_client.get_collections().collections
                collection_names = [c.name for c in collections]
                
                if COLLECTION_NAME not in collection_names:
                    _qdrant_client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=DIMENSION,
                            distance=Distance.COSINE
                        )
                    )
                    print(f"Created Qdrant collection: {COLLECTION_NAME}")
                else:
                    print(f"Connected to Qdrant collection: {COLLECTION_NAME}")
                
            except Exception as e:
                print(f"Error initializing Qdrant: {e}")
                print("Falling back to in-memory storage")
                globals()['QDRANT_AVAILABLE'] = False
                return None
        else:
            return None
    
    return _qdrant_client


def store_trending_pins(pins: list[dict]) -> int:
    if not pins:
        return 0
    embedder = _get_embedder()
    qdrant_client = _get_qdrant_client()

    texts = []
    ids = []
    metadatas = []
    for pin in pins:
        text = f"{pin.get('title', '')}\n{pin.get('description', '')}".strip()
        if not text:
            continue
        # Generate a valid UUID based on the content hash
        content_hash = hashlib.sha256(f"{text}|{pin.get('pin_url','')}".encode("utf-8")).hexdigest()
        pid = str(uuid.UUID(hashlib.sha256(content_hash.encode()).hexdigest()[0:32]))
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
    
    if globals().get('QDRANT_AVAILABLE', False) and qdrant_client:
        # Store in Qdrant
        points = []
        for i, (pid, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
            points.append(PointStruct(
                id=pid,
                vector=embedding,
                payload={**metadata, "text": texts[i]}
            ))
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            
        print(f"Stored {len(texts)} pins in Qdrant")
    else:
        # Fallback storage
        for i, (text, pid, metadata) in enumerate(zip(texts, ids, metadatas)):
            _fallback_storage[pid] = {
                "text": text,
                "embedding": embeddings[i],
                "metadata": metadata
            }
        print(f"Stored {len(texts)} pins in fallback memory")
    
    return len(texts)


def query_similar_trends(query_text: str, top_k: int = 5) -> list[dict]:
    if not query_text.strip():
        return []
    embedder = _get_embedder()
    qdrant_client = _get_qdrant_client()
    query_embedding = embedder.encode([query_text]).tolist()[0]
    
    if globals().get('QDRANT_AVAILABLE', False) and qdrant_client:
        try:
            # Query Qdrant
            results = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=0.0
            )
            
            items = []
            for hit in results:
                payload = hit.payload or {}
                items.append({
                    "text": payload.get("text", ""),
                    "title": payload.get("title", ""),
                    "description": payload.get("description", ""),
                    "image_url": payload.get("image_url", ""),
                    "pin_url": payload.get("pin_url", ""),
                    "source": payload.get("source", ""),
                    "score": hit.score
                })
            
            print(f"Found {len(items)} similar trends in Qdrant")
            return items
            
        except Exception as e:
            print(f"Error querying Qdrant: {e}")
            print("Falling back to in-memory search")
            globals()['QDRANT_AVAILABLE'] = False
            return _fallback_query(query_embedding, top_k)
    else:
        # Fallback: simple cosine similarity search
        return _fallback_query(query_embedding, top_k)


def _fallback_query(query_embedding: list, top_k: int = 5) -> list[dict]:
    """Fallback in-memory similarity search"""
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    if not _fallback_storage:
        return []
    
    # Calculate similarities
    stored_embeddings = [item["embedding"] for item in _fallback_storage.values()]
    similarities = cosine_similarity([query_embedding], stored_embeddings)[0]
    
    # Get top-k most similar items
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    items = []
    for idx in top_indices:
        item_key = list(_fallback_storage.keys())[idx]
        item = _fallback_storage[item_key]
        items.append({"text": item["text"], **item["metadata"]})
    
    print(f"Found {len(items)} similar trends in fallback memory")
    return items
