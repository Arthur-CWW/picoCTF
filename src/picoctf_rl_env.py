#!/usr/bin/env python3
"""
Minimal picoCTF RL Environment for LLM Training

This is a simplified adaptation of the picoCTF platform specifically designed
for reinforcement learning with language models.
"""

import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class CategoryType(Enum):
    CRYPTOGRAPHY = "cryptography"
    WEB_EXPLOITATION = "web-exploitation"
    BINARY_EXPLOITATION = "binary-exploitation"
    REVERSE_ENGINEERING = "reverse-engineering"
    FORENSICS = "forensics"
    GENERAL_SKILLS = "general-skills"


@dataclass
class Challenge:
    """Represents a single CTF challenge."""
    name: str
    description: str
    category: CategoryType
    flag: str
    hints: List[str]
    score: int
    author: str
    files: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.files is None:
            self.files = []


class PicoCTFRLEnv:
    """
    Minimal RL Environment for picoCTF challenges.

    This environment provides:
    - Challenge selection and presentation
    - Flag validation and reward calculation
    - Episode management
    - Multi-challenge support
    """

    def __init__(self,
                 challenges_dir: Optional[Path] = None,
                 max_attempts: int = 10,
                 reward_correct: float = 1.0,
                 reward_incorrect: float = -0.1,
                 reward_partial: float = 0.5,
                 enable_hints: bool = True):
        """
        Initialize the RL environment.

        Args:
            challenges_dir: Directory containing challenge definitions
            max_attempts: Maximum attempts per challenge before episode ends
            reward_correct: Reward for correct flag
            reward_incorrect: Penalty for incorrect flag
            reward_partial: Reward for partial credit (if applicable)
            enable_hints: Whether to provide hints as part of observation
        """
        self.challenges_dir = challenges_dir or Path("challenges")
        self.max_attempts = max_attempts
        self.reward_correct = reward_correct
        self.reward_incorrect = reward_incorrect
        self.reward_partial = reward_partial
        self.enable_hints = enable_hints

        # Environment state
        self.current_challenge: Optional[Challenge] = None
        self.attempts_made = 0
        self.challenges_completed = 0
        self.total_score = 0
        self.episode_active = False

        # Load available challenges
        self.challenges: List[Challenge] = []
        self.load_challenges()

    def load_challenges(self) -> None:
        """Load challenges from the challenges directory."""
        if not self.challenges_dir.exists():
            print(f"Warning: Challenges directory {self.challenges_dir} does not exist")
            self._create_sample_challenges()
            return

        for challenge_file in self.challenges_dir.glob("**/challenge.json"):
            try:
                with open(challenge_file) as f:
                    data = json.load(f)

                challenge = Challenge(
                    name=data["name"],
                    description=data["description"],
                    category=CategoryType(data["category"]),
                    flag=data["flag"],
                    hints=data.get("hints", []),
                    score=data.get("score", 100),
                    author=data.get("author", "Unknown"),
                    files=data.get("files", [])
                )
                self.challenges.append(challenge)

            except Exception as e:
                print(f"Error loading challenge {challenge_file}: {e}")

        print(f"Loaded {len(self.challenges)} challenges")

    def _create_sample_challenges(self) -> None:
        """Create sample challenges for demonstration."""
        self.challenges_dir.mkdir(parents=True, exist_ok=True)

        sample_challenges = [
            {
                "name": "Basic Flag",
                "description": "Find the flag hidden in this message: The secret word is 'picoCTF{hello_world}'",
                "category": "general-skills",
                "flag": "picoCTF{hello_world}",
                "hints": ["Look for text in the picoCTF{} format"],
                "score": 50,
                "author": "RL Environment"
            },
            {
                "name": "Caesar Cipher",
                "description": "Decrypt this Caesar cipher: ovdp{pblah_iba_ybir_zngu}",
                "category": "cryptography",
                "flag": "picoCTF{math_is_fun_love_math}",
                "hints": ["Try different shift values", "ROT13 is a common Caesar cipher"],
                "score": 100,
                "author": "RL Environment"
            }
        ]

        for i, challenge_data in enumerate(sample_challenges):
            challenge_dir = self.challenges_dir / f"sample_{i}"
            challenge_dir.mkdir(exist_ok=True)

            with open(challenge_dir / "challenge.json", "w") as f:
                json.dump(challenge_data, f, indent=2)

            challenge = Challenge(**challenge_data, category=CategoryType(challenge_data["category"]))
            self.challenges.append(challenge)

    def reset(self, challenge_name: Optional[str] = None, category: Optional[CategoryType] = None) -> Dict[str, Any]:
        """
        Reset the environment for a new episode.

        Args:
            challenge_name: Specific challenge to load (optional)
            category: Category to filter challenges by (optional)

        Returns:
            Initial observation
        """
        self.attempts_made = 0
        self.episode_active = True

        # Select challenge
        if challenge_name:
            challenges = [c for c in self.challenges if c.name == challenge_name]
            if not challenges:
                raise ValueError(f"Challenge '{challenge_name}' not found")
            self.current_challenge = challenges[0]
        elif category:
            challenges = [c for c in self.challenges if c.category == category]
            if not challenges:
                raise ValueError(f"No challenges found for category '{category.value}'")
            self.current_challenge = random.choice(challenges)
        else:
            self.current_challenge = random.choice(self.challenges)

        return self._get_observation()

    def step(self, action: str) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.

        Args:
            action: The agent's flag submission (string)

        Returns:
            observation, reward, done, info
        """
        if not self.episode_active or self.current_challenge is None:
            raise RuntimeError("Episode not active. Call reset() first.")

        self.attempts_made += 1

        # Check flag correctness
        correct, reward, partial_credit = self._evaluate_flag(action)

        # Determine if episode is done
        done = correct or self.attempts_made >= self.max_attempts

        if correct:
            self.challenges_completed += 1
            self.total_score += self.current_challenge.score

        if done:
            self.episode_active = False

        observation = self._get_observation()

        info = {
            "correct": correct,
            "partial_credit": partial_credit,
            "attempts_remaining": self.max_attempts - self.attempts_made,
            "challenge_score": self.current_challenge.score if correct else 0,
            "submitted_flag": action,
            "correct_flag": self.current_challenge.flag if done else None
        }

        return observation, reward, done, info

    def _evaluate_flag(self, submitted_flag: str) -> Tuple[bool, float, bool]:
        """
        Evaluate a submitted flag.

        Args:
            submitted_flag: The flag submitted by the agent

        Returns:
            (is_correct, reward, has_partial_credit)
        """
        if self.current_challenge is None:
            return False, self.reward_incorrect, False

        correct_flag = self.current_challenge.flag.strip()
        submitted_flag = submitted_flag.strip()

        # Exact match
        if submitted_flag == correct_flag:
            return True, self.reward_correct, False

        # Case-insensitive match
        if submitted_flag.lower() == correct_flag.lower():
            return True, self.reward_correct * 0.9, True

        # Partial credit for containing the flag content
        if self._has_flag_format(submitted_flag) and self._similar_content(submitted_flag, correct_flag):
            return False, self.reward_partial, True

        # No credit
        return False, self.reward_incorrect, False

    def _has_flag_format(self, flag: str) -> bool:
        """Check if the flag has the correct format (picoCTF{...})."""
        return bool(re.match(r'picoCTF\{.*\}', flag))

    def _similar_content(self, submitted: str, correct: str) -> bool:
        """Check if submitted flag has similar content to correct flag."""
        # Extract content between braces
        submitted_content = re.findall(r'picoCTF\{(.*?)\}', submitted)
        correct_content = re.findall(r'picoCTF\{(.*?)\}', correct)

        if not submitted_content or not correct_content:
            return False

        # Simple similarity check
        submitted_words = set(submitted_content[0].lower().split('_'))
        correct_words = set(correct_content[0].lower().split('_'))

        intersection = submitted_words.intersection(correct_words)
        union = submitted_words.union(correct_words)

        similarity = len(intersection) / len(union) if union else 0
        return similarity > 0.5

    def _get_observation(self) -> Dict[str, Any]:
        """Get current environment observation."""
        if not self.current_challenge:
            return {"error": "No active challenge"}

        obs = {
            "challenge_name": self.current_challenge.name,
            "description": self.current_challenge.description,
            "category": self.current_challenge.category.value,
            "score": self.current_challenge.score,
            "author": self.current_challenge.author,
            "attempts_made": self.attempts_made,
            "attempts_remaining": self.max_attempts - self.attempts_made,
            "files": self.current_challenge.files
        }

        if self.enable_hints and self.attempts_made > 2:
            obs["hints"] = self.current_challenge.hints[:self.attempts_made - 2]

        return obs

    def get_challenge_list(self, category: Optional[CategoryType] = None) -> List[Dict[str, Any]]:
        """Get list of available challenges, optionally filtered by category."""
        challenges = self.challenges
        if category:
            challenges = [c for c in challenges if c.category == category]

        return [
            {
                "name": c.name,
                "category": c.category.value,
                "score": c.score,
                "author": c.author
            }
            for c in challenges
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get current environment statistics."""
        return {
            "challenges_completed": self.challenges_completed,
            "total_score": self.total_score,
            "total_challenges": len(self.challenges),
            "completion_rate": self.challenges_completed / len(self.challenges) if self.challenges else 0
        }


# Example usage and testing functions
def demo_environment():
    """Demonstrate the RL environment."""
    env = PicoCTFRLEnv()

    print("Available challenges:")
    for challenge in env.get_challenge_list():
        print(f"  - {challenge['name']} ({challenge['category']}) - {challenge['score']} pts")

    print("\n" + "="*50)
    print("Starting episode...")

    obs = env.reset()
    print(f"Challenge: {obs['challenge_name']}")
    print(f"Description: {obs['description']}")
    print(f"Category: {obs['category']}")

    # Simulate some attempts
    test_submissions = ["wrong_flag", "picoCTF{wrong}", "picoCTF{hello_world}"]

    for submission in test_submissions:
        if not env.episode_active:
            break

        print(f"\nSubmitting: {submission}")
        obs, reward, done, info = env.step(submission)

        print(f"Reward: {reward}")
        print(f"Correct: {info['correct']}")
        print(f"Attempts remaining: {info['attempts_remaining']}")

        if done:
            print(f"Episode finished! Final score: {info['challenge_score']}")
            break


if __name__ == "__main__":
    demo_environment()