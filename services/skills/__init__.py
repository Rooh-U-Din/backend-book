"""
Skills module for Reusable Intelligence Subagents.

This module provides the skill registry and individual skill implementations
for the Physical AI Book chatbot enhancement.
"""

from .registry import skill_registry, SkillRegistry
from .base import BaseSkill, AgentContext, SkillResult

# Import and register skills
from .explain_skill import ExplainSkill

# Register all skills at module load
def _register_skills():
    """Register all available skills with the global registry."""
    skills = [
        ExplainSkill(),
    ]
    for skill in skills:
        if not skill_registry.is_registered(skill.skill_id):
            skill_registry.register(skill)

_register_skills()

__all__ = [
    'skill_registry',
    'SkillRegistry',
    'BaseSkill',
    'AgentContext',
    'SkillResult',
    'ExplainSkill',
]
