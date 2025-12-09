"""
Translation Service

Handles chapter translation using Google Translate (free) with caching.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, Tuple
from deep_translator import GoogleTranslator
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
        # Google Translate is free, no API key needed
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

    def _translate_with_google(self, content: str, target_language: SupportedLanguage) -> str:
        """
        Translate content using Google Translate (free).

        Args:
            content: Text to translate
            target_language: Target language

        Returns:
            Translated text
        """
        if target_language == SupportedLanguage.ENGLISH:
            return content  # No translation needed

        # Map language to Google Translate code
        lang_code = "ur" if target_language == SupportedLanguage.URDU else "en"

        try:
            # deep_translator has a limit of ~5000 chars per request
            max_chunk_size = 4500

            translator = GoogleTranslator(source='en', target=lang_code)

            if len(content) <= max_chunk_size:
                return translator.translate(content)

            # Split by paragraphs and translate in chunks
            paragraphs = content.split('\n\n')
            translated_parts = []
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    # Translate current chunk
                    if current_chunk.strip():
                        translated = translator.translate(current_chunk.strip())
                        translated_parts.append(translated)
                    current_chunk = para + "\n\n"

            # Translate remaining chunk
            if current_chunk.strip():
                translated = translator.translate(current_chunk.strip())
                translated_parts.append(translated)

            return "\n\n".join(translated_parts)

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

        # Translate using Google Translate
        translated_content = self._translate_with_google(content, target_language)

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
