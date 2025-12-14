"""
Explain Skill - Code Explanation

Analyzes code and generates plain-language explanations
tailored to the reader's context.
"""

from typing import Optional
from .base import BaseSkill, AgentContext, SkillResult, Suggestion
from services.gemini_service import get_gemini_service


class ExplainSkill(BaseSkill):
    """
    Explains code in plain language.

    Takes selected code and generates a clear, educational explanation
    suitable for readers learning physical AI and robotics concepts.
    """

    skill_id = "explain"
    name = "Code Explanation"
    description = "Analyzes code and generates plain-language explanations"
    version = "1.0.0"
    enabled = True

    input_schema = {
        "required": ["selected_text"],
        "optional": ["chapter_id"],
    }

    # Maximum input length (approximately 5000 words)
    MAX_INPUT_LENGTH = 25000

    async def execute(self, context: AgentContext, **kwargs) -> SkillResult:
        """
        Generate a plain-language explanation of the selected code.

        Args:
            context: AgentContext with user and request information
            selected_text: The code to explain
            chapter_id: Optional chapter context

        Returns:
            SkillResult with explanation content
        """
        selected_text = kwargs.get('selected_text', '')
        chapter_id = kwargs.get('chapter_id')

        # Validate input
        self.validate_input(**kwargs)

        if len(selected_text) > self.MAX_INPUT_LENGTH:
            raise ValueError(
                f"Selected text exceeds maximum length of {self.MAX_INPUT_LENGTH} characters. "
                "Please select a smaller code section."
            )

        # Get expertise level from user profile if available
        expertise_level = "intermediate"
        if context.user_profile:
            expertise_level = context.user_profile.get('expertise_level', 'intermediate')

        # Build the prompt
        prompt = self._build_prompt(selected_text, chapter_id, expertise_level)

        # Call Gemini
        gemini = get_gemini_service()
        response_text, latency_ms = gemini.generate_answer(
            query=prompt,
            context_chunks=[],  # Direct generation, no RAG context needed
            selected_text=None,
        )

        # Build suggestions for follow-up actions
        suggestions = self._build_suggestions(selected_text)

        return SkillResult(
            content=response_text,
            citations=[],
            suggestions=suggestions,
        )

    def _build_prompt(
        self,
        code: str,
        chapter_id: Optional[str],
        expertise_level: str,
    ) -> str:
        """Build the prompt for code explanation."""

        # Adjust explanation depth based on expertise
        depth_guidance = {
            "beginner": "Explain concepts thoroughly, avoiding jargon. Define any technical terms used.",
            "intermediate": "Balance detail with conciseness. Technical terms can be used with brief context.",
            "expert": "Be concise and focus on advanced concepts. Assume familiarity with programming basics.",
        }

        guidance = depth_guidance.get(expertise_level, depth_guidance["intermediate"])

        chapter_context = ""
        if chapter_id:
            chapter_context = f"\n\nThis code is from the chapter: {chapter_id}"

        return f"""You are an expert educator for a Physical AI & Humanoid Robotics textbook.

Analyze the following code and provide a clear, educational explanation.

{guidance}

Code to explain:
```
{code}
```
{chapter_context}

Provide your explanation in the following structure:
1. **Overview**: What does this code do? (1-2 sentences)
2. **Key Concepts**: Explain the main programming concepts or algorithms used
3. **Step-by-Step Breakdown**: Walk through the logic
4. **Connection to Robotics/AI**: How does this relate to physical AI concepts (if applicable)?

Keep the explanation focused and educational. Use markdown formatting for clarity."""

    def _build_suggestions(self, code: str) -> list[Suggestion]:
        """Generate follow-up suggestions based on the code."""
        suggestions = []

        # Always suggest translation for accessibility
        suggestions.append(Suggestion(
            type="skill",
            skill_id="translate",
            label="Translate to Urdu",
            description="Read this explanation in Urdu",
        ))

        # If code looks like it might have errors, suggest debug
        error_indicators = ['error', 'exception', 'try', 'except', 'catch', 'raise']
        if any(indicator in code.lower() for indicator in error_indicators):
            suggestions.append(Suggestion(
                type="skill",
                skill_id="debug",
                label="Debug this code",
                description="Get help troubleshooting potential issues",
            ))

        return suggestions
