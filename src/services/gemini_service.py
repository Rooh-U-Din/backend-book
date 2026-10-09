"""
Google Gemini API client wrapper for embeddings and completions
"""

import google.generativeai as genai
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
import time

# Ensure .env is loaded from root or backend directory
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class GeminiService:
    """Manages Google Gemini API operations"""

    DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"
    FALLBACK_EMBEDDING_MODEL = "models/gemini-embedding-001"

    @staticmethod
    def _resolve_embedding_model(model_name: str) -> str:
        """
        Normalize and migrate deprecated or retired embedding models.
        text-embedding-004 was retired by Google in favor of gemini-embedding-2.
        """
        if not model_name:
            return GeminiService.DEFAULT_EMBEDDING_MODEL

        clean_name = model_name.strip()
        if not clean_name.startswith("models/"):
            clean_name = f"models/{clean_name}"

        retired_models = {
            "models/text-embedding-004": GeminiService.DEFAULT_EMBEDDING_MODEL,
            "models/embedding-001": GeminiService.DEFAULT_EMBEDDING_MODEL,
        }

        if clean_name in retired_models:
            target = retired_models[clean_name]
            print(f"[GeminiService] Automatically migrating retired model '{clean_name}' to '{target}'")
            return target

        return clean_name

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure Gemini API
        genai.configure(api_key=self.api_key)

        # Initialize chat model
        chat_model_name = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
        self.chat_model = genai.GenerativeModel(chat_model_name)

        # Initialize embedding model (default to gemini-embedding-2, with auto-migration from text-embedding-004)
        raw_embedding_model = os.getenv("EMBEDDING_MODEL", self.DEFAULT_EMBEDDING_MODEL)
        self.embedding_model = self._resolve_embedding_model(raw_embedding_model)
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
        print(f"[GeminiService] Initialized with embedding model: {self.embedding_model} (dimension: {self.embedding_dimension})")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text chunk

        Args:
            text: Text to embed

        Returns:
            Embedding vector matching embedding_dimension
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=self.embedding_dimension
            )
            return result['embedding']
        except Exception as e:
            # Automatic fallback to gemini-embedding-001 if primary model fails
            if self.embedding_model != self.FALLBACK_EMBEDDING_MODEL:
                try:
                    print(f"[GeminiService] Primary embedding model '{self.embedding_model}' failed ({e}). Trying fallback '{self.FALLBACK_EMBEDDING_MODEL}'...")
                    result = genai.embed_content(
                        model=self.FALLBACK_EMBEDDING_MODEL,
                        content=text,
                        task_type="retrieval_document",
                        output_dimensionality=self.embedding_dimension
                    )
                    return result['embedding']
                except Exception as fallback_err:
                    print(f"[GeminiService] Fallback embedding model also failed: {fallback_err}")
            print(f"[GeminiService] Error generating embedding: {e}")
            raise

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query

        Args:
            query: Search query text

        Returns:
            Embedding vector matching embedding_dimension
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query",
                output_dimensionality=self.embedding_dimension
            )
            return result['embedding']
        except Exception as e:
            # Automatic fallback to gemini-embedding-001 if primary model fails
            if self.embedding_model != self.FALLBACK_EMBEDDING_MODEL:
                try:
                    print(f"[GeminiService] Primary query embedding model '{self.embedding_model}' failed ({e}). Trying fallback '{self.FALLBACK_EMBEDDING_MODEL}'...")
                    result = genai.embed_content(
                        model=self.FALLBACK_EMBEDDING_MODEL,
                        content=query,
                        task_type="retrieval_query",
                        output_dimensionality=self.embedding_dimension
                    )
                    return result['embedding']
                except Exception as fallback_err:
                    print(f"[GeminiService] Fallback query embedding also failed: {fallback_err}")
            print(f"[GeminiService] Error generating query embedding: {e}")
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
                task_type="retrieval_query",
                output_dimensionality=self.embedding_dimension
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
