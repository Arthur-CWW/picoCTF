import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from typing_extensions import Literal
except ImportError:
    from typing import Literal  # Python 3.8+

import tyro
from tyro.extras import SubcommandApp


class DifficultyLevel(Enum):
    """Enumeration for challenge difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


CategoryType = Literal["general", "crypto", "forensics", "web", "binary", "reverse"]


@dataclass(frozen=True)
class CTFChallenge:
    """Immutable CTF challenge representation."""
    id: str
    name: str
    category: CategoryType
    difficulty: DifficultyLevel
    description: str
    flag: str
    hints: List[str]
    points: int
    files: List[str] = field(default_factory=list)
    environment: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate challenge data after initialization."""
        if not self.id or not self.name or not self.flag:
            raise ValueError("Challenge must have id, name, and flag")
        if not self.flag.startswith("picoCTF{") or not self.flag.endswith("}"):
            raise ValueError("Flag must be in format picoCTF{...}")
        if self.points <= 0:
            raise ValueError("Points must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert challenge to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "description": self.description,
            "flag": self.flag,
            "hints": self.hints,
            "points": self.points,
            "files": self.files,
            "environment": self.environment,
        }


@dataclass
class DatasetStats:
    """Statistics about the CTF dataset."""
    total_challenges: int
    categories: Dict[CategoryType, int]
    difficulties: Dict[str, int]
    total_points: int
    avg_points_per_challenge: float


class CTFDataset:
    """Dataset manager for CTF challenges."""

    def __init__(self, data_dir: Union[str, Path] = Path("env/dataset")) -> None:
        """Initialize dataset manager."""
        self.data_dir: Path = Path(data_dir)
        self.challenges: List[CTFChallenge] = []
        self.categories: Set[CategoryType] = set()
        self._challenge_index: Dict[str, CTFChallenge] = {}
        self.load_dataset()

    def load_dataset(self) -> None:
        """Load challenges from dataset directory."""
        dataset_file = self.data_dir / "challenges.json"

        if dataset_file.exists():
            self._load_from_file(dataset_file)
        else:
            print(f"Dataset file {dataset_file} not found, creating sample dataset...")
            self._create_sample_dataset()

    def _load_from_file(self, dataset_file: Path) -> None:
        """Load challenges from JSON file."""
        try:
            with open(dataset_file, encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)

            challenges_data: List[Dict[str, Any]] = data.get("challenges", [])

            for challenge_data in challenges_data:
                challenge = self._create_challenge_from_dict(challenge_data)
                self._add_challenge(challenge)

            print(f"Loaded {len(self.challenges)} challenges from {dataset_file}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading dataset: {e}")
            self._create_sample_dataset()

    def _create_challenge_from_dict(self, data: Dict[str, Any]) -> CTFChallenge:
        """Create a CTFChallenge from dictionary data."""
        return CTFChallenge(
            id=data["id"],
            name=data["name"],
            category=data["category"],  # type: ignore
            difficulty=DifficultyLevel(data.get("difficulty", "medium")),
            description=data["description"],
            flag=data["flag"],
            hints=data.get("hints", []),
            points=data.get("points", 100),
            files=data.get("files", []),
            environment=data.get("environment"),
        )

    def _add_challenge(self, challenge: CTFChallenge) -> None:
        """Add a challenge to the dataset and update indexes."""
        if challenge.id in self._challenge_index:
            raise ValueError(f"Challenge with ID {challenge.id} already exists")

        self.challenges.append(challenge)
        self.categories.add(challenge.category)
        self._challenge_index[challenge.id] = challenge

    def _create_sample_dataset(self) -> None:
        """Create a sample dataset for testing."""
        sample_challenges_data: List[Dict[str, Any]] = [
            {
                "id": "basic_flag_001",
                "name": "Find the Flag",
                "category": "general",
                "difficulty": "easy",
                "description": "The flag is right here: picoCTF{welcome_to_ctf}",
                "flag": "picoCTF{welcome_to_ctf}",
                "hints": ["Look in the description"],
                "points": 50,
            },
            {
                "id": "caesar_001",
                "name": "Caesar Cipher",
                "category": "crypto",
                "difficulty": "easy",
                "description": "Decrypt this: fvpbPGS{jryq_gneq_qrp_fgheq}",
                "flag": "picoCTF{weld_targ_dec_sturd}",
                "hints": ["Try ROT13", "Caesar cipher with shift 13"],
                "points": 100,
            },
            {
                "id": "base64_001",
                "name": "Base64 Decode",
                "category": "general",
                "difficulty": "easy",
                "description": "Decode: cGljb0NURntlbmNvZGluZ19pc19ub3RfZW5jcnlwdGlvbn0=",
                "flag": "picoCTF{encoding_is_not_encryption}",
                "hints": ["This looks like base64", "Use a decoder"],
                "points": 75,
            },
            {
                "id": "xor_001",
                "name": "Single Byte XOR",
                "category": "crypto",
                "difficulty": "medium",
                "description": "Find the key and decrypt: 73626960647f6b206821204f21254f7d694f7624662065622127234f726927756d",
                "flag": "picoCTF{sgl_byt_xor_is_weak}",
                "hints": ["Try XORing with single bytes", "Look for readable text"],
                "points": 150,
            },
            {
                "id": "hidden_001",
                "name": "Hidden Data",
                "category": "forensics",
                "difficulty": "easy",
                "description": "There's something hidden in this text file.",
                "flag": "picoCTF{hidden_in_plain_sight}",
                "hints": ["Check the end of files", "Look for unusual spacing"],
                "points": 100,
                "files": ["data.txt"],
            },
        ]

        # Create dataset directory and files
        self.data_dir.mkdir(parents=True, exist_ok=True)

        dataset = {"challenges": sample_challenges_data}
        with open(self.data_dir / "challenges.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        # Create sample files
        self._create_sample_files()

        # Load the challenges we just created
        self.load_dataset()

    def _create_sample_files(self) -> None:
        """Create sample challenge files."""
        files_dir = self.data_dir / "files"
        files_dir.mkdir(exist_ok=True)

        sample_file_content = """This is a normal looking file.
Nothing suspicious here.
Just some regular content for analysis.

Some more text to make it look legitimate.
Adding more lines...

End of file.
picoCTF{hidden_in_plain_sight}"""

        with open(files_dir / "data.txt", "w", encoding="utf-8") as f:
            f.write(sample_file_content)

    def get_challenge_by_id(self, challenge_id: str) -> Optional[CTFChallenge]:
        """Get a specific challenge by ID."""
        return self._challenge_index.get(challenge_id)

    def get_challenges_by_category(self, category: CategoryType) -> List[CTFChallenge]:
        """Get challenges filtered by category."""
        return [c for c in self.challenges if c.category == category]

    def get_challenges_by_difficulty(self, difficulty: DifficultyLevel) -> List[CTFChallenge]:
        """Get challenges filtered by difficulty."""
        return [c for c in self.challenges if c.difficulty == difficulty]

    def get_random_challenge(
        self,
        category: Optional[CategoryType] = None,
        difficulty: Optional[DifficultyLevel] = None,
    ) -> CTFChallenge:
        """Get a random challenge with optional filters."""
        candidates = self.challenges

        if category:
            candidates = [c for c in candidates if c.category == category]
        if difficulty:
            candidates = [c for c in candidates if c.difficulty == difficulty]

        if not candidates:
            raise ValueError("No challenges match the specified criteria")

        return random.choice(candidates)

    def get_dataset_stats(self) -> DatasetStats:
        """Get comprehensive statistics about the dataset."""
        category_counts: Dict[CategoryType, int] = {}
        difficulty_counts: Dict[str, int] = {}

        for challenge in self.challenges:
            category_counts[challenge.category] = category_counts.get(challenge.category, 0) + 1
            difficulty_value = challenge.difficulty.value
            difficulty_counts[difficulty_value] = difficulty_counts.get(difficulty_value, 0) + 1

        total_points = sum(c.points for c in self.challenges)
        avg_points = total_points / len(self.challenges) if self.challenges else 0

        return DatasetStats(
            total_challenges=len(self.challenges),
            categories=category_counts,
            difficulties=difficulty_counts,
            total_points=total_points,
            avg_points_per_challenge=avg_points,
        )

    def export_dataset(self, output_file: Union[str, Path]) -> None:
        """Export the full dataset to a file."""
        output_path = Path(output_file)
        dataset_data = {
            "challenges": [challenge.to_dict() for challenge in self.challenges],
            "stats": self.get_dataset_stats().__dict__,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset_data, f, indent=2, ensure_ascii=False)

        print(f"Exported dataset to {output_path}")


def convert_picoctf_to_dataset(source_dir: Union[str, Path], target_dir: Union[str, Path]) -> None:
    """Convert original picoCTF problems to our dataset format."""
    import re

    source_path = Path(source_dir)
    target_path = Path(target_dir)

    if not source_path.exists():
        raise FileNotFoundError(f"Source directory {source_path} does not exist")

    challenges: List[Dict[str, Any]] = []
    challenge_id = 1

    category_map: Dict[str, CategoryType] = {
        "Cryptography": "crypto",
        "General Skills": "general",
        "Forensics": "forensics",
        "Web Exploitation": "web",
        "Binary Exploitation": "binary",
        "Reverse Engineering": "reverse",
    }

    for problem_json in source_path.rglob("problem.json"):
        try:
            challenge_dir = problem_json.parent
            with open(problem_json, encoding="utf-8") as f:
                problem_data: Dict[str, Any] = json.load(f)

            # Extract flag
            flag = _extract_flag_from_challenge(challenge_dir, problem_data)
            if not flag:
                continue  # Skip if no flag found

            category = category_map.get(problem_data.get("category", ""), "general")

            # Determine difficulty based on score
            score: int = problem_data.get("score", 100)
            difficulty = _determine_difficulty(score)

            challenge = {
                "id": f"{category}_{challenge_id:03d}",
                "name": problem_data.get("name", challenge_dir.name),
                "category": category,
                "difficulty": difficulty,
                "description": _clean_description(problem_data.get("description", "")),
                "flag": flag,
                "hints": problem_data.get("hints", []),
                "points": score,
            }

            challenges.append(challenge)
            challenge_id += 1

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error converting {challenge_dir.name}: {e}")

    # Save dataset
    target_path.mkdir(parents=True, exist_ok=True)
    dataset = {"challenges": challenges}

    with open(target_path / "challenges.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"Converted {len(challenges)} challenges to {target_path}")


def _extract_flag_from_challenge(challenge_dir: Path, problem_data: Dict[str, Any]) -> Optional[str]:
    """Extract flag from challenge directory and metadata."""
    import re

    # Check flag file
    flag_file = challenge_dir / "flag"
    if flag_file.exists():
        try:
            flag = flag_file.read_text(encoding="utf-8").strip()
            if flag.startswith("picoCTF{"):
                return flag
        except (OSError, UnicodeDecodeError):
            pass

    # Look for flag in description
    description = problem_data.get("description", "")
    flag_match = re.search(r"picoCTF\{[^}]+\}", description)
    if flag_match:
        return flag_match.group(0)

    return None


def _determine_difficulty(score: int) -> str:
    """Determine difficulty level based on score."""
    if score <= 100:
        return "easy"
    elif score <= 300:
        return "medium"
    else:
        return "hard"


def _clean_description(description: str) -> str:
    """Clean and simplify challenge description."""
    import re

    # Remove template variables like {{server}}, {{port}}
    description = re.sub(r"\{\{[^}]+\}\}", "[PLACEHOLDER]", description)
    # Remove HTML tags
    description = re.sub(r"<[^>]+>", "", description)
    # Clean up whitespace
    description = re.sub(r"\s+", " ", description).strip()
    return description


# Create the tyro SubcommandApp
# app = ()
app = SubcommandApp()


@app.command(name="convert")
def convert_cmd(
    source_dir: Path,
    target_dir: Path = Path("env/dataset")
) -> None:
    """Convert original picoCTF problems to dataset format."""
    convert_picoctf_to_dataset(source_dir, target_dir)

@app.command(name="stats")
def stats_cmd(
    data_dir: Path = Path("env/dataset")
) -> None:
    """Show dataset statistics."""
    dataset = CTFDataset(data_dir)
    stats = dataset.get_dataset_stats()
    print("Dataset Stats:")
    print(f"  Total challenges: {stats.total_challenges}")
    print(f"  Categories: {dict(stats.categories)}")
    print(f"  Difficulties: {stats.difficulties}")
    print(f"  Total points: {stats.total_points}")
    print(f"  Average points: {stats.avg_points_per_challenge:.1f}")

@app.command(name="export")
def export_cmd(
    output_file: Path = Path("ctf_dataset_export.json"),
    data_dir: Path = Path("env/dataset")
) -> None:
    """Export dataset to a JSON file."""
    dataset = CTFDataset(data_dir)
    dataset.export_dataset(output_file)

@app.command(name='ls' )
def ls(
    data_dir: Path = Path("env/dataset"),
    category: Optional[CategoryType] = None,
    difficulty: Optional[str] = None,
    verbose: bool = False
) -> None:
    """List challenges with optional filtering."""
    dataset = CTFDataset(data_dir)

    challenges = dataset.challenges

    # Apply filters
    if category:
        challenges = [c for c in challenges if c.category == category]

    if difficulty:
        try:
            diff_level = DifficultyLevel(difficulty)
            challenges = [c for c in challenges if c.difficulty == diff_level]
        except ValueError:
            print(f"Invalid difficulty: {difficulty}. Valid options: easy, medium, hard")
            return

    if not challenges:
        print("No challenges found matching the criteria.")
        return

    print(f"Found {len(challenges)} challenge(s):")
    print("=" * 80)

    for challenge in challenges:
        print(f"ID: {challenge.id}")
        print(f"Name: {challenge.name}")
        print(f"Category: {challenge.category}")
        print(f"Difficulty: {challenge.difficulty.value}")
        print(f"Points: {challenge.points}")

        if verbose:
            print(f"Description: {challenge.description}")
            if challenge.hints:
                print(f"Hints: {', '.join(challenge.hints)}")
            if challenge.files:
                print(f"Files: {', '.join(challenge.files)}")
            print(f"Flag: {challenge.flag}")

        print("-" * 40)

if __name__ == "__main__":
    app.cli(description="""
CTF Dataset Manager

Core dataset functionality for managing CTF challenges and environments.
Focused on dataset operations and environment management, not RL training.
"""
)

