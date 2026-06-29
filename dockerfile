# ── Base image
# python:3.11-slim = official Python 3.11 on minimal Debian.
# Slim has no extras (no curl, no gcc preinstalled beyond what pip needs).
# We pin to 3.11 explicitly — "latest" can silently break builds months from now.
FROM python:3.11-slim

# ── Suppress Python noise inside containers
# PYTHONDONTWRITEBYTECODE: don't create .pyc files — irrelevant in a container
# PYTHONUNBUFFERED: print() and logging output appears in docker logs immediately,
# not held in a buffer. Critical for seeing bot startup messages.
ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

# ── Working directory
# All subsequent COPY, RUN, CMD instructions operate relative to /app.
# Docker creates this directory if it doesn't exist.
WORKDIR /app

# ── Install system dependencies
# sentence-transformers and torch need these C libraries to compile correctly.
# --no-install-recommends keeps the image lean.
# We clean up the apt cache in the same RUN layer to avoid bloating the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies (cached layer)
# Copy requirements.txt FIRST, before any source code.
# Docker only re-runs this layer when requirements.txt changes.
# If you change bot/telegram_bot.py but not requirements.txt,
# Docker reuses this cached layer — pip install takes ~0 seconds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy source code (invalidated on any code change)
# This layer comes AFTER pip install intentionally.
# Changing your Python files only invalidates from here downward.
COPY src/ ./src/

# ── Startup command
# Equivalent to: cd /app && python -m bot.telegram_bot
# CMD is not a build step — it runs when a container starts.
# Using the list form (not a string) avoids a shell wrapper process.
CMD ["python3", "src/bot/telegram_bot.py"]