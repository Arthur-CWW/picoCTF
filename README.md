# CTF Environment & Dataset Manager

A clean, type-safe CTF environment for testing and managing cybersecurity challenges. Focused on dataset management and interactive testing with Docker support.

## Quick Start

### 1. Using the Setup Script (Recommended)

```bash
# Run the interactive setup
./setup-dev.sh

# Choose your option:
# l) Local development (lightweight)
# d) Docker environment (full Ubuntu 22.04 + CTF tools)
# b) Both (recommended)
```

### 2. Manual Local Setup

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Test the environment
uv run python -m src.ctf_cli
```

### 3. Docker Environment

```bash
# Build and run full environment
docker-compose up -d ctf-dev
docker-compose exec ctf-dev bash

# Or test specific components
docker-compose run --rm ctf-cli      # Run CLI
docker-compose run --rm ctf-dataset  # Test dataset
```

## Project Structure

```
picoCTF/
├── src/                    # Main source code
│   ├── ctf_dataset.py     # Dataset management
│   ├── ctf_cli.py         # Interactive CLI
│   └── __init__.py        # Package definition
├── env/                   # Environment data (persisted)
│   ├── dataset/          # Challenge data
│   ├── challenges/       # Your solutions
│   ├── writeups/         # Documentation
│   └── tools/            # Custom tools
├── docker-compose.yml    # Container orchestration
├── Dockerfile           # Ubuntu 22.04 + CTF tools
├── pyproject.toml       # Package configuration
└── setup-dev.sh         # Interactive setup
```

## Interactive CLI Usage

Start the CLI and explore challenges:

```bash
uv run python -m src.ctf_cli
```

### Available Commands

```
🚩 Welcome to picoCTF Environment CLI!

ctf> help                    # Show all commands
ctf> list                    # List all challenges
ctf> select basic_flag_001   # Select a challenge
ctf> info                    # Show challenge details
ctf> hint                    # Get progressive hints
ctf> submit picoCTF{flag}    # Submit your solution
ctf> files                   # Show challenge files
ctf> stats                   # Your progress
ctf> random                  # Random challenge
ctf> category crypto         # Filter by category
ctf> quit                    # Exit
```

### Example Session

```bash
ctf> list
📋 Available Challenges:
------------------------------------------------------------

🏷️  GENERAL:
  ⭕ 🟢    basic_flag_001  - Find the Flag (50pts)
  ⭕ 🟢    base64_001      - Base64 Decode (75pts)

🏷️  CRYPTO:
  ⭕ 🟢    caesar_001      - Caesar Cipher (100pts)
  ⭕ 🟡    xor_001         - Single Byte XOR (150pts)

ctf> select basic_flag_001
🎯 Selected challenge: Find the Flag

🎯 UNSOLVED
==================================================
🏷️  ID: basic_flag_001
📝 Name: Find the Flag
📂 Category: general
🟢 Difficulty: easy
💰 Points: 50
🔄 Attempts: 0

📖 Description:
   The flag is right here: picoCTF{welcome_to_ctf}

💡 Use 'hint' for hints, 'submit <flag>' to submit a solution

ctf> submit picoCTF{welcome_to_ctf}
🎉 CORRECT! Well done!
💰 +50 points! Total score: 50
```

## Dataset Management

### Working with Datasets

```python
from src.ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel

# Load dataset
dataset = CTFDataset()

# Get statistics
stats = dataset.get_dataset_stats()
print(f"Total challenges: {stats.total_challenges}")

# Filter challenges
crypto_challenges = dataset.get_challenges_by_category("crypto")
easy_challenges = dataset.get_challenges_by_difficulty(DifficultyLevel.EASY)

# Random selection
random_challenge = dataset.get_random_challenge(category="crypto")

# Export dataset
dataset.export_dataset("my_dataset.json")
```

### Converting picoCTF Problems

```bash
# Convert original picoCTF problems to our format
uv run python -m src.ctf_dataset convert problems/ env/dataset/

# Or programmatically
python -c "
from src.ctf_dataset import convert_picoctf_to_dataset
convert_picoctf_to_dataset('problems/', 'env/dataset/')
"
```

## Development Environments

### Local Development (Lightweight)

Best for quick testing and development:

```bash
# Install and run
uv sync
uv run python -m src.ctf_cli

# Benefits:
# - Fast startup
# - Uses your existing system
# - Minimal resource usage
```

### Docker Environment (Full CTF Suite)

Ubuntu 22.04 with comprehensive CTF tools:

```bash
# Build and enter environment
docker-compose run --rm ctf-dev

# Available tools:
# - gdb, objdump, readelf, strings
# - openssl, gpg, base64
# - steghide, exiftool, binwalk
# - netcat, nmap, tcpdump
# - And much more...
```

### Container Services

```bash
# Interactive development
docker-compose exec ctf-dev bash

# Test CLI
docker-compose run --rm ctf-cli

# Dataset operations
docker-compose run --rm ctf-dataset

# All services
docker-compose up -d
```

## Features

✅ **Clean Structure**: Organized `src/` folder, persistent `env/` data
✅ **Type Safe**: Full type annotations with mypy support
✅ **Interactive CLI**: Test challenges immediately
✅ **Docker Ready**: Full Ubuntu 22.04 environment with CTF tools
✅ **Dataset Management**: Load, filter, export challenge data
✅ **File Handling**: Challenge files and environment configs
✅ **Progress Tracking**: Scoring and completion tracking
✅ **Minimal Dependencies**: Easy deployment and distribution

## Environment Structure

The `env/` directory persists your work across containers:

```
env/
├── dataset/            # Challenge definitions and files
│   ├── challenges.json # Challenge metadata
│   └── files/         # Challenge files (binaries, texts, etc.)
├── challenges/        # Your solution scripts
├── writeups/          # Documentation and writeups
└── tools/            # Custom tools and utilities
```

## Available Tools (Docker Environment)

### Analysis & Debugging
- `gdb` - GNU Debugger
- `strace`/`ltrace` - System/library call tracing
- `objdump`, `readelf`, `nm` - Binary analysis
- `strings`, `hexdump`, `xxd` - Data examination

### Cryptography & Encoding
- `openssl` - Crypto operations
- `gpg` - PGP operations
- Base64, hex utilities

### Forensics & Steganography
- `steghide` - Steganography tool
- `exiftool` - Metadata extraction
- `binwalk` - Firmware analysis
- `foremost` - File carving

### Network & Web
- `netcat` - Network utility
- `nmap` - Network mapping
- `tcpdump` - Packet capture

## Usage Examples

### Quick Test Drive

```bash
# 1. Setup
./setup-dev.sh  # Choose 'l' for local

# 2. Start CLI
uv run python -m src.ctf_cli

# 3. Try a challenge
ctf> random
ctf> info
ctf> hint
ctf> submit picoCTF{your_answer}
```

### Docker Workflow

```bash
# 1. Build environment
docker-compose build

# 2. Start development
docker-compose run --rm ctf-dev

# 3. Inside container
root@container:/workspace# ctf-cli
ctf> list
ctf> select caesar_001
# ... work on challenge with full tool suite
```

### Dataset Operations

```bash
# View dataset info
uv run python -m src.ctf_dataset

# Convert picoCTF problems
uv run python -m src.ctf_dataset convert problems/ env/dataset/

# Custom dataset creation
python3 -c "
from src.ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel
dataset = CTFDataset()
# ... add custom challenges
dataset.export_dataset('my_ctf.json')
"
```

## Development

### Local Development Setup

```bash
# Install with dev dependencies
uv sync --extra dev

# Run type checking
uv run mypy src/

# Format code
uv run black src/
uv run isort src/

# Run tests (when available)
uv run pytest
```

### Adding New Challenges

Create challenges by adding to `env/dataset/challenges.json`:

```json
{
  "challenges": [
    {
      "id": "my_challenge_001",
      "name": "My Custom Challenge",
      "category": "crypto",
      "difficulty": "easy",
      "description": "Solve this puzzle...",
      "flag": "picoCTF{my_solution}",
      "hints": ["Try this approach"],
      "points": 100,
      "files": ["challenge.txt"],
      "environment": {
        "server": "example.com",
        "port": 1337
      }
    }
  ]
}
```

## Troubleshooting

### uv Issues
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache and resync
rm -rf .venv uv.lock
uv sync
```

### Docker Issues
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache

# Check logs
docker-compose logs ctf-dev
```

### Module Import Issues
```bash
# Make sure PYTHONPATH is set
export PYTHONPATH="/path/to/picoCTF:$PYTHONPATH"

# Or use module syntax
python -m src.ctf_cli
```

## Contributing

1. Fork the repository
2. Install development dependencies: `uv sync --extra dev`
3. Make your changes with proper type annotations
4. Run type checking: `uv run mypy src/`
5. Test your changes: `uv run python -m src.ctf_cli`
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Ready to hack?** Run `./setup-dev.sh` to get started! 🚩
