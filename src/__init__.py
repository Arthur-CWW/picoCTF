"""
CTF Environment Package

Core environment and dataset functionality for CTF challenges.
Focused on dataset management and interactive testing.
"""

from .ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel, CategoryType, DatasetStats
from .ctf_cli import CTFSession, main as cli_main
from .ctf_models import (
    CTFChallenge as CTFChallengeModel,
    CategoryType as CategoryTypeModel,
    DifficultyLevel as DifficultyLevelModel,
    ProblemMetadata,
    DatasetStats as DatasetStatsModel,
    EnvironmentConfig,
    SessionState
)
from .challenge_loader import ChallengeLoader, load_challenges_dynamically
from .ctf_cli_improved import main as improved_cli_main

__version__ = "0.1.0"
__all__ = [
    "CTFDataset",
    "CTFChallenge",
    "DifficultyLevel",
    "CategoryType",
    "DatasetStats",
    "CTFSession",
    "cli_main",
    # New pydantic models
    "CTFChallengeModel",
    "CategoryTypeModel",
    "DifficultyLevelModel",
    "ProblemMetadata",
    "DatasetStatsModel",
    "EnvironmentConfig",
    "SessionState",
    # Challenge loading
    "ChallengeLoader",
    "load_challenges_dynamically",
    # Improved CLI
    "improved_cli_main",
]