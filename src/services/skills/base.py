"""
Base classes for the Skill system.

Provides abstract base class for skill implementations and data structures
for context passing and result formatting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


@dataclass
class AgentContext:
    """
    Contextual information passed to skills during execution.

    This dataclass aggregates all contextual information needed by skills
    and is serialized to the SkillInvocation.context field for debugging.
    """
    user_id: str
    user_email: str
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None
    selected_text: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'user_email': self.user_email,
            'trace_id': self.trace_id,
            'timestamp': self.timestamp.isoformat(),
            'chapter_id': self.chapter_id,
            'chapter_title': self.chapter_title,
            'selected_text': self.selected_text[:500] if self.selected_text else None,
            'user_profile': self.user_profile,
        }


@dataclass
class Citation:
    """Reference to related content in the book."""
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chapter_id': self.chapter_id,
            'chapter_title': self.chapter_title,
            'section_title': self.section_title,
            'url': self.url,
        }


@dataclass
class Suggestion:
    """Follow-up action suggestion."""
    type: str  # 'skill', 'chapter', 'topic'
    label: str
    skill_id: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'label': self.label,
            'skill_id': self.skill_id,
            'description': self.description,
        }


@dataclass
class SkillResult:
    """
    Result from skill execution.

    Contains the generated content along with optional citations
    and suggestions for follow-up actions.
    """
    content: str
    citations: List[Citation] = field(default_factory=list)
    suggestions: List[Suggestion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'citations': [c.to_dict() for c in self.citations] if self.citations else None,
            'suggestions': [s.to_dict() for s in self.suggestions] if self.suggestions else None,
        }


class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    Skills must implement the execute() method and provide metadata
    through the skill_id, name, description, and version properties.

    Example implementation:
        class ExplainSkill(BaseSkill):
            skill_id = "explain"
            name = "Code Explanation"
            description = "Explains code in plain language"
            version = "1.0.0"

            async def execute(self, context: AgentContext, **kwargs) -> SkillResult:
                selected_text = kwargs.get('selected_text')
                # ... implementation
                return SkillResult(content="Explanation here")
    """

    # Subclasses must define these class attributes
    skill_id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True

    # Input schema for validation (JSON Schema format)
    input_schema: Dict[str, Any] = {
        "required": [],
        "optional": [],
    }

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs) -> SkillResult:
        """
        Execute the skill with the given context and input.

        Args:
            context: AgentContext with user and request information
            **kwargs: Skill-specific input parameters

        Returns:
            SkillResult with generated content

        Raises:
            ValueError: If required input is missing or invalid
            Exception: If skill execution fails
        """
        pass

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters against the skill's schema.

        Args:
            **kwargs: Input parameters to validate

        Raises:
            ValueError: If required parameters are missing
        """
        for required_field in self.input_schema.get("required", []):
            if required_field not in kwargs or kwargs[required_field] is None:
                raise ValueError(f"Missing required field: {required_field}")

    def get_info(self) -> Dict[str, Any]:
        """Get skill metadata for API responses."""
        return {
            "id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "input_schema": self.input_schema,
        }
