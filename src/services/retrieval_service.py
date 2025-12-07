"""
Retrieval Service for RAG Chatbot

Handles vector search and chunk retrieval from Qdrant.

Author: Physical AI & Humanoid Robotics Course
License: MIT
"""

from typing import List, Optional
from services.qdrant_service import get_qdrant_service
from services.gemini_service import get_gemini_service
from models.embeddings import SearchResult, BookChunk, ChunkMetadata


class RetrievalService:
    """Retrieves relevant book chunks using vector similarity search"""

    def __init__(self):
        self.qdrant = get_qdrant_service()
        self.gemini = get_gemini_service()

    def query_similar_chunks(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Find chunks similar to query using vector search

        Args:
            query: User's question
            top_k: Number of results to return
            chapter_filter: Optional chapter_id to filter results

        Returns:
            List of SearchResult objects with chunks and scores
        """
        # Generate query embedding
        query_vector = self.gemini.generate_query_embedding(query)

        # Search Qdrant
        results = self.qdrant.search(
            query_vector=query_vector,
            limit=top_k,
            chapter_filter=chapter_filter
        )

        # Convert to SearchResult objects
        search_results = []
        for result in results:
            payload = result['payload']

            chunk = BookChunk(
                id=result['id'],
                vector=[],  # Don't return full vector
                chunk_text=payload.get('chunk_text', ''),
                metadata=ChunkMetadata(
                    chapter_id=payload.get('chapter_id', ''),
                    chapter_title=payload.get('chapter_title', ''),
                    section_title=payload.get('section_title', ''),
                    url_path=payload.get('url_path', ''),
                    chunk_index=payload.get('chunk_index', 0),
                    token_count=payload.get('token_count', 0),
                    created_at=payload.get('created_at', '')
                )
            )

            search_results.append(
                SearchResult(
                    chunk=chunk,
                    score=result['score']
                )
            )

        return search_results

    def query_with_selection(
        self,
        query: str,
        selected_text: str,
        chapter_id: str,
        top_k: int = 3
    ) -> List[SearchResult]:
        """
        Query with selection context - prioritize chunks from same chapter

        Args:
            query: User's question
            selected_text: Text user selected
            chapter_id: Current chapter
            top_k: Number of results

        Returns:
            List of SearchResult objects filtered by chapter
        """
        return self.query_similar_chunks(
            query=query,
            top_k=top_k,
            chapter_filter=chapter_id
        )


# Global retrieval service instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the global retrieval service instance"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
