"""Centralized model definitions for HeliosCommand agents."""

from typing import Final


class LLMModels:
    """Model name constants used across all agents."""

    GEMINI_2_5_FLASH: Final[str] = "gemini-2.5-flash"
    GEMINI_2_5_PRO: Final[str] = "gemini-2.5-pro"
    GEMINI_2_0_FLASH: Final[str] = "gemini-2.0-flash"

    DEFAULT: Final[str] = GEMINI_2_5_FLASH
