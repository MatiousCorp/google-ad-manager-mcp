FROM python:3.11-slim

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy project files needed for installation
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies as root (required for pip install)
RUN pip install --no-cache-dir .

# Set ownership of app directory to non-root user
RUN chown -R appuser:appgroup /app

# Environment variables (required - must be set at runtime)
# GAM_CREDENTIALS_PATH: Path to service account JSON (default: /app/credentials.json if mounting)
# GAM_NETWORK_CODE: Your Google Ad Manager network code (REQUIRED)
# GAM_MCP_TRANSPORT: Transport mode - "stdio" or "http" (default: http)
# GAM_MCP_AUTH_TOKEN: Authentication token for HTTP mode (generate with: python -c "import secrets; print(secrets.token_hex(32))")
ENV GAM_CREDENTIALS_PATH=/app/credentials.json
ENV GAM_MCP_TRANSPORT=stdio
ENV GAM_MCP_HOST=0.0.0.0
ENV GAM_MCP_PORT=8000

# Switch to non-root user
USER appuser

EXPOSE 8000

# Run the server
CMD ["python", "-m", "gam_mcp.server"]
