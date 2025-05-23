#!/bin/bash
# CTF Environment Setup Script

set -e  # Exit on any error

echo "🚀 CTF Environment Setup"
echo "======================="

# Check if we're on Ubuntu (remote SSH as per user info)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PACKAGE_MANAGER="apt"
else
    echo "❌ This script is designed for Ubuntu/Debian systems"
    exit 1
fi

# Function to install system dependencies
install_system_deps() {
    echo "📦 Installing system dependencies..."
    sudo apt update
    sudo apt install -y \
        build-essential \
        curl \
        git \
        python3 \
        python3-pip \
        python3-venv \
        docker.io \
        docker-compose \
        gdb \
        binutils \
        hexdump \
        xxd \
        file \
        strings \
        openssl \
        netcat-openbsd \
        jq \
        zip \
        unzip
}

# Function to install uv
install_uv() {
    echo "⚡ Installing uv package manager..."
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
}

# Function to setup local environment
setup_local() {
    echo "🏠 Setting up local environment..."
    install_uv

    # Create virtual environment and install dependencies
    uv sync

    # Create directories
    mkdir -p env/{dataset,challenges,writeups,tools}

    echo "✅ Local setup complete!"
    echo "Run: uv run python ctf_cli.py"
}

# Function to setup Docker environment
setup_docker() {
    echo "🐳 Setting up Docker environment..."

    # Add user to docker group if not already
    if ! groups | grep -q docker; then
        sudo usermod -aG docker $USER
        echo "⚠️  Added you to docker group. Please log out and back in, then re-run this script."
        exit 0
    fi

    # Build and start containers
    docker-compose build

    echo "✅ Docker setup complete!"
    echo "Run: docker-compose run --rm ctf-dev"
}

# Main menu
echo "Choose your setup approach:"
echo "  l) Local development (lightweight, current system)"
echo "  d) Docker environment (full Ubuntu 22.04 with CTF tools)"
echo "  b) Both (recommended)"

read -p "Your choice [l/d/b]: " choice

case $choice in
    l|L)
        setup_local
        ;;
    d|D)
        install_system_deps
        setup_docker
        ;;
    b|B)
        install_system_deps
        setup_local
        setup_docker
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Setup complete! Here's how to use your environment:"
echo ""
echo "📋 Available Commands:"
echo "  Local:  uv run python ctf_cli.py"
echo "  Docker: docker-compose run --rm ctf-dev"
echo "  Test:   docker-compose run --rm ctf-test"
echo ""
echo "📂 Project Structure:"
echo "  env/dataset/     - Challenge data"
echo "  env/challenges/  - Your challenge solutions"
echo "  env/writeups/    - Documentation"
echo "  env/tools/       - Custom tools"
echo ""
echo "🚀 Ready to start hacking!"