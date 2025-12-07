"""
Google Gemini API client wrapper for embeddings and completions
"""

import google.generativeai as genai
import os
from typing import List, Optional
import time


class GeminiService:
    """Manages Google Gemini API operations"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure Gemini API
        genai.configure(api_key=self.api_key)

        # Initialize models
        self.chat_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self.embedding_model = 'models/embedding-001'

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text chunk

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query

        Args:
            query: Search query text

        Returns:
            768-dimensional embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            raise

    def generate_answer(
        self,
        query: str,
        context_chunks: List[str],
        selected_text: Optional[str] = None
    ) -> str:
        """
        Generate answer using Gemini with RAG context

        Args:
            query: User's question
            context_chunks: Retrieved text chunks for context
            selected_text: Optional selected text for selection mode

        Returns:
            Generated answer text
        """
        # Build prompt with context
        context = "\n\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(context_chunks)])

        if selected_text:
            prompt = f"""You are a helpful assistant for a Physical AI & Humanoid Robotics textbook.

The user has selected the following text:
{selected_text}

Based on the selected text and the following relevant sections from the book, answer the user's question.

Relevant sections:
{context}

Question: {query}

Please provide a clear, accurate answer based primarily on the selected text and supporting context. Include specific references to chapters or sections when relevant."""
        else:
            prompt = f"""You are a helpful assistant for a Physical AI & Humanoid Robotics textbook.

Based on the following relevant sections from the book, answer the user's question accurately and concisely.

Relevant sections:
{context}

Question: {query}

Please provide a clear answer and mention which chapters or sections you're referencing."""

        try:
            start_time = time.time()
            response = self.chat_model.generate_content(prompt)
            latency_ms = int((time.time() - start_time) * 1000)

            return response.text, latency_ms
        except Exception as e:
            print(f"Error generating answer: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Gemini API availability"""
        try:
            # Try a simple embedding operation
            genai.embed_content(
                model=self.embedding_model,
                content="test",
                task_type="retrieval_query"
            )
            return True
        except Exception as e:
            print(f"Gemini health check failed: {e}")
            return False


# Global Gemini service instance
gemini_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """Get or create the global Gemini service instance"""
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service
