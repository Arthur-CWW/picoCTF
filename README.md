# picoCTF RL Environment

A minimal, type-safe CTF environment designed for LLM training with [verl](https://github.com/volcengine/verl).

## Quick Start

### 1. Setup with uv

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone/navigate to your project
cd picoCTF

# Install the package in development mode
uv pip install -e .

# Or install with specific extras
uv pip install -e ".[dev,server]"
```

### 2. Test the Environment

```bash
# Start the interactive CLI to play around
uv run ctf-cli

# Or run it directly
python ctf_cli.py
```

### 3. Interactive CLI Commands

Once you start `ctf-cli`, you'll see:

```
🚩 Welcome to picoCTF RL Environment CLI!
==================================================
Loaded 5 challenges
Categories: general, crypto, forensics
Difficulties: easy, medium

ctf> help
```

**Available Commands:**
- `list` - Show all challenges
- `select <id>` - Select a challenge (e.g., `select basic_flag_001`)
- `random` - Pick a random challenge
- `info` - Show current challenge details
- `submit <flag>` - Submit your answer (e.g., `submit picoCTF{hello}`)
- `hint` - Get progressive hints
- `stats` - Show your progress
- `quit` - Exit

### 4. Example Session

```bash
ctf> list
📋 Available Challenges:
----------------------------------------------------------

🏷️  GENERAL:
  ⭕ 🟢 basic_flag_001   - Find the Flag (50pts)
  ⭕ 🟢 base64_001       - Base64 Decode (75pts)

🏷️  CRYPTO:
  ⭕ 🟢 caesar_001       - Caesar Cipher (100pts)
  ⭕ 🟡 xor_001          - Single Byte XOR (150pts)

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

ctf> random
🎲 Random challenge: Caesar Cipher
# ... and so on
```

## Project Structure

```
picoCTF/
├── ctf_dataset.py      # Dataset management with type safety
├── ctf_cli.py          # Interactive CLI for testing
├── pyproject.toml      # Package configuration with uv
├── dataset/            # Challenge data
│   ├── challenges.json # Challenge definitions
│   └── files/          # Challenge files
└── README.md           # This file
```

## Features

✅ **Type-safe**: Comprehensive type annotations with mypy support
✅ **Interactive CLI**: Test challenges immediately
✅ **Multiple categories**: crypto, general, forensics, web, binary, reverse
✅ **Progressive hints**: Unlock hints as you make attempts
✅ **Score tracking**: Points and progress tracking
✅ **verl integration**: Export datasets for RL training
✅ **Minimal dependencies**: Easy docker deployment

## Dataset Management

### Create Custom Dataset

```python
from ctf_dataset import CTFDataset, CTFChallenge, DifficultyLevel

# Create a challenge
challenge = CTFChallenge(
    id="my_challenge_001",
    name="My Custom Challenge",
    category="crypto",
    difficulty=DifficultyLevel.EASY,
    description="Solve this puzzle...",
    flag="picoCTF{my_flag}",
    hints=["Try this approach", "Look for patterns"],
    points=100
)

# Save to dataset
dataset = CTFDataset()
# Add your challenges and export
dataset.export_for_verl("my_dataset.json")
```

### Convert Existing picoCTF Challenges

```bash
# Convert original picoCTF problems
uv run ctf-dataset convert /path/to/picoCTF/problems ./dataset

# Or use the function directly
python -c "from ctf_dataset import convert_picoctf_to_dataset; convert_picoctf_to_dataset('problems/', 'dataset/')"
```

## verl Integration

Export your dataset for training with [verl](https://github.com/volcengine/verl):

```python
from ctf_dataset import CTFDataset

dataset = CTFDataset()
dataset.export_for_verl("ctf_training_data.json")
```

This creates a JSON file compatible with verl's training pipeline:

```json
[
  {
    "instruction": "Solve this crypto challenge: Decrypt this Caesar cipher...",
    "input": "",
    "output": "picoCTF{correct_flag}",
    "challenge_id": "caesar_001",
    "category": "crypto",
    "difficulty": "easy",
    "points": 100,
    "hints": ["Try ROT13", "Caesar cipher with shift 13"]
  }
]
```

## Development

### Setup Development Environment

```bash
# Install with all development dependencies
uv pip install -e ".[dev]"

# Run type checking
uv run mypy .

# Format code
uv run black .
uv run isort .

# Run tests
uv run pytest
```

### Docker Usage

```bash
# Build minimal container
docker build -t ctf-env .

# Run CLI in container
docker run -it ctf-env ctf-cli

# Run as a service
docker run -p 8000:8000 ctf-env ctf-server
```

## Examples

### Quick Test Drive

```bash
# 1. Install and run
uv pip install -e .
uv run ctf-cli

# 2. Try the built-in challenges
ctf> random
ctf> info
ctf> hint
ctf> submit picoCTF{your_answer}
```

### Integration with verl

```python
# train_with_verl.py
from ctf_dataset import CTFDataset

# Load and export dataset
dataset = CTFDataset()
dataset.export_for_verl("ctf_data.json")

# Use with verl training pipeline
# (verl integration code would go here)
```

## Contributing

1. Fork the repository
2. Install development dependencies: `uv pip install -e ".[dev]"`
3. Make your changes with proper type annotations
4. Run tests and type checking: `uv run mypy . && uv run pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Ready to test?** Run `uv run ctf-cli` and start solving challenges! 🚩
