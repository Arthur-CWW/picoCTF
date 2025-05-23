"""
CTF Environment Package

Core environment and dataset functionality for CTF challenges.
Focused on dataset management and interactive testing.
"""

from .ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel, CategoryType, DatasetStats
from .ctf_cli import CTFSession, main as cli_main

__version__ = "0.1.0"
__all__ = [
    "CTFDataset",
    "CTFChallenge",
    "DifficultyLevel",
    "CategoryType",
    "DatasetStats",
    "CTFSession",
    "cli_main",
]