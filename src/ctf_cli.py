#!/usr/bin/env python3
"""
Interactive CLI for testing CTF challenges.

This provides a simple command-line interface to play around with
the CTF environment and test challenges.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import re

from .ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel, CategoryType


class CTFSession:
    """Interactive CTF challenge session manager."""

    def __init__(self, dataset: CTFDataset) -> None:
        """Initialize the session with a dataset."""
        self.dataset = dataset
        self.current_challenge: Optional[CTFChallenge] = None
        self.attempts: List[str] = []
        self.score = 0
        self.solved_challenges: List[str] = []

    def start(self) -> None:
        """Start the interactive session."""
        print("🚩 Welcome to picoCTF Environment CLI!")
        print("=" * 50)

        stats = self.dataset.get_dataset_stats()
        print(f"Loaded {stats.total_challenges} challenges")
        print(f"Categories: {', '.join(stats.categories.keys())}")
        print(f"Difficulties: {', '.join(stats.difficulties.keys())}")
        print()

        self.show_help()

        while True:
            try:
                command = input("\nctf> ").strip().lower()
                if not command:
                    continue

                if command in ['quit', 'exit', 'q']:
                    print("👋 Thanks for playing!")
                    break
                elif command in ['help', 'h', '?']:
                    self.show_help()
                elif command in ['list', 'ls']:
                    self.list_challenges()
                elif command.startswith('select '):
                    challenge_id = command[7:].strip()
                    self.select_challenge(challenge_id)
                elif command in ['info', 'i']:
                    self.show_current_challenge()
                elif command in ['hint', 'hints']:
                    self.show_hints()
                elif command.startswith('submit '):
                    flag = command[7:].strip()
                    self.submit_flag(flag)
                elif command in ['stats', 'score']:
                    self.show_stats()
                elif command in ['random', 'rand', 'r']:
                    self.random_challenge()
                elif command.startswith('category '):
                    category = command[9:].strip()
                    self.list_by_category(category)
                elif command.startswith('difficulty '):
                    difficulty = command[11:].strip()
                    self.list_by_difficulty(difficulty)
                elif command in ['files']:
                    self.show_files()
                elif command in ['env', 'environment']:
                    self.show_environment()
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n👋 Thanks for playing!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def show_help(self) -> None:
        """Show available commands."""
        help_text = """
📚 Available Commands:
  help, h, ?           - Show this help
  list, ls             - List all challenges
  select <id>          - Select a challenge by ID
  random, rand, r      - Select a random challenge
  category <cat>       - List challenges by category
  difficulty <diff>    - List challenges by difficulty
  info, i              - Show current challenge details
  hint, hints          - Show hints for current challenge
  submit <flag>        - Submit a flag for current challenge
  files                - Show files for current challenge
  env, environment     - Show environment info for current challenge
  stats, score         - Show your progress
  quit, exit, q        - Exit the CLI

🎯 Categories: general, crypto, forensics, web, binary, reverse
🔥 Difficulties: easy, medium, hard
        """
        print(help_text)

    def list_challenges(self) -> None:
        """List all available challenges."""
        print("\n📋 Available Challenges:")
        print("-" * 60)

        by_category: Dict[CategoryType, List[CTFChallenge]] = {}
        for challenge in self.dataset.challenges:
            if challenge.category not in by_category:
                by_category[challenge.category] = []
            by_category[challenge.category].append(challenge)

        for category, challenges in by_category.items():
            print(f"\n🏷️  {category.upper()}:")
            for challenge in challenges:
                solved = "✅" if challenge.id in self.solved_challenges else "⭕"
                difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                diff_emoji = difficulty_emoji.get(challenge.difficulty.value, "⚪")
                files_indicator = "📁" if challenge.files else "  "
                print(f"  {solved} {diff_emoji} {files_indicator} {challenge.id:15s} - {challenge.name} ({challenge.points}pts)")

    def list_by_category(self, category: str) -> None:
        """List challenges by category."""
        if category not in ['general', 'crypto', 'forensics', 'web', 'binary', 'reverse']:
            print(f"❌ Invalid category: {category}")
            print("Valid categories: general, crypto, forensics, web, binary, reverse")
            return

        challenges = self.dataset.get_challenges_by_category(category)  # type: ignore
        if not challenges:
            print(f"No challenges found in category: {category}")
            return

        print(f"\n📋 {category.upper()} Challenges:")
        print("-" * 40)
        for challenge in challenges:
            solved = "✅" if challenge.id in self.solved_challenges else "⭕"
            files_indicator = "📁" if challenge.files else "  "
            print(f"  {solved} {files_indicator} {challenge.id:15s} - {challenge.name} ({challenge.points}pts)")

    def list_by_difficulty(self, difficulty: str) -> None:
        """List challenges by difficulty."""
        try:
            diff_level = DifficultyLevel(difficulty)
        except ValueError:
            print(f"❌ Invalid difficulty: {difficulty}")
            print("Valid difficulties: easy, medium, hard")
            return

        challenges = self.dataset.get_challenges_by_difficulty(diff_level)
        if not challenges:
            print(f"No challenges found with difficulty: {difficulty}")
            return

        print(f"\n📋 {difficulty.upper()} Challenges:")
        print("-" * 40)
        for challenge in challenges:
            solved = "✅" if challenge.id in self.solved_challenges else "⭕"
            files_indicator = "📁" if challenge.files else "  "
            print(f"  {solved} {files_indicator} {challenge.id:15s} - {challenge.name} ({challenge.points}pts)")

    def select_challenge(self, challenge_id: str) -> None:
        """Select a challenge to work on."""
        challenge = self.dataset.get_challenge_by_id(challenge_id)
        if not challenge:
            print(f"❌ Challenge not found: {challenge_id}")
            return

        self.current_challenge = challenge
        self.attempts = []
        print(f"🎯 Selected challenge: {challenge.name}")
        self.show_current_challenge()

    def random_challenge(self) -> None:
        """Select a random challenge."""
        # Prefer unsolved challenges
        unsolved = [c for c in self.dataset.challenges if c.id not in self.solved_challenges]
        if unsolved:
            challenge = self.dataset.get_random_challenge()
            # Try to get an unsolved one from the same category
            candidates = [c for c in unsolved if c.category == challenge.category]
            if candidates:
                challenge = candidates[0]
            else:
                challenge = unsolved[0]
        else:
            challenge = self.dataset.get_random_challenge()

        self.current_challenge = challenge
        self.attempts = []
        print(f"🎲 Random challenge: {challenge.name}")
        self.show_current_challenge()

    def show_current_challenge(self) -> None:
        """Show details of the current challenge."""
        if not self.current_challenge:
            print("❌ No challenge selected. Use 'select <id>' or 'random'")
            return

        c = self.current_challenge
        solved = "✅ SOLVED" if c.id in self.solved_challenges else "🎯 UNSOLVED"
        difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        diff_emoji = difficulty_emoji.get(c.difficulty.value, "⚪")

        print(f"\n{solved}")
        print("=" * 50)
        print(f"🏷️  ID: {c.id}")
        print(f"📝 Name: {c.name}")
        print(f"📂 Category: {c.category}")
        print(f"{diff_emoji} Difficulty: {c.difficulty.value}")
        print(f"💰 Points: {c.points}")
        print(f"🔄 Attempts: {len(self.attempts)}")
        print()
        print("📖 Description:")
        print(f"   {c.description}")

        if c.files:
            print(f"\n📁 Files: {', '.join(c.files)}")
            print("   (Use 'files' command for file details)")

        if c.environment:
            print(f"\n🔧 Environment: Available (use 'env' command)")

        print("\n💡 Use 'hint' for hints, 'submit <flag>' to submit a solution")

    def show_files(self) -> None:
        """Show files for the current challenge."""
        if not self.current_challenge:
            print("❌ No challenge selected")
            return

        if not self.current_challenge.files:
            print("📁 No files for this challenge")
            return

        print(f"\n📁 Files for {self.current_challenge.name}:")
        files_dir = self.dataset.data_dir / "files"

        for filename in self.current_challenge.files:
            file_path = files_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  📄 {filename} ({size} bytes)")
                print(f"     Location: {file_path}")

                # Show file content preview for small text files
                if size < 1024 and filename.endswith(('.txt', '.md', '.py', '.js', '.html')):
                    try:
                        content = file_path.read_text(encoding='utf-8')[:200]
                        print(f"     Preview: {content}{'...' if len(content) == 200 else ''}")
                    except:
                        print("     (Binary or unreadable content)")
            else:
                print(f"  ❌ {filename} (file not found)")

    def show_environment(self) -> None:
        """Show environment information for the current challenge."""
        if not self.current_challenge:
            print("❌ No challenge selected")
            return

        if not self.current_challenge.environment:
            print("🔧 No special environment configuration for this challenge")
            return

        print(f"\n🔧 Environment for {self.current_challenge.name}:")
        env = self.current_challenge.environment

        for key, value in env.items():
            print(f"  {key}: {value}")

    def show_hints(self) -> None:
        """Show hints for the current challenge."""
        if not self.current_challenge:
            print("❌ No challenge selected")
            return

        hints = self.current_challenge.hints
        if not hints:
            print("💡 No hints available for this challenge")
            return

        # Show hints progressively based on number of attempts
        hints_to_show = min(len(self.attempts) + 1, len(hints))

        print(f"\n💡 Hints ({hints_to_show}/{len(hints)} available):")
        for i in range(hints_to_show):
            print(f"  {i+1}. {hints[i]}")

        if hints_to_show < len(hints):
            print(f"   (Make more attempts to unlock {len(hints) - hints_to_show} more hints)")

    def submit_flag(self, flag: str) -> None:
        """Submit a flag for the current challenge."""
        if not self.current_challenge:
            print("❌ No challenge selected")
            return

        # Clean up the flag
        flag = flag.strip()
        if not flag:
            print("❌ Empty flag submitted")
            return

        self.attempts.append(flag)
        c = self.current_challenge

        # Check if correct
        if flag == c.flag:
            print("🎉 CORRECT! Well done!")
            if c.id not in self.solved_challenges:
                self.solved_challenges.append(c.id)
                self.score += c.points
                print(f"💰 +{c.points} points! Total score: {self.score}")
            else:
                print("(Already solved - no additional points)")
            return

        # Check for common issues
        if flag.lower() == c.flag.lower():
            print("🔸 Almost! Check the capitalization")
            return

        if not flag.startswith("picoCTF{"):
            print("🔸 Remember: flags should start with 'picoCTF{'")
            return

        if not flag.endswith("}"):
            print("🔸 Remember: flags should end with '}'")
            return

        # Check for partial credit
        correct_content = re.findall(r'picoCTF\{(.*?)\}', c.flag)
        submitted_content = re.findall(r'picoCTF\{(.*?)\}', flag)

        if correct_content and submitted_content:
            correct_words = set(correct_content[0].lower().split('_'))
            submitted_words = set(submitted_content[0].lower().split('_'))

            intersection = correct_words.intersection(submitted_words)
            if intersection:
                print(f"🔸 Partially correct! You got: {', '.join(intersection)}")
                print("   Keep working on it!")
                return

        print("❌ Incorrect. Try again!")

        # Show hints after a few attempts
        if len(self.attempts) >= 2:
            print("💡 Type 'hint' if you need help")

    def show_stats(self) -> None:
        """Show session statistics."""
        total_challenges = len(self.dataset.challenges)
        solved_count = len(self.solved_challenges)
        completion_rate = (solved_count / total_challenges * 100) if total_challenges > 0 else 0

        print(f"\n📊 Your Progress:")
        print("-" * 30)
        print(f"🎯 Total Score: {self.score}")
        print(f"✅ Solved: {solved_count}/{total_challenges} ({completion_rate:.1f}%)")

        if self.current_challenge:
            print(f"🔄 Current: {self.current_challenge.name} ({len(self.attempts)} attempts)")

        # Show solved challenges by category
        if self.solved_challenges:
            print(f"\n🏆 Solved Challenges:")
            for challenge_id in self.solved_challenges:
                challenge = self.dataset.get_challenge_by_id(challenge_id)
                if challenge:
                    print(f"  ✅ {challenge.name} ({challenge.points}pts)")


def main() -> None:
    """Main CLI entry point."""
    print("🚀 Initializing CTF Environment...")

    # Initialize dataset
    try:
        dataset = CTFDataset()
        if not dataset.challenges:
            print("❌ No challenges found! Make sure you have challenges in the env/dataset directory.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        sys.exit(1)

    # Start interactive session
    session = CTFSession(dataset)
    session.start()


if __name__ == "__main__":
    main()