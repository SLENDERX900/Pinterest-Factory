"""
memory_agent.py - STEP 2: The Reasoning Agent & Memory (Local & $0 Budget)
Implements Semantic Chunking, VectorDB with Qdrant, and Reasoning Verification Loop
"""

import os
import uuid
import time
import math
from typing import List, Dict, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain.text_splitter import RecursiveCharacterTextSplitter
import hashlib


class MemoryAgent:
    """
    Reasoning Agent with semantic memory and verification loop
    """
    
    def __init__(self, collection_name: str = "pinterest-trends"):
        self.collection_name = collection_name
        self.embedding_model = None
        self.qdrant_client = None
        self.text_splitter = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all components for semantic memory"""
        try:
            # Initialize embedding model (free Hugging Face model)
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Embedding model loaded: all-MiniLM-L6-v2")
            
            # Initialize Qdrant client (local instance)
            self.qdrant_client = QdrantClient(path="./data/qdrant")
            print("✅ Qdrant client initialized (local)")
            
            # Initialize text splitter for semantic chunking
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=200,
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            print("✅ Semantic chunking initialized")
            
            # Create collection if it doesn't exist
            self._create_collection()
            
        except Exception as e:
            print(f"❌ Memory agent initialization failed: {e}")
    
    def _create_collection(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 embedding dimension
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created collection: {self.collection_name}")
            else:
                print(f"✅ Collection exists: {self.collection_name}")
                
        except Exception as e:
            print(f"❌ Collection creation failed: {e}")
    
    def process_pinterest_pins(self, pins: List[Dict]) -> int:
        """
        Process Pinterest pins through semantic chunking and store in VectorDB
        Returns number of chunks stored
        """
        if not pins:
            print("⚠️ No pins to process")
            return 0
        
        print(f"🧠 Processing {len(pins)} Pinterest pins through semantic chunking...")
        
        total_chunks = 0
        
        for pin in pins:
            # Combine title and description for chunking
            text_content = f"{pin.get('title', '')} {pin.get('description', '')}"
            
            if not text_content.strip():
                continue
            
            # Semantic chunking
            chunks = self.text_splitter.split_text(text_content)
            
            # Embed and store each chunk
            for chunk in chunks:
                if len(chunk.strip()) < 10:
                    continue
                
                # Generate embedding
                embedding = self.embedding_model.encode(chunk).tolist()
                
                # Generate deterministic UUID
                chunk_id = self._generate_uuid(chunk)
                
                # Store in Qdrant
                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        'text': chunk,
                        'source_pin_title': pin.get('title', ''),
                        'source_pin_saves': pin.get('save_count', 0),
                        'chunk_index': total_chunks,
                        'timestamp': time.time()
                    }
                )
                
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                
                total_chunks += 1
        
        print(f"✅ Processed and stored {total_chunks} semantic chunks")
        return total_chunks
    
    def _generate_uuid(self, text: str) -> str:
        """Generate deterministic UUID from text"""
        hash_obj = hashlib.md5(text.encode())
        return str(uuid.UUID(bytes=hash_obj.digest()))
    
    def reasoning_verification_loop(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Implement the "Reasoning Verification Loop": 
        Query VectorDB, read top-performing chunks, output "Learning Summary"
        """
        print(f"🤖 Running Reasoning Verification Loop for query: {query}")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Query Qdrant for similar chunks
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=0.3
            )
            
            if not search_results:
                print("⚠️ No similar chunks found in memory")
                return {
                    'learning_summary': 'No relevant Pinterest trends found in memory',
                    'top_chunks': [],
                    'psychological_triggers': [],
                    'engagement_insights': []
                }
            
            # Extract top chunks
            top_chunks = []
            for result in search_results:
                chunk_data = {
                    'text': result.payload.get('text', ''),
                    'source_pin_title': result.payload.get('source_pin_title', ''),
                    'source_pin_saves': result.payload.get('source_pin_saves', 0),
                    'similarity_score': result.score
                }
                top_chunks.append(chunk_data)
            
            # Generate Learning Summary (analyze why these hooks work)
            learning_summary = self._generate_learning_summary(top_chunks)
            
            # Identify psychological triggers
            psychological_triggers = self._identify_psychological_triggers(top_chunks)
            
            # Generate engagement insights
            engagement_insights = self._generate_engagement_insights(top_chunks)
            
            print(f"✅ Reasoning Verification Loop completed")
            print(f"📊 Found {len(top_chunks)} relevant chunks")
            print(f"🧠 Learning Summary: {learning_summary[:100]}...")
            
            return {
                'learning_summary': learning_summary,
                'top_chunks': top_chunks,
                'psychological_triggers': psychological_triggers,
                'engagement_insights': engagement_insights
            }
            
        except Exception as e:
            print(f"❌ Reasoning Verification Loop failed: {e}")
            return {
                'learning_summary': f'Reasoning loop failed: {str(e)}',
                'top_chunks': [],
                'psychological_triggers': [],
                'engagement_insights': []
            }
    
    def _generate_learning_summary(self, chunks: List[Dict]) -> str:
        """Generate learning summary analyzing why these hooks work"""
        if not chunks:
            return "No chunks available for analysis"
        
        # Analyze common patterns
        common_words = []
        high_saving_chunks = [c for c in chunks if c.get('source_pin_saves', 0) > 1000]
        
        for chunk in high_saving_chunks[:3]:
            words = chunk.get('text', '').split()
            common_words.extend([w.lower() for w in words if len(w) > 4])
        
        # Get most common words
        from collections import Counter
        word_counts = Counter(common_words)
        top_words = [word for word, count in word_counts.most_common(5)]
        
        summary = f"High-performing pins emphasize: {', '.join(top_words)}. "
        summary += f"Pattern analysis shows {len(high_saving_chunks)} high-engagement pins using similar language patterns. "
        summary += "These hooks work because they combine urgency, specificity, and emotional appeal."
        
        return summary
    
    def _identify_psychological_triggers(self, chunks: List[Dict]) -> List[str]:
        """Identify psychological triggers from top chunks"""
        triggers = []
        
        trigger_keywords = {
            'urgency': ['quick', 'fast', 'easy', 'instant', 'ready', 'now'],
            'authority': ['best', 'perfect', 'ultimate', 'expert', 'pro'],
            'social_proof': ['popular', 'trending', 'viral', 'favorite', 'loved'],
            'scarcity': ['limited', 'rare', 'exclusive', 'special', 'only'],
            'curiosity': ['secret', 'hidden', 'discover', 'amazing', 'surprise']
        }
        
        for chunk in chunks:
            text = chunk.get('text', '').lower()
            for trigger, keywords in trigger_keywords.items():
                if any(kw in text for kw in keywords):
                    if trigger not in triggers:
                        triggers.append(trigger)
        
        return triggers[:5]  # Limit to top 5 triggers
    
    def _generate_engagement_insights(self, chunks: List[Dict]) -> List[str]:
        """Generate engagement insights from chunk data"""
        insights = []
        
        if not chunks:
            return insights
        
        # Calculate average save count
        save_counts = [c.get('source_pin_saves', 0) for c in chunks]
        avg_saves = sum(save_counts) / len(save_counts) if save_counts else 0
        
        insights.append(f"Average saves: {int(avg_saves):,}")
        
        # Identify high performers
        high_performers = [c for c in chunks if c.get('source_pin_saves', 0) > avg_saves * 1.5]
        if high_performers:
            insights.append(f"{len(high_performers)} high-performing pins identified")
        
        # Similarity analysis
        avg_similarity = sum(c.get('similarity_score', 0) for c in chunks) / len(chunks)
        insights.append(f"Average similarity: {avg_similarity:.2f}")
        
        return insights


# Convenience function
def run_reasoning_loop(query: str, pins: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function for the reasoning verification loop
    """
    agent = MemoryAgent()
    
    # Process pins first
    agent.process_pinterest_pins(pins)
    
    # Run reasoning loop
    return agent.reasoning_verification_loop(query)
