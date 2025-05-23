#!/usr/bin/env python3
"""
Advanced CTF CLI with dynamic challenge loading and admin functionality.

Features:
- Dynamic challenge discovery and loading
- Tyro-based CLI with rich command line arguments
- Admin commands for environment inspection
- Type-safe operations with pydantic models
"""
from .nested import subcommand_cli_from_nested_dict

import sys
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal, Union, Callable
from dataclasses import dataclass, field
import logging
import random

import tyro
from tyro.extras import SubcommandApp,subcommand_cli_from_dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import print as rprint

from .ctf_models import (
    CTFChallenge,
    CategoryType,
    DifficultyLevel,
    DatasetStats,
    SessionState
)
from .challenge_loader import ChallengeLoader, load_challenges_dynamically

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from .ctf_dataset import app as ctf_dataset_main
console = Console()

# Create the main application
app = SubcommandApp()

# Constants for emojis and formatting
DIFFICULTY_EMOJIS = {
    DifficultyLevel.EASY: "🟢 Easy",
    DifficultyLevel.MEDIUM: "🟡 Med",
    DifficultyLevel.HARD: "🔴 Hard"
}

STATUS_EMOJIS = {"solved": "✅", "unsolved": "⭕"}


@dataclass
class CLIConfig:
    """Configuration for the CTF CLI."""
    base_path: Path = Path(".")
    challenge_sources: List[str] = field(default_factory=lambda: ["picoctf_problems", "json_datasets"])
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    session_file: Optional[Path] = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING"
    color: bool = True

    def __post_init__(self):
        """Set up logging level."""
        logging.getLogger().setLevel(getattr(logging, self.log_level))


class CTFSession:
    """Enhanced CTF session with rich display and persistence."""

    def __init__(self, config: CLIConfig) -> None:
        """Initialize the session with configuration."""
        self.config = config
        self.console = Console()
        self.challenges: List[CTFChallenge] = []
        self.current_challenge: Optional[CTFChallenge] = None
        self.state = SessionState()
        self._challenge_index: Dict[str, CTFChallenge] = {}

        # Command registry for cleaner command handling
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            'help': lambda _: self.show_help(),
            'h': lambda _: self.show_help(),
            '?': lambda _: self.show_help(),
            'list': lambda _: self.list_challenges(),
            'ls': lambda _: self.list_challenges(),
            'select': lambda args: self.select_challenge(args[0]) if args else self._show_error("Usage: select <id>"),
            'info': lambda _: self.show_current_challenge(),
            'i': lambda _: self.show_current_challenge(),
            'hint': lambda _: self.show_hints(),
            'hints': lambda _: self.show_hints(),
            'submit': lambda args: self.submit_flag(' '.join(args)) if args else self._show_error("Usage: submit <flag>"),
            'stats': lambda _: self.show_stats(),
            'score': lambda _: self.show_stats(),
            'random': lambda _: self.random_challenge(),
            'rand': lambda _: self.random_challenge(),
            'r': lambda _: self.random_challenge(),
            'category': lambda args: self.list_by_category(args[0]) if args else self._show_error("Usage: category <name>"),
            'difficulty': lambda args: self.list_by_difficulty(args[0]) if args else self._show_error("Usage: difficulty <level>"),
            'files': lambda _: self.show_files(),
            'env': lambda _: self.show_environment(),
            'environment': lambda _: self.show_environment(),
            'sources': lambda _: self.show_sources(),
            'reload': lambda _: self.reload_challenges(),
        }

        # Load session state if file exists
        if config.session_file and config.session_file.exists():
            self.load_session_state()

    def _show_error(self, message: str) -> None:
        """Helper to show error messages."""
        self.console.print(f"❌ [red]{message}[/red]")

    def _get_challenge_status(self, challenge: CTFChallenge) -> str:
        """Get status emoji for a challenge."""
        return STATUS_EMOJIS["solved"] if challenge.id in self.state.solved_challenges else STATUS_EMOJIS["unsolved"]

    def _get_difficulty_display(self, difficulty: DifficultyLevel) -> str:
        """Get difficulty display with emoji."""
        return DIFFICULTY_EMOJIS.get(difficulty, str(difficulty))

    def _create_challenge_table(self, challenges: List[CTFChallenge], title: str, extra_columns: Optional[List[str]] = None) -> Table:
        """Helper to create standardized challenge tables."""
        table = Table(title=f"{title} ({len(challenges)})")
        table.add_column("Status", width=6)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")

        if not extra_columns or "category" in extra_columns:
            table.add_column("Category", style="magenta")
        if not extra_columns or "difficulty" in extra_columns:
            table.add_column("Difficulty", width=10)
        if not extra_columns or "points" in extra_columns:
            table.add_column("Points", style="green", width=8)
        if not extra_columns or "files" in extra_columns:
            table.add_column("Files", width=6)

        for challenge in challenges:
            row = [
                self._get_challenge_status(challenge),
                challenge.id,
                challenge.name[:30] + "..." if len(challenge.name) > 30 else challenge.name,
            ]

            if not extra_columns or "category" in extra_columns:
                row.append(challenge.category.value)
            if not extra_columns or "difficulty" in extra_columns:
                row.append(self._get_difficulty_display(challenge.difficulty))
            if not extra_columns or "points" in extra_columns:
                row.append(str(challenge.points))
            if not extra_columns or "files" in extra_columns:
                row.append("📁" if challenge.files else "")

            table.add_row(*row)

        return table

    def load_challenges(self) -> None:
        """Load challenges dynamically."""
        self.console.print("🔍 [bold blue]Discovering challenges...[/bold blue]")

        loader = ChallengeLoader(self.config.base_path)
        sources = loader.discover_challenge_sources()

        # Show discovered sources
        sources_table = Table(title="Discovered Challenge Sources")
        sources_table.add_column("Source Type", style="cyan")
        sources_table.add_column("Count", style="green")
        sources_table.add_column("Paths", style="dim")

        for source_type, paths in sources.items():
            paths_str = "\n".join(str(p) for p in paths[:3])
            if len(paths) > 3:
                paths_str += f"\n... and {len(paths) - 3} more"
            sources_table.add_row(source_type, str(len(paths)), paths_str)

        self.console.print(sources_table)

        # Load challenges with progress bar
        self.challenges = []
        for source_type in track(self.config.challenge_sources, description="Loading challenges..."):
            if source_type in sources:
                challenges = loader.load_challenges_from_sources(
                    sources=[source_type],
                    include_patterns=self.config.include_patterns,
                    exclude_patterns=self.config.exclude_patterns
                )
                self.challenges.extend(challenges)

        # Build index
        self._challenge_index = {c.id: c for c in self.challenges}
        self.console.print(f"✅ [bold green]Loaded {len(self.challenges)} challenges[/bold green]")

    def start_interactive(self) -> None:
        """Start the interactive session."""
        self.console.print(Panel.fit(
            "🚩 [bold red]Welcome to Advanced picoCTF Environment CLI![/bold red]\n"
            "Type 'help' for commands or use Tab completion.",
            border_style="blue"
        ))

        if not self.challenges:
            self.console.print("❌ [red]No challenges loaded![/red]")
            return

        self.show_stats()

        while True:
            try:
                command = self.console.input("\n[bold cyan]ctf>[/bold cyan] ").strip()
                if not command:
                    continue

                if command.lower() in ['quit', 'exit', 'q']:
                    self.save_session_state()
                    self.console.print("👋 [yellow]Thanks for playing![/yellow]")
                    break

                self.handle_command(command)

            except KeyboardInterrupt:
                self.save_session_state()
                self.console.print("\n👋 [yellow]Session saved. Thanks for playing![/yellow]")
                break
            except Exception as e:
                self.console.print(f"❌ [red]Error: {e}[/red]")

    def handle_command(self, command: str) -> None:
        """Handle interactive commands using command registry."""
        parts = command.lower().split()
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        if cmd in self.commands:
            self.commands[cmd](args)
        else:
            self._show_error(f"Unknown command: {command}")
            self.console.print("Type 'help' for available commands")

    def show_help(self) -> None:
        """Show available commands with rich formatting."""
        help_table = Table(title="Available Commands", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        help_table.add_column("Example", style="dim")

        commands = [
            ("help, h, ?", "Show this help", "help"),
            ("list, ls", "List all challenges", "list"),
            ("select <id>", "Select a challenge by ID", "select crypto_001"),
            ("random, rand, r", "Select a random challenge", "random"),
            ("category <cat>", "List challenges by category", "category crypto"),
            ("difficulty <diff>", "List challenges by difficulty", "difficulty easy"),
            ("info, i", "Show current challenge details", "info"),
            ("hint, hints", "Show hints for current challenge", "hint"),
            ("submit <flag>", "Submit a flag", "submit picoCTF{...}"),
            ("files", "Show files for current challenge", "files"),
            ("env, environment", "Show environment info", "env"),
            ("stats, score", "Show your progress", "stats"),
            ("sources", "Show challenge sources", "sources"),
            ("reload", "Reload challenges", "reload"),
            ("quit, exit, q", "Exit the CLI", "quit"),
        ]

        for cmd, desc, example in commands:
            help_table.add_row(cmd, desc, example)

        self.console.print(help_table)

    def list_challenges(self) -> None:
        """List all challenges with rich table formatting."""
        table = self._create_challenge_table(self.challenges, "Available Challenges")
        self.console.print(table)

    def show_stats(self) -> None:
        """Show comprehensive statistics."""
        if not self.challenges:
            return

        total = len(self.challenges)
        solved = len(self.state.solved_challenges)
        completion_rate = (solved / total * 100) if total > 0 else 0

        # Main stats panel
        stats_text = f"""
[bold green]Total Score:[/bold green] {self.state.score}
[bold blue]Challenges Solved:[/bold blue] {solved}/{total} ({completion_rate:.1f}%)
[bold yellow]Current Challenge:[/bold yellow] {self.current_challenge.name if self.current_challenge else "None"}
        """

        self.console.print(Panel(stats_text.strip(), title="Your Progress", border_style="green"))

        # Category breakdown
        cat_stats = {}
        for challenge in self.challenges:
            cat = challenge.category
            if cat not in cat_stats:
                cat_stats[cat] = {"total": 0, "solved": 0, "points": 0}
            cat_stats[cat]["total"] += 1
            cat_stats[cat]["points"] += challenge.points
            if challenge.id in self.state.solved_challenges:
                cat_stats[cat]["solved"] += 1

        cat_table = Table(title="Progress by Category")
        cat_table.add_column("Category", style="magenta")
        cat_table.add_column("Solved/Total", style="green")
        cat_table.add_column("Completion", style="cyan")
        cat_table.add_column("Points", style="yellow")

        for cat, stats in cat_stats.items():
            completion = (stats["solved"] / stats["total"] * 100) if stats["total"] > 0 else 0
            cat_table.add_row(
                cat.value,
                f"{stats['solved']}/{stats['total']}",
                f"{completion:.1f}%",
                str(stats["points"])
            )

        self.console.print(cat_table)

    def show_sources(self) -> None:
        """Show information about challenge sources."""
        loader = ChallengeLoader(self.config.base_path)
        sources = loader.discover_challenge_sources()

        for source_type, paths in sources.items():
            self.console.print(f"\n[bold]{source_type.replace('_', ' ').title()}:[/bold]")
            for path in paths:
                self.console.print(f"  📁 {path}")

    def reload_challenges(self) -> None:
        """Reload challenges from sources."""
        self.console.print("🔄 [yellow]Reloading challenges...[/yellow]")
        self.load_challenges()
        self.console.print("✅ [green]Challenges reloaded![/green]")

    def select_challenge(self, challenge_id: str) -> None:
        """Select a challenge to work on."""
        challenge = self._challenge_index.get(challenge_id)
        if not challenge:
            self._show_error(f"Challenge not found: {challenge_id}")
            return

        self.current_challenge = challenge
        self.state.current_challenge_id = challenge_id
        if challenge_id not in self.state.attempts:
            self.state.attempts[challenge_id] = []

        self.console.print(f"🎯 [bold green]Selected challenge: {challenge.name}[/bold green]")
        self.show_current_challenge()

    def show_current_challenge(self) -> None:
        """Show detailed information about the current challenge."""
        if not self.current_challenge:
            self._show_error("No challenge selected")
            return

        c = self.current_challenge
        solved = "✅ SOLVED" if c.id in self.state.solved_challenges else "🎯 UNSOLVED"

        # Create challenge info panel
        info_text = f"""
[bold]ID:[/bold] {c.id}
[bold]Name:[/bold] {c.name}
[bold]Category:[/bold] {c.category.value}
[bold]Difficulty:[/bold] {c.difficulty.value}
[bold]Points:[/bold] {c.points}
[bold]Attempts:[/bold] {len(self.state.attempts.get(c.id, []))}

[bold]Description:[/bold]
{c.description}
        """

        if c.files:
            info_text += f"\n[bold]Files:[/bold] {', '.join(c.files)}"

        if c.environment:
            info_text += f"\n[bold]Environment:[/bold] Available"

        self.console.print(Panel(
            info_text.strip(),
            title=f"{solved} - {c.name}",
            border_style="green" if c.id in self.state.solved_challenges else "yellow"
        ))

    def show_hints(self) -> None:
        """Show hints for the current challenge."""
        if not self.current_challenge:
            self._show_error("No challenge selected")
            return

        hints = self.current_challenge.hints
        if not hints:
            self.console.print("💡 [yellow]No hints available for this challenge[/yellow]")
            return

        # Show hints progressively based on number of attempts
        attempts = self.state.attempts.get(self.current_challenge.id, [])
        hints_to_show = min(len(attempts) + 1, len(hints))

        hints_text = ""
        for i in range(hints_to_show):
            hints_text += f"💡 **Hint {i+1}:** {hints[i]}\n"

        if hints_to_show < len(hints):
            hints_text += f"\n🔒 *Make more attempts to unlock {len(hints) - hints_to_show} more hints*"

        self.console.print(Panel(
            hints_text.strip(),
            title=f"Hints ({hints_to_show}/{len(hints)} available)",
            border_style="yellow"
        ))

    def submit_flag(self, flag: str) -> None:
        """Submit a flag for the current challenge."""
        if not self.current_challenge:
            self._show_error("No challenge selected")
            return

        # Clean up the flag
        flag = flag.strip()
        if not flag:
            self._show_error("Empty flag submitted")
            return

        challenge_id = self.current_challenge.id
        if challenge_id not in self.state.attempts:
            self.state.attempts[challenge_id] = []

        self.state.attempts[challenge_id].append(flag)
        c = self.current_challenge

        # Check if correct
        if flag == c.flag:
            self.console.print("🎉 [bold green]CORRECT! Well done![/bold green]")
            if c.id not in self.state.solved_challenges:
                self.state.solved_challenges.add(c.id)
                self.state.score += c.points
                self.console.print(f"💰 [green]+{c.points} points! Total score: {self.state.score}[/green]")
            else:
                self.console.print("[yellow](Already solved - no additional points)[/yellow]")
            return

        # Check for common issues
        if flag.lower() == c.flag.lower():
            self.console.print("🔸 [yellow]Almost! Check the capitalization[/yellow]")
            return

        if not flag.startswith("picoCTF{"):
            self.console.print("🔸 [yellow]Remember: flags should start with 'picoCTF{'[/yellow]")
            return

        if not flag.endswith("}"):
            self.console.print("🔸 [yellow]Remember: flags should end with '}'[/yellow]")
            return

        self.console.print("❌ [red]Incorrect. Try again![/red]")

        # Show hints after a few attempts
        if len(self.state.attempts[challenge_id]) >= 2:
            self.console.print("💡 [dim]Type 'hint' if you need help[/dim]")

    def random_challenge(self) -> None:
        """Select a random challenge."""
        # Prefer unsolved challenges
        unsolved = [c for c in self.challenges if c.id not in self.state.solved_challenges]
        challenge = random.choice(unsolved if unsolved else self.challenges)

        self.current_challenge = challenge
        self.state.current_challenge_id = challenge.id
        if challenge.id not in self.state.attempts:
            self.state.attempts[challenge.id] = []

        self.console.print(f"🎲 [bold green]Random challenge: {challenge.name}[/bold green]")
        self.show_current_challenge()

    def list_by_category(self, category: str) -> None:
        """List challenges by category."""
        try:
            cat_enum = CategoryType(category.lower())
        except ValueError:
            self._show_error(f"Invalid category: {category}")
            self.console.print(f"Valid categories: {', '.join([c.value for c in CategoryType])}")
            return

        challenges = [c for c in self.challenges if c.category == cat_enum]
        if not challenges:
            self.console.print(f"[yellow]No challenges found in category: {category}[/yellow]")
            return

        table = self._create_challenge_table(
            challenges,
            f"{category.title()} Challenges",
            extra_columns=["difficulty", "points"]  # Exclude category since it's filtered
        )
        self.console.print(table)

    def list_by_difficulty(self, difficulty: str) -> None:
        """List challenges by difficulty."""
        try:
            diff_enum = DifficultyLevel(difficulty.lower())
        except ValueError:
            self._show_error(f"Invalid difficulty: {difficulty}")
            self.console.print(f"Valid difficulties: {', '.join([d.value for d in DifficultyLevel])}")
            return

        challenges = [c for c in self.challenges if c.difficulty == diff_enum]
        if not challenges:
            self.console.print(f"[yellow]No challenges found with difficulty: {difficulty}[/yellow]")
            return

        table = self._create_challenge_table(
            challenges,
            f"{difficulty.title()} Challenges",
            extra_columns=["category", "points"]  # Exclude difficulty since it's filtered
        )
        self.console.print(table)

    def show_files(self) -> None:
        """Show files for the current challenge."""
        if not self.current_challenge:
            self._show_error("No challenge selected")
            return

        if not self.current_challenge.files:
            self.console.print("📁 [yellow]No files for this challenge[/yellow]")
            return

        files_text = f"📁 **Files for {self.current_challenge.name}:**\n\n"

        base_path = self.current_challenge.source_path or self.config.base_path / "files"

        for filename in self.current_challenge.files:
            file_path = base_path / filename
            if file_path.exists():
                size = file_path.stat().st_size
                files_text += f"📄 **{filename}** ({size} bytes)\n"
                files_text += f"   Location: `{file_path}`\n"

                # Show file content preview for small text files
                if size < 1024 and filename.endswith(('.txt', '.md', '.py', '.js', '.html', '.json')):
                    try:
                        content = file_path.read_text(encoding='utf-8')[:200]
                        files_text += f"   Preview: {content}{'...' if len(content) == 200 else ''}\n"
                    except:
                        files_text += "   (Binary or unreadable content)\n"
            else:
                files_text += f"❌ **{filename}** (file not found)\n"
            files_text += "\n"

        self.console.print(Panel(
            files_text.strip(),
            title="Challenge Files",
            border_style="blue"
        ))

    def show_environment(self) -> None:
        """Show environment information for the current challenge."""
        if not self.current_challenge:
            self._show_error("No challenge selected")
            return

        if not self.current_challenge.environment:
            self.console.print("🔧 [yellow]No special environment configuration for this challenge[/yellow]")
            return

        env_text = f"🔧 **Environment for {self.current_challenge.name}:**\n\n"
        env = self.current_challenge.environment

        for key, value in env.items():
            env_text += f"**{key}:** {value}\n"

        self.console.print(Panel(
            env_text.strip(),
            title="Environment Configuration",
            border_style="green"
        ))

    def save_session_state(self) -> None:
        """Save session state to file."""
        if not self.config.session_file:
            return

        try:
            state_data = self.state.model_dump()
            with open(self.config.session_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            self.console.print(f"💾 [dim]Session saved to {self.config.session_file}[/dim]")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def load_session_state(self) -> None:
        """Load session state from file."""
        if not self.config.session_file:
            return

        try:
            with open(self.config.session_file, 'r') as f:
                state_data = json.load(f)
            self.state = SessionState(**state_data)
            self.console.print(f"📂 [dim]Session loaded from {self.config.session_file}[/dim]")
        except Exception as e:
            logger.error(f"Failed to load session: {e}")


def interactive_session(config: CLIConfig) -> None:
    """Start an interactive CTF session."""
    session = CTFSession(config)
    session.load_challenges()
    session.start_interactive()


def list_sources(config: CLIConfig) -> None:
    """List all available challenge sources."""
    console.print("🔍 [bold blue]Discovering challenge sources...[/bold blue]")
    loader = ChallengeLoader(config.base_path)
    sources = loader.discover_challenge_sources()

    for source_type, paths in sources.items():
        console.print(f"\n[bold]{source_type.replace('_', ' ').title()}:[/bold]")
        for path in paths:
            console.print(f"  📁 {path}")


def list_challenges(config: CLIConfig) -> None:
    """List all challenges without starting interactive mode."""
    challenges = load_challenges_dynamically(
        config.base_path,
        config.challenge_sources,
        config.include_patterns,
        config.exclude_patterns
    )

    table = Table(title=f"Available Challenges ({len(challenges)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Difficulty", style="yellow")
    table.add_column("Points", style="green")

    for challenge in challenges:
        table.add_row(
            challenge.id,
            challenge.name,
            challenge.category.value,
            challenge.difficulty.value,
            str(challenge.points)
        )

    console.print(table)


def admin_inspect(
    config: CLIConfig,
    challenge_id: Optional[str] = None,
    category: Optional[str] = None,
    show_files: bool = False,
    show_environment: bool = False
) -> None:
    """Admin command to inspect challenges and environments."""
    challenges = load_challenges_dynamically(
        config.base_path,
        config.challenge_sources,
        config.include_patterns,
        config.exclude_patterns
    )

    # Filter challenges based on criteria
    filtered_challenges = challenges

    if challenge_id:
        filtered_challenges = [c for c in challenges if c.id == challenge_id]
    elif category:
        filtered_challenges = [c for c in challenges if c.category.value == category]

    if not filtered_challenges:
        console.print("❌ [red]No challenges found matching criteria[/red]")
        return

    for challenge in filtered_challenges:
        console.print(f"\n[bold cyan]Challenge: {challenge.id}[/bold cyan]")
        console.print(f"Name: {challenge.name}")
        console.print(f"Category: {challenge.category.value}")
        console.print(f"Difficulty: {challenge.difficulty.value}")
        console.print(f"Points: {challenge.points}")
        console.print(f"Flag: {challenge.flag}")

        if show_files and challenge.files:
            console.print("Files:")
            for file in challenge.files:
                console.print(f"  📄 {file}")

        if show_environment and challenge.environment:
            console.print("Environment:")
            for key, value in challenge.environment.items():
                console.print(f"  {key}: {value}")

        if challenge.source_path:
            console.print(f"Source: {challenge.source_path}")


def main() -> None:
    """Main CLI entry point with tyro SubcommandApp."""

    def interactive(
        challenge_id: Optional[str] = None,
        path: Path = Path("."),
        sources: str = "picoctf_problems,json_datasets",
        session: Optional[Path] = None,
        verbose: bool = False
    ) -> None:
        """Start interactive CTF session, optionally starting with a specific challenge."""
        log_level = "DEBUG" if verbose else "WARNING"
        config = CLIConfig(
            base_path=path,
            challenge_sources=sources.split(","),
            session_file=session,
            log_level=log_level  # type: ignore
        )

        session_obj = CTFSession(config)
        session_obj.load_challenges()

        # If challenge_id is provided, select it automatically
        if challenge_id:
            session_obj.select_challenge(challenge_id)

        session_obj.start_interactive()

    def sources_cmd(path: Path = Path(".")) -> None:
        """List challenge sources."""
        config = CLIConfig(base_path=path)
        list_sources(config)

    def list_cmd(
        path: Path = Path("."),
        sources: str = "picoctf_problems,json_datasets",
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> None:
        """List challenges."""
        config = CLIConfig(
            base_path=path,
            challenge_sources=sources.split(",")
        )

        # Load challenges once
        challenges = load_challenges_dynamically(
            config.base_path,
            config.challenge_sources,
            config.include_patterns,
            config.exclude_patterns
        )

        # Apply filters
        if category:
            try:
                cat_enum = CategoryType(category.lower())
                challenges = [c for c in challenges if c.category == cat_enum]
            except ValueError:
                console.print(f"❌ Invalid category: {category}")
                return

        if difficulty:
            try:
                diff_enum = DifficultyLevel(difficulty.lower())
                challenges = [c for c in challenges if c.difficulty == diff_enum]
            except ValueError:
                console.print(f"❌ Invalid difficulty: {difficulty}")
                return

        # Display table
        table = Table(title=f"Challenges ({len(challenges)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Cat", style="magenta", width=8)
        table.add_column("Diff", style="yellow", width=6)
        table.add_column("Pts", style="green", width=5)

        for challenge in challenges:
            table.add_row(
                challenge.id,
                challenge.name[:40] + "..." if len(challenge.name) > 40 else challenge.name,
                challenge.category.value[:8],
                challenge.difficulty.value[:4],
                str(challenge.points)
            )

        console.print(table)

    def inspect_cmd(
        challenge_id: str,
        path: Path = Path("."),
        sources: str = "picoctf_problems,json_datasets",
        files: bool = False,
        env: bool = False,
        all: bool = False
    ) -> None:
        """Inspect a challenge."""
        if all:
            files = env = True

        config = CLIConfig(
            base_path=path,
            challenge_sources=sources.split(",")
        )
        admin_inspect(config, challenge_id, None, files, env)

    def stats_cmd(
        path: Path = Path("."),
        session: Optional[Path] = None
    ) -> None:
        """Show challenge statistics."""
        config = CLIConfig(base_path=path, session_file=session)

        # Load session if exists
        if session and session.exists():
            try:
                with open(session, 'r') as f:
                    state_data = json.load(f)
                state = SessionState(**state_data)
            except:
                state = SessionState()
        else:
            state = SessionState()

        # Load challenges
        challenges = load_challenges_dynamically(
            config.base_path,
            config.challenge_sources,
            config.include_patterns,
            config.exclude_patterns
        )

        # Calculate stats
        total = len(challenges)
        solved = len(state.solved_challenges)
        completion = (solved / total * 100) if total > 0 else 0

        # Show stats
        stats_text = f"""
[bold green]Score:[/bold green] {state.score}
[bold blue]Solved:[/bold blue] {solved}/{total} ({completion:.1f}%)
        """

        console.print(Panel(stats_text.strip(), title="Stats", border_style="green"))

    # Dictionary-based alias system for cleaner code
    aliases = {
        # Interactive aliases
        "i": interactive,
        "shell": interactive,

        # List aliases
        "ls": list_cmd,
        "l": list_cmd,

        # Sources aliases
        "src": sources_cmd,

        # Inspect aliases
        "info": inspect_cmd,
        "show": inspect_cmd,
        "cat": inspect_cmd,

        # Stats aliases
        "st": stats_cmd,
        "status": stats_cmd,
        # Quick aliases
        # "data": ctf_dataset_main.cli,
        "data" : ctf_dataset_main._subcommands.copy()
    }

    # Check if no arguments are provided and default to interactive
    if len(sys.argv) == 1:
        interactive()
        return
    # subcommand_cli_from_dict(aliases)
    subcommand_cli_from_nested_dict(aliases)


if __name__ == "__main__":
    main()