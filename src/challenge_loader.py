#!/usr/bin/env python3
"""
Dynamic challenge loader for CTF environments.

Supports loading challenges from multiple sources:
- picoCTF problems directory
- JSON dataset files
- Individual challenge directories
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
import logging

from .ctf_models import (
    CTFChallenge,
    CategoryType,
    DifficultyLevel,
    ProblemMetadata
)

logger = logging.getLogger(__name__)


class ChallengeLoader:
    """Dynamic challenge loader with multiple source support."""

    def __init__(self, base_path: Path = Path(".")):
        """Initialize the challenge loader."""
        self.base_path = Path(base_path)
        self._flag_cache: Dict[str, str] = {}

    def discover_challenge_sources(self) -> Dict[str, List[Path]]:
        """Discover all available challenge sources."""
        sources = {
            "picoctf_problems": [],
            "json_datasets": [],
            "individual_challenges": []
        }

        # Look for picoCTF problems directory
        problems_dir = self.base_path / "problems"
        if problems_dir.exists():
            sources["picoctf_problems"] = list(self._find_picoctf_challenges(problems_dir))

        # Look for JSON dataset files
        for json_file in self.base_path.rglob("*.json"):
            if json_file.name in ["challenges.json", "dataset.json", "ctf_dataset.json"]:
                sources["json_datasets"].append(json_file)

        # Look for individual challenge directories
        for challenge_dir in self.base_path.rglob("challenge.json"):
            sources["individual_challenges"].append(challenge_dir.parent)

        return sources

    def _find_picoctf_challenges(self, problems_dir: Path) -> Generator[Path, None, None]:
        """Find all picoCTF challenge directories."""
        for problem_json in problems_dir.rglob("problem.json"):
            yield problem_json.parent

    def load_challenges_from_sources(
        self,
        sources: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[CTFChallenge]:
        """Load challenges from specified sources with filtering."""
        all_sources = self.discover_challenge_sources()

        if sources is None:
            # Default to all available sources
            sources = list(all_sources.keys())

        challenges = []

        for source_type in sources:
            if source_type not in all_sources:
                logger.warning(f"Unknown source type: {source_type}")
                continue

            for source_path in all_sources[source_type]:
                try:
                    if source_type == "picoctf_problems":
                        challenge = self._load_picoctf_challenge(source_path)
                    elif source_type == "json_datasets":
                        challenges.extend(self._load_json_dataset(source_path))
                        continue
                    elif source_type == "individual_challenges":
                        challenge = self._load_individual_challenge(source_path)
                    else:
                        continue

                    if challenge and self._should_include_challenge(
                        challenge, include_patterns, exclude_patterns
                    ):
                        challenges.append(challenge)

                except Exception as e:
                    logger.error(f"Error loading challenge from {source_path}: {e}")

        return challenges

    def _should_include_challenge(
        self,
        challenge: CTFChallenge,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]]
    ) -> bool:
        """Check if challenge should be included based on patterns."""
        challenge_text = f"{challenge.id} {challenge.name} {challenge.category} {challenge.difficulty}"

        # Check exclude patterns first
        if exclude_patterns:
            for pattern in exclude_patterns:
                if re.search(pattern, challenge_text, re.IGNORECASE):
                    return False

        # Check include patterns
        if include_patterns:
            for pattern in include_patterns:
                if re.search(pattern, challenge_text, re.IGNORECASE):
                    return True
            return False  # If include patterns specified but none match

        return True

    def _load_picoctf_challenge(self, challenge_dir: Path) -> Optional[CTFChallenge]:
        """Load a challenge from a picoCTF problem directory."""
        problem_json = challenge_dir / "problem.json"
        if not problem_json.exists():
            return None

        try:
            with open(problem_json, 'r', encoding='utf-8') as f:
                problem_data = json.load(f)

            metadata = ProblemMetadata(**problem_data)

            # Generate challenge ID from directory path
            challenge_id = self._generate_challenge_id(challenge_dir)

            # Determine difficulty from score
            difficulty = self._score_to_difficulty(metadata.score)

            # Normalize category
            category = CategoryType.normalize_category(metadata.category)

            # Find or generate flag
            flag = self._find_flag(challenge_dir, challenge_id)

            # Find associated files
            files = self._find_challenge_files(challenge_dir)

            # Create environment config if needed
            environment = self._create_environment_config(metadata, challenge_dir)

            return CTFChallenge(
                id=challenge_id,
                name=metadata.name,
                category=category,
                difficulty=difficulty,
                description=metadata.description,
                flag=flag,
                hints=metadata.hints,
                points=metadata.score,
                files=files,
                environment=environment,
                source_path=challenge_dir,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error loading picoCTF challenge from {challenge_dir}: {e}")
            return None

    def _load_json_dataset(self, json_file: Path) -> List[CTFChallenge]:
        """Load challenges from a JSON dataset file."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            challenges = []
            challenges_data = data.get("challenges", [])

            for challenge_data in challenges_data:
                try:
                    # Convert old format to new if needed
                    if "difficulty" in challenge_data:
                        challenge_data["difficulty"] = DifficultyLevel(challenge_data["difficulty"])
                    if "category" in challenge_data:
                        challenge_data["category"] = CategoryType.normalize_category(challenge_data["category"])

                    challenge = CTFChallenge(**challenge_data)
                    challenges.append(challenge)
                except Exception as e:
                    logger.error(f"Error loading challenge from {json_file}: {e}")

            return challenges

        except Exception as e:
            logger.error(f"Error loading JSON dataset from {json_file}: {e}")
            return []

    def _load_individual_challenge(self, challenge_dir: Path) -> Optional[CTFChallenge]:
        """Load a challenge from an individual challenge directory."""
        challenge_json = challenge_dir / "challenge.json"
        if not challenge_json.exists():
            return None

        try:
            with open(challenge_json, 'r', encoding='utf-8') as f:
                challenge_data = json.load(f)

            # Add source path
            challenge_data["source_path"] = challenge_dir

            return CTFChallenge(**challenge_data)

        except Exception as e:
            logger.error(f"Error loading individual challenge from {challenge_dir}: {e}")
            return None

    def _generate_challenge_id(self, challenge_dir: Path) -> str:
        """Generate a unique challenge ID from directory path."""
        # Use relative path from problems directory
        problems_dir = self.base_path / "problems"
        try:
            rel_path = challenge_dir.relative_to(problems_dir)
            # Replace path separators with underscores
            challenge_id = str(rel_path).replace("/", "_").replace("\\", "_")
            # Remove any problematic characters
            challenge_id = re.sub(r'[^a-zA-Z0-9_-]', '_', challenge_id)
            return challenge_id
        except ValueError:
            # Fallback to directory name
            return challenge_dir.name

    def _score_to_difficulty(self, score: int) -> DifficultyLevel:
        """Convert score to difficulty level."""
        if score <= 50:
            return DifficultyLevel.EASY
        elif score <= 150:
            return DifficultyLevel.MEDIUM
        else:
            return DifficultyLevel.HARD

    def _find_flag(self, challenge_dir: Path, challenge_id: str) -> str:
        """Find or generate the flag for a challenge."""
        # Check cache first
        if challenge_id in self._flag_cache:
            return self._flag_cache[challenge_id]

        # Look for flag file
        flag_file = challenge_dir / "flag"
        if flag_file.exists():
            try:
                flag_content = flag_file.read_text(encoding='utf-8').strip()
                if flag_content and not flag_content.startswith("{{"):
                    self._flag_cache[challenge_id] = flag_content
                    return flag_content
            except Exception:
                pass

        # Look for flag in other files
        for file_path in challenge_dir.rglob("*.txt"):
            try:
                content = file_path.read_text(encoding='utf-8')
                flag_match = re.search(r'picoCTF\{[^}]+\}', content)
                if flag_match:
                    flag = flag_match.group(0)
                    self._flag_cache[challenge_id] = flag
                    return flag
            except Exception:
                continue

        # Generate a default flag
        default_flag = f"picoCTF{{{challenge_id}_placeholder}}"
        self._flag_cache[challenge_id] = default_flag
        return default_flag

    def _find_challenge_files(self, challenge_dir: Path) -> List[str]:
        """Find associated files for a challenge."""
        files = []

        # Skip common metadata files
        skip_files = {"problem.json", "flag", "challenge.json", ".gitignore", "README.md"}

        for file_path in challenge_dir.rglob("*"):
            if file_path.is_file() and file_path.name not in skip_files:
                # Get relative path from challenge directory
                rel_path = file_path.relative_to(challenge_dir)
                files.append(str(rel_path))

        return files

    def _create_environment_config(
        self,
        metadata: ProblemMetadata,
        challenge_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """Create environment configuration from challenge metadata."""
        env_config = {}

        if metadata.pip_requirements:
            env_config["pip_requirements"] = metadata.pip_requirements

        if metadata.pip_python_version:
            env_config["python_version"] = metadata.pip_python_version

        if metadata.pkg_dependencies:
            env_config["package_dependencies"] = metadata.pkg_dependencies

        # Check for Docker files
        dockerfile = challenge_dir / "Dockerfile"
        if dockerfile.exists():
            env_config["dockerfile"] = str(dockerfile)

        docker_compose = challenge_dir / "docker-compose.yml"
        if docker_compose.exists():
            env_config["docker_compose"] = str(docker_compose)

        return env_config if env_config else None


def load_challenges_dynamically(
    base_path: Path = Path("."),
    sources: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> List[CTFChallenge]:
    """Convenience function to load challenges dynamically."""
    loader = ChallengeLoader(base_path)
    return loader.load_challenges_from_sources(sources, include_patterns, exclude_patterns)