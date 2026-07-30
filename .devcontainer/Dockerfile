# Open Bus hackathon devcontainer — Python 3.12 + Node (via feature) + Jupyter.
#
# Python 3.12 rather than 3.14: reliable wheels for the whole scientific stack.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image ships a yarn apt source (dl.yarnpkg.com) with no matching
# GPG key, which makes `apt-get update` fail outright. We install Node via a
# devcontainer feature, not apt, so drop the broken source instead of fixing it.
RUN rm -f /etc/apt/sources.list.d/yarn.list

# Hebrew glyphs. Agency names come back as Hebrew, so without these fonts every
# chart label renders as empty boxes. Debian has no standalone "fonts-noto-hebrew"
# package — NotoSansHebrew/NotoSerifHebrew ship inside fonts-noto-core. This is the
# only apt package we need.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends fonts-noto-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv: fast, lockfile-based Python env management.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Keep the venv OUT of the bind-mounted workspace: faster, and it can't clash
# with a host-side venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/home/vscode/.cache/matplotlib

# Pre-create the mount points with the right owner. A fresh Docker named volume
# inherits the ownership of the image path it covers — if ~/.claude doesn't exist
# here, the volume mounts as root and Claude Code (or gh) can't write its credentials.
RUN mkdir -p /opt/venv /home/vscode/.cache/matplotlib /home/vscode/.claude /home/vscode/.config/gh \
    && chown -R vscode:vscode /opt/venv /home/vscode/.cache /home/vscode/.claude /home/vscode/.config
