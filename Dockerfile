FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies and CTF tools
RUN apt-get update && apt-get install -y \
    # Basic development tools
    build-essential \
    curl \
    git \
    vim \
    nano \
    wget \
    unzip \
    sudo \
    # Python and development
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # CTF and security tools
    gdb \
    strace \
    ltrace \
    binutils \
    hexdump \
    xxd \
    file \
    strings \
    objdump \
    readelf \
    nm \
    # Crypto and encoding tools
    openssl \
    gpg \
    # Network tools
    netcat-openbsd \
    nmap \
    tcpdump \
    # Text processing
    jq \
    grep \
    sed \
    awk \
    # Archive tools
    zip \
    unrar \
    p7zip-full \
    # Additional CTF tools
    steghide \
    exiftool \
    foremost \
    binwalk \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Create working directory
WORKDIR /workspace

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY README.md ./

# Install Python dependencies
RUN uv sync

# Create directories for CTF work
RUN mkdir -p /workspace/env/{dataset,challenges,writeups,tools}

# Set up environment
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONPATH="/workspace:$PYTHONPATH"

# Default command
CMD ["bash"]
