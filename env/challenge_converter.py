#!/usr/bin/env python3
"""
Challenge Converter for picoCTF RL Environment

This tool converts original picoCTF challenges into the simplified format
needed for the RL environment.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import re
import sys

from picoctf_rl_env import CategoryType


class ChallengeConverter:
    """Converts original picoCTF challenges to RL environment format."""

    def __init__(self, source_dir: Path, target_dir: Path):
        """
        Initialize converter.

        Args:
            source_dir: Original picoCTF problems directory
            target_dir: Target directory for RL challenges
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def convert_all(self) -> None:
        """Convert all challenges from source to target directory."""
        converted_count = 0

        for problem_json in self.source_dir.rglob("problem.json"):
            try:
                challenge_dir = problem_json.parent
                print(f"Converting {challenge_dir.name}...")

                if self.convert_challenge(challenge_dir):
                    converted_count += 1

            except Exception as e:
                print(f"Error converting {challenge_dir.name}: {e}")
                continue

        print(f"\nConverted {converted_count} challenges successfully!")

    def convert_challenge(self, challenge_dir: Path) -> bool:
        """
        Convert a single challenge.

        Args:
            challenge_dir: Directory containing the challenge

        Returns:
            True if conversion successful
        """
        problem_json = challenge_dir / "problem.json"
        if not problem_json.exists():
            return False

        # Load original problem metadata
        with open(problem_json) as f:
            problem_data = json.load(f)

        # Extract flag
        flag = self._extract_flag(challenge_dir, problem_data)
        if not flag:
            print(f"  Warning: Could not extract flag for {challenge_dir.name}")
            return False

        # Map category
        category = self._map_category(challenge_dir)

        # Create converted challenge
        converted_challenge = {
            "name": problem_data.get("name", challenge_dir.name),
            "description": self._clean_description(problem_data.get("description", "")),
            "category": category,
            "flag": flag,
            "hints": problem_data.get("hints", []),
            "score": problem_data.get("score", 100),
            "author": problem_data.get("author", "Unknown"),
            "files": self._get_relevant_files(challenge_dir)
        }

        # Create target directory
        target_challenge_dir = self.target_dir / challenge_dir.name
        target_challenge_dir.mkdir(exist_ok=True)

        # Save converted challenge
        with open(target_challenge_dir / "challenge.json", "w") as f:
            json.dump(converted_challenge, f, indent=2)

        # Copy relevant files
        self._copy_challenge_files(challenge_dir, target_challenge_dir)

        print(f"  ✓ Converted: {converted_challenge['name']} ({category})")
        return True

    def _extract_flag(self, challenge_dir: Path, problem_data: Dict) -> Optional[str]:
        """Extract the flag from various sources."""
        # Check if static flag is defined
        if problem_data.get("static_flag"):
            flag_file = challenge_dir / "flag"
            if flag_file.exists():
                return flag_file.read_text().strip()

        # Look for flag in files
        for flag_file in ["flag", "flag.txt", "solution.txt"]:
            flag_path = challenge_dir / flag_file
            if flag_path.exists():
                content = flag_path.read_text().strip()
                # Look for picoCTF{...} pattern
                flag_match = re.search(r'picoCTF\{[^}]+\}', content)
                if flag_match:
                    return flag_match.group(0)

        # Check challenge.py for flag generation
        challenge_py = challenge_dir / "challenge.py"
        if challenge_py.exists():
            content = challenge_py.read_text()
            # Look for hardcoded flags
            flag_match = re.search(r'picoCTF\{[^}]+\}', content)
            if flag_match:
                return flag_match.group(0)

        # Try to extract from description or other sources
        description = problem_data.get("description", "")
        flag_match = re.search(r'picoCTF\{[^}]+\}', description)
        if flag_match:
            return flag_match.group(0)

        return None

    def _map_category(self, challenge_dir: Path) -> str:
        """Map challenge directory structure to category."""
        path_parts = challenge_dir.parts

        # Look for category in path
        category_mappings = {
            "cryptography": "cryptography",
            "crypto": "cryptography",
            "web": "web-exploitation",
            "web-exploitation": "web-exploitation",
            "binary": "binary-exploitation",
            "binary-exploitation": "binary-exploitation",
            "pwn": "binary-exploitation",
            "reverse": "reverse-engineering",
            "reverse-engineering": "reverse-engineering",
            "rev": "reverse-engineering",
            "forensics": "forensics",
            "general": "general-skills",
            "general-skills": "general-skills",
            "misc": "general-skills"
        }

        for part in path_parts:
            part_lower = part.lower()
            for key, category in category_mappings.items():
                if key in part_lower:
                    return category

        return "general-skills"  # Default category

    def _clean_description(self, description: str) -> str:
        """Clean and simplify the description."""
        # Remove template variables like {{server}}, {{port}}
        description = re.sub(r'\{\{[^}]+\}\}', '[PLACEHOLDER]', description)

        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)

        # Clean up whitespace
        description = re.sub(r'\s+', ' ', description).strip()

        return description

    def _get_relevant_files(self, challenge_dir: Path) -> List[str]:
        """Get list of files that should be accessible to participants."""
        relevant_extensions = {'.txt', '.py', '.c', '.cpp', '.java', '.js',
                              '.html', '.css', '.png', '.jpg', '.gif', '.zip',
                              '.tar', '.gz', '.pcap', '.exe', '.bin'}

        exclude_files = {'challenge.py', 'Dockerfile', 'Makefile', 'flag',
                        'key', 'server.py', 'problem.json'}

        files = []
        for file_path in challenge_dir.iterdir():
            if file_path.is_file():
                if (file_path.suffix.lower() in relevant_extensions and
                    file_path.name not in exclude_files):
                    files.append(file_path.name)

        return files

    def _copy_challenge_files(self, source_dir: Path, target_dir: Path) -> None:
        """Copy relevant challenge files to target directory."""
        # Copy files that participants need
        relevant_files = self._get_relevant_files(source_dir)

        for filename in relevant_files:
            source_file = source_dir / filename
            target_file = target_dir / filename

            try:
                shutil.copy2(source_file, target_file)
            except Exception as e:
                print(f"    Warning: Could not copy {filename}: {e}")


def create_additional_challenges():
    """Create some additional challenges for variety."""
    additional_challenges = [
        {
            "name": "Base64 Decode",
            "description": "Decode this base64 string: cGljb0NURnt3ZWxjb21lX3RvX2Jhc2U2NH0=",
            "category": "general-skills",
            "flag": "picoCTF{welcome_to_base64}",
            "hints": [
                "Base64 is a common encoding scheme",
                "Use an online decoder or command line tools"
            ],
            "score": 75,
            "author": "RL Environment",
            "files": []
        },
        {
            "name": "Simple XOR",
            "description": "A message was XORed with a single character. Find the key and decode: \n7c2e2f2e6f6c202c6d652e656f6d65",
            "category": "cryptography",
            "flag": "picoCTF{single_byte_xor}",
            "hints": [
                "Try XORing with different single characters",
                "Look for readable English text"
            ],
            "score": 150,
            "author": "RL Environment",
            "files": []
        },
        {
            "name": "Hidden Message",
            "description": "There's a flag hidden in this text file. Can you find it?",
            "category": "forensics",
            "flag": "picoCTF{hidden_in_plain_sight}",
            "hints": [
                "Look at the file carefully",
                "Sometimes things are hidden at the end"
            ],
            "score": 100,
            "author": "RL Environment",
            "files": ["message.txt"]
        }
    ]

    challenges_dir = Path("challenges")
    challenges_dir.mkdir(exist_ok=True)

    for i, challenge in enumerate(additional_challenges):
        challenge_dir = challenges_dir / f"additional_{i}"
        challenge_dir.mkdir(exist_ok=True)

        # Save challenge JSON
        with open(challenge_dir / "challenge.json", "w") as f:
            json.dump(challenge, f, indent=2)

        # Create sample files if needed
        if challenge["name"] == "Hidden Message":
            with open(challenge_dir / "message.txt", "w") as f:
                f.write("""This is a normal text file.
Nothing suspicious here.
Just some regular content.

Hope you're having a good day!

End of file.
picoCTF{hidden_in_plain_sight}""")


def main():
    """Main conversion function."""
    if len(sys.argv) < 2:
        print("Usage: python challenge_converter.py <source_problems_dir> [target_dir]")
        print("\nThis will convert picoCTF problems to RL environment format.")
        return

    source_dir = Path(sys.argv[1])
    target_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("challenges")

    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        return

    print(f"Converting challenges from {source_dir} to {target_dir}")

    converter = ChallengeConverter(source_dir, target_dir)
    converter.convert_all()

    # Add some additional challenges
    print("\nCreating additional sample challenges...")
    create_additional_challenges()

    print(f"\nConversion complete! Challenges saved to {target_dir}")
    print("You can now use these with the RL environment.")


if __name__ == "__main__":
    main()