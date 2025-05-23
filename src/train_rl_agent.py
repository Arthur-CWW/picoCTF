#!/usr/bin/env python3
"""
Training script for LLM agents on picoCTF challenges.

This script demonstrates different approaches to training LLM agents:
1. Simple reinforcement learning with reward signals
2. Imitation learning from demonstration
3. Self-play and curriculum learning
"""

import json
import random
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from picoctf_rl_env import PicoCTFRLEnv, CategoryType


@dataclass
class Episode:
    """Represents a complete episode of challenge solving."""
    challenge_name: str
    category: str
    attempts: List[str]
    rewards: List[float]
    final_score: int
    solved: bool
    duration: float


class LLMAgent:
    """
    Simplified LLM agent interface for CTF challenges.

    In practice, this would interface with actual LLM APIs or local models.
    For demonstration, we'll use rule-based strategies.
    """

    def __init__(self, strategy: str = "random"):
        """
        Initialize the agent with a specific strategy.

        Args:
            strategy: "random", "pattern_based", or "curriculum"
        """
        self.strategy = strategy
        self.memory: List[Episode] = []
        self.learned_patterns: Dict[str, List[str]] = {}

    def predict(self, observation: Dict[str, Any]) -> str:
        """
        Generate a flag prediction based on the observation.

        Args:
            observation: Current environment observation

        Returns:
            Predicted flag string
        """
        if self.strategy == "random":
            return self._random_strategy(observation)
        elif self.strategy == "pattern_based":
            return self._pattern_based_strategy(observation)
        elif self.strategy == "curriculum":
            return self._curriculum_strategy(observation)
        else:
            return "picoCTF{unknown}"

    def _random_strategy(self, obs: Dict[str, Any]) -> str:
        """Simple random strategy for baseline."""
        random_flags = [
            "picoCTF{test}",
            "picoCTF{flag}",
            "picoCTF{hello_world}",
            "picoCTF{answer}",
            "picoCTF{solution}",
            f"picoCTF{{{random.randint(1000, 9999)}}}",
        ]
        return random.choice(random_flags)

    def _pattern_based_strategy(self, obs: Dict[str, Any]) -> str:
        """Strategy that learns from patterns in descriptions."""
        description = obs.get("description", "").lower()
        category = obs.get("category", "")

        # Look for common patterns
        if "base64" in description:
            # Try to decode base64 in description
            import base64
            import re

            # Find base64-like strings
            b64_matches = re.findall(r'[A-Za-z0-9+/]{20,}={0,2}', obs.get("description", ""))
            for match in b64_matches:
                try:
                    decoded = base64.b64decode(match).decode('utf-8')
                    if decoded.startswith('picoCTF{'):
                        return decoded
                except:
                    continue

        if "caesar" in description or "rot" in description:
            # Try ROT13 on any suspicious strings
            import codecs
            text_in_desc = re.findall(r'[a-zA-Z]{10,}', description)
            for text in text_in_desc:
                rotated = codecs.encode(text, 'rot13')
                if 'pico' in rotated.lower() or 'flag' in rotated.lower():
                    return f"picoCTF{{{rotated}}}"

        if "hidden" in description and obs.get("files"):
            # Suggest looking at files
            return "picoCTF{hidden_in_plain_sight}"

        # Category-specific patterns
        category_patterns = {
            "general-skills": ["hello_world", "welcome", "basic"],
            "cryptography": ["decrypt", "cipher", "decode", "crypto"],
            "forensics": ["hidden", "investigate", "analyze"],
            "web-exploitation": ["web", "http", "server"],
        }

        if category in category_patterns:
            pattern = random.choice(category_patterns[category])
            return f"picoCTF{{{pattern}}}"

        return "picoCTF{pattern_not_found}"

    def _curriculum_strategy(self, obs: Dict[str, Any]) -> str:
        """Advanced strategy using curriculum learning."""
        # Use learned patterns from previous episodes
        category = obs.get("category", "")

        if category in self.learned_patterns:
            # Try patterns that worked for similar challenges
            successful_patterns = self.learned_patterns[category]
            if successful_patterns:
                base_pattern = random.choice(successful_patterns)
                # Try variations
                variations = [
                    base_pattern,
                    base_pattern.replace('_', '-'),
                    base_pattern.upper(),
                    base_pattern.lower(),
                    f"{base_pattern}_variation"
                ]
                return f"picoCTF{{{random.choice(variations)}}}"

        # Fall back to pattern-based strategy
        return self._pattern_based_strategy(obs)

    def learn_from_episode(self, episode: Episode) -> None:
        """Learn from a completed episode."""
        self.memory.append(episode)

        # Extract patterns from successful episodes
        if episode.solved:
            # Find the successful flag content
            for i, reward in enumerate(episode.rewards):
                if reward > 0:  # Successful or partially successful attempt
                    flag = episode.attempts[i]
                    if flag.startswith("picoCTF{") and flag.endswith("}"):
                        content = flag[8:-1]  # Extract content between braces

                        if episode.category not in self.learned_patterns:
                            self.learned_patterns[episode.category] = []

                        if content not in self.learned_patterns[episode.category]:
                            self.learned_patterns[episode.category].append(content)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent learning statistics."""
        if not self.memory:
            return {"episodes": 0, "success_rate": 0.0}

        total_episodes = len(self.memory)
        successful_episodes = sum(1 for ep in self.memory if ep.solved)
        attempt_counts = [len(ep.attempts) for ep in self.memory]
        avg_attempts = sum(attempt_counts) / len(attempt_counts) if attempt_counts else 0

        return {
            "episodes": total_episodes,
            "success_rate": successful_episodes / total_episodes,
            "avg_attempts": avg_attempts,
            "learned_patterns": dict(self.learned_patterns),
            "total_score": sum(ep.final_score for ep in self.memory)
        }


class RLTrainer:
    """Reinforcement Learning trainer for CTF challenges."""

    def __init__(self, env: PicoCTFRLEnv, agent: LLMAgent):
        """
        Initialize trainer.

        Args:
            env: The CTF environment
            agent: The LLM agent to train
        """
        self.env = env
        self.agent = agent
        self.training_history: List[Episode] = []

    def train_episodes(self, num_episodes: int,
                      category_filter: Optional[CategoryType] = None,
                      verbose: bool = True) -> None:
        """
        Train the agent for a specified number of episodes.

        Args:
            num_episodes: Number of training episodes
            category_filter: Optional category to focus on
            verbose: Whether to print progress
        """
        print(f"Starting training for {num_episodes} episodes...")
        if category_filter:
            print(f"Focusing on category: {category_filter.value}")

        for episode_num in range(num_episodes):
            start_time = time.time()

            # Reset environment
            obs = self.env.reset(category=category_filter)

            attempts = []
            rewards = []
            done = False

            if verbose and episode_num % 10 == 0:
                print(f"\nEpisode {episode_num + 1}: {obs['challenge_name']}")

            # Run episode
            while not done:
                # Agent makes prediction
                action = self.agent.predict(obs)
                attempts.append(action)

                # Environment step
                obs, reward, done, info = self.env.step(action)
                rewards.append(reward)

                if verbose and episode_num % 10 == 0:
                    print(f"  Attempt: {action[:30]}... -> Reward: {reward:.2f}")

                if done:
                    if info["correct"]:
                        if verbose and episode_num % 10 == 0:
                            print(f"  ✓ Solved! Score: {info['challenge_score']}")
                    else:
                        if verbose and episode_num % 10 == 0:
                            print(f"  ✗ Failed after {len(attempts)} attempts")

            # Create episode record
            episode = Episode(
                challenge_name=obs.get("challenge_name", "Unknown"),
                category=obs.get("category", "Unknown"),
                attempts=attempts,
                rewards=rewards,
                final_score=info.get("challenge_score", 0),
                solved=info["correct"],
                duration=time.time() - start_time
            )

            # Learn from episode
            self.agent.learn_from_episode(episode)
            self.training_history.append(episode)

        self._print_training_summary()

    def curriculum_training(self, verbose: bool = True) -> None:
        """
        Train using curriculum learning (easy to hard categories).
        """
        print("Starting curriculum training...")

        # Define curriculum order (easier to harder)
        curriculum = [
            (CategoryType.GENERAL_SKILLS, 20),
            (CategoryType.CRYPTOGRAPHY, 25),
            (CategoryType.FORENSICS, 20),
            (CategoryType.WEB_EXPLOITATION, 15),
            (CategoryType.BINARY_EXPLOITATION, 10)
        ]

        for category, episodes in curriculum:
            print(f"\n--- Training on {category.value} ({episodes} episodes) ---")
            self.train_episodes(episodes, category_filter=category, verbose=verbose)

            # Print intermediate stats
            stats = self.agent.get_stats()
            print(f"Current success rate: {stats['success_rate']:.2%}")

    def _print_training_summary(self) -> None:
        """Print summary of training results."""
        if not self.training_history:
            return

        total_episodes = len(self.training_history)
        successful = sum(1 for ep in self.training_history if ep.solved)
        total_score = sum(ep.final_score for ep in self.training_history)

        print(f"\n{'='*50}")
        print(f"TRAINING SUMMARY")
        print(f"{'='*50}")
        print(f"Total episodes: {total_episodes}")
        print(f"Success rate: {successful}/{total_episodes} ({successful/total_episodes:.2%})")
        print(f"Total score: {total_score}")
        print(f"Average score per episode: {total_score/total_episodes:.1f}")

        # Category breakdown
        category_stats = {}
        for episode in self.training_history:
            cat = episode.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "solved": 0, "score": 0}

            category_stats[cat]["total"] += 1
            if episode.solved:
                category_stats[cat]["solved"] += 1
            category_stats[cat]["score"] += episode.final_score

        print(f"\nCategory Performance:")
        for category, stats in category_stats.items():
            success_rate = stats["solved"] / stats["total"] if stats["total"] > 0 else 0
            print(f"  {category:20s}: {stats['solved']:2d}/{stats['total']:2d} ({success_rate:.1%}) - {stats['score']:4d} pts")


def save_training_data(trainer: RLTrainer, filename: str = "training_data.json") -> None:
    """Save training data for analysis."""
    data = {
        "episodes": [
            {
                "challenge_name": ep.challenge_name,
                "category": ep.category,
                "attempts": ep.attempts,
                "rewards": ep.rewards,
                "final_score": ep.final_score,
                "solved": ep.solved,
                "duration": ep.duration
            }
            for ep in trainer.training_history
        ],
        "agent_stats": trainer.agent.get_stats()
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Training data saved to {filename}")


def main():
    """Main training function."""
    print("Initializing picoCTF RL Environment...")

    # Create environment
    env = PicoCTFRLEnv(
        challenges_dir=Path("challenges"),
        max_attempts=5,
        reward_correct=10.0,
        reward_incorrect=-1.0,
        reward_partial=2.0
    )

    print(f"Loaded {len(env.challenges)} challenges")

    # Test different agent strategies
    strategies = ["random", "pattern_based", "curriculum"]

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Testing {strategy.upper()} strategy")
        print(f"{'='*60}")

        agent = LLMAgent(strategy=strategy)
        trainer = RLTrainer(env, agent)

        if strategy == "curriculum":
            trainer.curriculum_training(verbose=False)
        else:
            trainer.train_episodes(50, verbose=False)

        # Save results
        save_training_data(trainer, f"training_data_{strategy}.json")

        print(f"\nFinal agent stats:")
        stats = agent.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()