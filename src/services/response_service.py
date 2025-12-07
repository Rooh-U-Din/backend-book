"""
Response Service for RAG Chatbot

Generates answers using Gemini with retrieved context.

Author: Physical AI & Humanoid Robotics Course
License: MIT
"""

from typing import List, Optional, Tuple
from services.gemini_service import get_gemini_service
from models.embeddings import SearchResult
from models.query import Citation


class ResponseService:
    """Generates answers from retrieved chunks using Gemini"""

    def __init__(self):
        self.gemini = get_gemini_service()

    def generate_answer(
        self,
        query: str,
        search_results: List[SearchResult],
        selected_text: Optional[str] = None
    ) -> Tuple[str, List[Citation], int]:
        """
        Generate answer from search results

        Args:
            query: User's question
            search_results: Retrieved chunks from Qdrant
            selected_text: Optional selected text for context

        Returns:
            Tuple of (answer_text, citations, latency_ms)
        """
        # Extract chunk texts for context
        context_chunks = [result.chunk.chunk_text for result in search_results]

        # Generate answer
        answer, latency_ms = self.gemini.generate_answer(
            query=query,
            context_chunks=context_chunks,
            selected_text=selected_text
        )

        # Extract citations
        citations = self._extract_citations(search_results)

        return answer, citations, latency_ms

    def _extract_citations(
        self,
        search_results: List[SearchResult]
    ) -> List[Citation]:
        """
        Extract citations from search results

        Args:
            search_results: Search results with metadata

        Returns:
            List of Citation objects
        """
        citations = []
        seen_chapters = set()  # Avoid duplicate citations from same chapter

        for result in search_results:
            chunk = result.chunk
            chapter_id = chunk.metadata.chapter_id

            # Skip if we already have citation from this chapter
            if chapter_id in seen_chapters:
                continue

            citation = Citation(
                chapter_id=chapter_id,
                chapter_title=chunk.metadata.chapter_title,
                section_title=chunk.metadata.section_title,
                url=chunk.metadata.url_path,
                relevance_score=result.score
            )

            citations.append(citation)
            seen_chapters.add(chapter_id)

            # Limit to top 3 citations
            if len(citations) >= 3:
                break

        return citations


# Global response service instance
_response_service: Optional[ResponseService] = None


def get_response_service() -> ResponseService:
    """Get or create the global response service instance"""
    global _response_service
    if _response_service is None:
        _response_service = ResponseService()
    return _response_service
