#!/usr/bin/env python3
"""
Pydantic models for CTF challenges and environments.

Provides type-safe data models with validation for CTF challenges.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.types import PositiveInt


class DifficultyLevel(str, Enum):
    """Enumeration for challenge difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CategoryType(str, Enum):
    """Enumeration for challenge categories."""
    GENERAL = "general"
    CRYPTO = "crypto"
    CRYPTOGRAPHY = "cryptography"  # picoCTF uses this
    FORENSICS = "forensics"
    WEB = "web"
    WEB_EXPLOITATION = "web-exploitation"  # picoCTF uses this
    BINARY = "binary"
    BINARY_EXPLOITATION = "binary-exploitation"  # picoCTF uses this
    REVERSE = "reverse"
    REVERSE_ENGINEERING = "reverse-engineering"  # picoCTF uses this
    PWNING = "pwning"
    MISCELLANEOUS = "miscellaneous"

    @classmethod
    def normalize_category(cls, category: str) -> "CategoryType":
        """Normalize category names from different sources."""
        category_lower = category.lower().replace(" ", "-")

        # Mapping for different category naming conventions
        mapping = {
            "cryptography": cls.CRYPTO,
            "web-exploitation": cls.WEB,
            "web exploitation": cls.WEB,
            "binary-exploitation": cls.BINARY,
            "binary exploitation": cls.BINARY,
            "reverse-engineering": cls.REVERSE,
            "reverse engineering": cls.REVERSE,
            "miscellaneous": cls.GENERAL,
            "misc": cls.GENERAL,
        }

        if category_lower in mapping:
            return mapping[category_lower]

        # Try direct match
        try:
            return cls(category_lower)
        except ValueError:
            # Default fallback
            return cls.GENERAL


class ProblemMetadata(BaseModel):
    """Model for problem.json metadata from picoCTF challenges."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields

    name: str
    category: str
    description: str
    score: PositiveInt = Field(default=100, description="Challenge points")
    hints: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    organization: Optional[str] = None
    event: Optional[str] = None
    walkthrough: Optional[str] = None
    pkg_dependencies: List[str] = Field(default_factory=list)
    pip_requirements: List[str] = Field(default_factory=list)
    pip_python_version: Optional[str] = None


class CTFChallenge(BaseModel):
    """Type-safe CTF challenge model with validation."""
    model_config = ConfigDict(frozen=True)  # Immutable

    id: str = Field(..., description="Unique challenge identifier")
    name: str = Field(..., description="Human-readable challenge name")
    category: CategoryType = Field(..., description="Challenge category")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM)
    description: str = Field(..., description="Challenge description")
    flag: str = Field(..., description="The correct flag")
    hints: List[str] = Field(default_factory=list, description="Challenge hints")
    points: PositiveInt = Field(default=100, description="Points for solving")
    files: List[str] = Field(default_factory=list, description="Associated files")
    environment: Optional[Dict[str, Any]] = Field(default=None, description="Environment config")
    source_path: Optional[Path] = Field(default=None, description="Source directory path")
    metadata: Optional[ProblemMetadata] = Field(default=None, description="Original problem metadata")

    @field_validator('flag')
    @classmethod
    def validate_flag(cls, v: str) -> str:
        """Validate flag format."""
        if not v.startswith("picoCTF{") or not v.endswith("}"):
            raise ValueError("Flag must be in format picoCTF{...}")
        return v

    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate challenge ID."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Challenge ID must be non-empty and alphanumeric with underscores/hyphens")
        return v


class DatasetStats(BaseModel):
    """Statistics about the CTF dataset."""
    total_challenges: int = Field(ge=0)
    categories: Dict[CategoryType, int] = Field(default_factory=dict)
    difficulties: Dict[DifficultyLevel, int] = Field(default_factory=dict)
    total_points: int = Field(ge=0)
    avg_points_per_challenge: float = Field(ge=0.0)
    source_directories: List[str] = Field(default_factory=list)


class EnvironmentConfig(BaseModel):
    """Configuration for challenge environments."""
    model_config = ConfigDict(extra="allow")

    type: str = Field(default="docker", description="Environment type")
    image: Optional[str] = Field(default=None, description="Docker image")
    ports: List[int] = Field(default_factory=list, description="Exposed ports")
    volumes: Dict[str, str] = Field(default_factory=dict, description="Volume mounts")
    environment_vars: Dict[str, str] = Field(default_factory=dict, alias="env")
    working_dir: Optional[str] = Field(default=None)
    command: Optional[List[str]] = Field(default=None)


class SessionState(BaseModel):
    """State of the current CTF session."""
    current_challenge_id: Optional[str] = None
    attempts: Dict[str, List[str]] = Field(default_factory=dict)  # challenge_id -> attempts
    solved_challenges: Set[str] = Field(default_factory=set)
    score: int = Field(default=0, ge=0)
    start_time: Optional[float] = None
    session_stats: Dict[str, Any] = Field(default_factory=dict)