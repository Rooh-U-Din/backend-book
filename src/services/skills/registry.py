"""
Skill Registry for dynamic skill management.

Provides a central registry for skill registration, lookup, and listing.
Skills are registered at application startup.
"""

from typing import Dict, List, Optional, Type
from .base import BaseSkill


class SkillRegistry:
    """
    Central registry for skill management.

    Provides methods to register, retrieve, and list skills.
    Skills are stored by their skill_id for O(1) lookup.

    Usage:
        # Register a skill
        registry.register(ExplainSkill())

        # Get a skill by ID
        skill = registry.get("explain")
        if skill:
            result = await skill.execute(context, selected_text="...")

        # List all enabled skills
        skills = registry.list_all(enabled_only=True)
    """

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """
        Register a skill instance.

        Args:
            skill: Skill instance to register

        Raises:
            ValueError: If skill_id is empty or already registered
        """
        if not skill.skill_id:
            raise ValueError(f"Skill {skill.__class__.__name__} has no skill_id defined")

        if skill.skill_id in self._skills:
            raise ValueError(f"Skill '{skill.skill_id}' is already registered")

        self._skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> Optional[BaseSkill]:
        """
        Get a skill by ID.

        Args:
            skill_id: The skill identifier

        Returns:
            The skill instance or None if not found
        """
        return self._skills.get(skill_id)

    def get_enabled(self, skill_id: str) -> Optional[BaseSkill]:
        """
        Get an enabled skill by ID.

        Args:
            skill_id: The skill identifier

        Returns:
            The skill instance if found and enabled, None otherwise
        """
        skill = self._skills.get(skill_id)
        if skill and skill.enabled:
            return skill
        return None

    def list_all(self, enabled_only: bool = True) -> List[BaseSkill]:
        """
        List all registered skills.

        Args:
            enabled_only: If True, only return enabled skills

        Returns:
            List of skill instances
        """
        if enabled_only:
            return [s for s in self._skills.values() if s.enabled]
        return list(self._skills.values())

    def is_registered(self, skill_id: str) -> bool:
        """
        Check if a skill is registered.

        Args:
            skill_id: The skill identifier

        Returns:
            True if skill is registered
        """
        return skill_id in self._skills

    def unregister(self, skill_id: str) -> bool:
        """
        Unregister a skill.

        Args:
            skill_id: The skill identifier

        Returns:
            True if skill was unregistered, False if not found
        """
        if skill_id in self._skills:
            del self._skills[skill_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all registered skills."""
        self._skills.clear()

    def __len__(self) -> int:
        """Return number of registered skills."""
        return len(self._skills)

    def __contains__(self, skill_id: str) -> bool:
        """Check if skill_id is registered."""
        return skill_id in self._skills


# Global singleton instance
skill_registry = SkillRegistry()
