FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js, npm, mcp-proxy, and Python via uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g mcp-proxy@5.12.0 \
    && node --version \
    && curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="/usr/local/bin" sh \
    && uv python install 3.10 --default --preview \
    && ln -s $(uv python find) /usr/local/bin/python \
    && python --version \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN uv sync

# Environment variables (set at runtime)
# GAM_CREDENTIALS_PATH: Path to service account JSON
# GAM_NETWORK_CODE: Your Google Ad Manager network code

EXPOSE 8080

# Run via mcp-proxy with shell mode to properly handle uv
CMD ["mcp-proxy", "--shell", "uv run python -m gam_mcp.server"]
