"""
Translation Service

Handles chapter translation using Gemini API with caching.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

from models.translation import (
    ChapterTranslation,
    TranslationResponse,
    SupportedLanguage,
    UserTranslationPreference
)

load_dotenv()


class TranslationService:
    """Service for translating chapter content with caching"""

    def __init__(self):
        # Use separate API key for translation (falls back to GEMINI_API_KEY if not set)
        self.api_key = os.getenv("TRANSLATION_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("TRANSLATION_API_KEY or GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

        # In-memory cache (use Redis/DB in production)
        self._translation_cache: Dict[str, ChapterTranslation] = {}
        self._user_preferences: Dict[str, UserTranslationPreference] = {}

    def _compute_content_hash(self, content: str) -> str:
        """Compute MD5 hash of content for cache invalidation"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _get_cache_key(self, chapter_id: str, language: SupportedLanguage) -> str:
        """Generate cache key for a translation"""
        return f"{chapter_id}:{language.value}"

    def get_cached_translation(
        self,
        chapter_id: str,
        language: SupportedLanguage,
        content_hash: Optional[str] = None
    ) -> Optional[ChapterTranslation]:
        """
        Retrieve cached translation if available and valid.

        Args:
            chapter_id: Chapter identifier
            language: Target language
            content_hash: Optional hash to validate cache freshness

        Returns:
            Cached translation or None
        """
        cache_key = self._get_cache_key(chapter_id, language)
        cached = self._translation_cache.get(cache_key)

        if cached:
            # If content_hash provided, verify cache is still valid
            if content_hash and cached.original_content_hash != content_hash:
                # Content changed, invalidate cache
                del self._translation_cache[cache_key]
                return None
            return cached

        return None

    def _translate_with_gemini(self, content: str, target_language: SupportedLanguage) -> str:
        """
        Translate content using Gemini API.

        Args:
            content: Text to translate
            target_language: Target language

        Returns:
            Translated text
        """
        if target_language == SupportedLanguage.ENGLISH:
            return content  # No translation needed

        language_name = "Urdu" if target_language == SupportedLanguage.URDU else target_language.value

        # List of technical terms to preserve
        preserve_terms = [
            "ROS 2", "ROS2", "ROS 1", "ROS", "Gazebo", "NVIDIA", "Isaac", "Isaac Sim", "Isaac ROS",
            "Unity", "Python", "C++", "Ubuntu", "Linux", "Windows", "macOS", "Docker", "Git", "GitHub",
            "API", "SDK", "CLI", "GUI", "IDE", "JSON", "YAML", "XML", "HTML", "CSS", "JavaScript",
            "HTTP", "HTTPS", "REST", "GraphQL", "WebSocket", "TCP", "UDP", "IP", "DDS",
            "GPU", "CPU", "RAM", "SSD", "CUDA", "TensorRT", "PyTorch", "TensorFlow", "OpenCV",
            "SLAM", "LIDAR", "LiDAR", "IMU", "GPS", "URDF", "SDF", "XACRO", "TF2",
            "PCL", "MoveIt", "Nav2", "rclpy", "rclcpp", "ament", "colcon",
            "Humble", "Iron", "Jazzy", "Noetic", "Melodic", "Foxy",
            "VLA", "RT-1", "RT-2", "OpenVLA", "Whisper", "GPT", "LLM",
            "FastAPI", "Uvicorn", "Pydantic", "SQLAlchemy", "Qdrant", "PostgreSQL",
            "npm", "Node.js", "React", "Docusaurus", "TypeScript",
        ]

        prompt = f"""You are an expert Urdu translator specializing in technical and educational content about robotics and artificial intelligence.

Your task: Translate the following content into high-quality, natural Urdu that reads like it was originally written in Urdu.

CRITICAL RULES:
1. DO NOT translate these technical terms (keep them in English): {', '.join(preserve_terms)}
2. DO NOT translate:
   - Code snippets, commands, or file paths
   - Variable names, function names, class names
   - URLs, email addresses
   - Version numbers (e.g., v2.0, 3.14)
3. DO translate:
   - All explanatory text and descriptions
   - Headers and section titles (but keep technical terms in English within them)
   - Bullet points and list items
4. Use proper Urdu grammar and sentence structure
5. Make the translation sound natural and professional, not machine-like
6. Preserve paragraph breaks and structure

Content to translate:
---
{content}
---

Provide ONLY the Urdu translation. No explanations or notes."""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Translation error: {e}")
            raise RuntimeError(f"Translation failed: {str(e)}")

    async def translate_chapter(
        self,
        chapter_id: str,
        content: str,
        target_language: SupportedLanguage = SupportedLanguage.URDU
    ) -> Tuple[TranslationResponse, int]:
        """
        Translate chapter content with caching.

        Args:
            chapter_id: Chapter identifier
            content: Chapter content to translate
            target_language: Target language (default: Urdu)

        Returns:
            Tuple of (TranslationResponse, latency_ms)
        """
        import time
        start_time = time.time()

        # Compute content hash for cache validation
        content_hash = self._compute_content_hash(content)

        # Check cache first
        cached = self.get_cached_translation(chapter_id, target_language, content_hash)
        if cached:
            latency_ms = int((time.time() - start_time) * 1000)
            return TranslationResponse(
                chapter_id=chapter_id,
                language=target_language,
                translated_content=cached.translated_content,
                cached=True,
                translated_at=cached.updated_at
            ), latency_ms

        # Translate using Gemini
        translated_content = self._translate_with_gemini(content, target_language)

        # Cache the translation
        now = datetime.utcnow()
        translation = ChapterTranslation(
            chapter_id=chapter_id,
            language=target_language,
            original_content_hash=content_hash,
            translated_content=translated_content,
            created_at=now,
            updated_at=now
        )

        cache_key = self._get_cache_key(chapter_id, target_language)
        self._translation_cache[cache_key] = translation

        latency_ms = int((time.time() - start_time) * 1000)

        return TranslationResponse(
            chapter_id=chapter_id,
            language=target_language,
            translated_content=translated_content,
            cached=False,
            translated_at=now
        ), latency_ms

    def set_user_preference(
        self,
        session_id: str,
        chapter_id: str,
        language: SupportedLanguage
    ) -> UserTranslationPreference:
        """
        Store user's language preference for a chapter.

        Args:
            session_id: User session ID
            chapter_id: Chapter identifier
            language: Preferred language

        Returns:
            Updated preference
        """
        pref_key = f"{session_id}:{chapter_id}"
        preference = UserTranslationPreference(
            session_id=session_id,
            chapter_id=chapter_id,
            preferred_language=language,
            updated_at=datetime.utcnow()
        )
        self._user_preferences[pref_key] = preference
        return preference

    def get_user_preference(
        self,
        session_id: str,
        chapter_id: str
    ) -> Optional[UserTranslationPreference]:
        """
        Get user's language preference for a chapter.

        Args:
            session_id: User session ID
            chapter_id: Chapter identifier

        Returns:
            User preference or None
        """
        pref_key = f"{session_id}:{chapter_id}"
        return self._user_preferences.get(pref_key)

    def get_cache_stats(self) -> Dict:
        """Get translation cache statistics"""
        return {
            "cached_translations": len(self._translation_cache),
            "user_preferences": len(self._user_preferences),
            "chapters_with_urdu": [
                k.split(":")[0] for k in self._translation_cache.keys()
                if k.endswith(":urdu")
            ]
        }


# Global service instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create the global translation service instance"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
