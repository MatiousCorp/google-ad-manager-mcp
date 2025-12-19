# Google Ad Manager MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

> **Automate Google Ad Manager with AI.** An MCP server that lets AI assistants like Claude, ChatGPT, Gemini, Cursor, and VS Code manage your ad campaigns, line items, creatives, and more through natural language.

<p align="center">
  <strong>Built by <a href="https://matious.com">Matious</a></strong> — We build custom AI tools and MCP servers for businesses.
</p>

---

## Why This Exists

Managing Google Ad Manager is tedious. Creating campaigns, uploading creatives, and configuring line items involves countless clicks through a complex UI.

**This MCP server changes that.** Connect it to Claude and manage your entire ad operations through conversation:

- *"Create a new campaign for Nike ending December 31st"*
- *"Upload all creatives from this folder and associate them with the Display line item"*
- *"Check which orders are currently delivering"*

No more clicking. Just tell Claude what you need.

## Features

- **Order Management**: List, create, and manage orders
- **Line Item Management**: Create, duplicate, and configure line items
- **Creative Management**: Upload images, associate with line items, bulk upload
- **Advertiser Management**: Find, create, and list advertisers
- **Verification Tools**: Verify line item setup, check delivery status
- **Campaign Workflow**: Complete campaign creation in one operation

## Installation

```bash
cd google-ad-manager-mcp
pip install -e .
```

Or with uv:

```bash
cd google-ad-manager-mcp
uv pip install -e .
```

### Dependencies

- **[FastMCP](https://github.com/jlowin/fastmcp)**: MCP server framework with native middleware support
- **[googleads](https://github.com/googleads/googleads-python-lib)**: Google Ad Manager SOAP API client

## Configuration

The server uses environment variables for configuration:

| Variable | Description | Required |
|----------|-------------|----------|
| `GAM_CREDENTIALS_PATH` | Path to service account JSON | **Yes** |
| `GAM_NETWORK_CODE` | Ad Manager network code | **Yes** |
| `GAM_MCP_TRANSPORT` | Transport mode: `stdio` or `http` | No (default: `stdio` in Docker, `http` otherwise) |
| `GAM_MCP_HOST` | Server host (HTTP mode only) | No (default: `0.0.0.0`) |
| `GAM_MCP_PORT` | Server port (HTTP mode only) | No (default: `8000`) |
| `GAM_MCP_AUTH_TOKEN` | Authentication token (HTTP mode only) | No (auto-generated if not set) |

## Authentication

The server implements Bearer token authentication using [FastMCP native middleware](https://gofastmcp.com/python-sdk/fastmcp-server-auth-auth), following [MCP security best practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices).

### Security Features

- **FastMCP Native Middleware**: Uses FastMCP 2.x middleware for proper MCP lifecycle management
- **Cryptographically secure tokens**: Generated using `secrets.token_hex(32)`
- **Timing attack prevention**: Uses constant-time comparison (`hmac.compare_digest`)
- **Tool-level authentication**: Auth validated on every tool call
- **Audit logging**: All authentication failures logged

### How It Works

Authentication is enforced at the tool level using FastMCP's middleware system:
- When a tool is called, the middleware validates the `Authorization` header
- If no token is configured (`GAM_MCP_AUTH_TOKEN` not set), requests are allowed
- Invalid or missing tokens return a `ToolError` with a helpful message

### Setup

For remote deployments, set a fixed authentication token:

```bash
# Generate a secure token
python -c "import secrets; print(secrets.token_hex(32))"

# Set it as environment variable
export GAM_MCP_AUTH_TOKEN="your-generated-token"
```

If not set, a random token is generated at startup and displayed in the logs.

Clients must include the token in the Authorization header:
```
Authorization: Bearer your-generated-token
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `/mcp` | MCP protocol endpoint (auth validated on tool calls) |

## Running the Server

### Local Development

```bash
# Using the installed command
gam-mcp

# Or directly with Python
python -m gam_mcp.server

# With custom configuration
GAM_NETWORK_CODE=12345678 GAM_MCP_PORT=9000 gam-mcp
```

### Docker Deployment

The Docker image runs as a non-root user (`appuser`) for security.

#### Build the Image

```bash
docker build -t google-ad-manager-mcp .
```

#### Run the Container

```bash
# Basic usage with credentials mounted
docker run -d \
  --name gam-mcp \
  -p 8000:8000 \
  -v /path/to/your/credentials.json:/app/credentials.json:ro \
  -e GAM_NETWORK_CODE=YOUR_NETWORK_CODE \
  google-ad-manager-mcp

# With authentication token (recommended for production)
docker run -d \
  --name gam-mcp \
  -p 8000:8000 \
  -v /path/to/your/credentials.json:/app/credentials.json:ro \
  -e GAM_NETWORK_CODE=YOUR_NETWORK_CODE \
  -e GAM_MCP_AUTH_TOKEN=$(python -c "import secrets; print(secrets.token_hex(32))") \
  google-ad-manager-mcp

# With custom port
docker run -d \
  --name gam-mcp \
  -p 9000:8000 \
  -v /path/to/your/credentials.json:/app/credentials.json:ro \
  -e GAM_NETWORK_CODE=YOUR_NETWORK_CODE \
  -e GAM_MCP_PORT=8000 \
  google-ad-manager-mcp
```

#### View Logs

```bash
# View startup logs (includes generated auth token if not set)
docker logs gam-mcp

# Follow logs
docker logs -f gam-mcp
```

#### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  gam-mcp:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./credentials.json:/app/credentials.json:ro
    environment:
      - GAM_NETWORK_CODE=YOUR_NETWORK_CODE
      - GAM_MCP_AUTH_TOKEN=your-secure-token
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

#### Verify the Container

```bash
# Check container is running
docker ps

# Test the endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}'
```

### Cloud Deployment (Railway, Fly.io, etc.)

1. Set environment variables in your cloud provider:
   - `GAM_CREDENTIALS_PATH`: Path to credentials (or use secrets)
   - `GAM_NETWORK_CODE`: Your Ad Manager network code
   - `GAM_MCP_AUTH_TOKEN`: A secure authentication token

2. Deploy using the included Dockerfile

## Connecting to AI Assistants

### Claude Desktop (Docker - Recommended)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-ad-manager": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GAM_NETWORK_CODE",
        "-v", "/path/to/credentials.json:/app/credentials.json:ro",
        "google-ad-manager-mcp"
      ],
      "env": {
        "GAM_NETWORK_CODE": "YOUR_NETWORK_CODE"
      }
    }
  }
}
```

### Claude Desktop (HTTP Mode)

If running the server in HTTP mode:

```json
{
  "mcpServers": {
    "google-ad-manager": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Remote Server with Authentication

If deploying remotely with authentication enabled:

```json
{
  "mcpServers": {
    "google-ad-manager": {
      "url": "https://your-server.com/mcp",
      "headers": {
        "Authorization": "Bearer your-secure-token"
      }
    }
  }
}
```

### Other MCP Clients

This server works with any MCP-compatible client, including:

- **ChatGPT Desktop** - OpenAI adopted MCP in March 2025
- **Cursor** - AI-powered IDE with MCP support
- **VS Code** - Via MCP extensions
- **Windsurf, Zed, Codeium** - Various IDE integrations

Refer to each client's documentation for MCP server configuration.

### Testing with MCP Inspector

```bash
# Without authentication
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# With authentication (set header in Inspector UI)
# Header: Authorization
# Value: Bearer your-token
```

## Available Tools

### Order Tools

| Tool | Description |
|------|-------------|
| `list_delivering_orders` | List all orders with delivering line items |
| `get_order` | Get order details by ID or name |
| `create_order` | Create a new order |
| `find_or_create_order` | Find existing or create new order |

### Line Item Tools

| Tool | Description |
|------|-------------|
| `get_line_item` | Get line item details |
| `create_line_item` | Create a new line item |
| `duplicate_line_item` | Duplicate an existing line item |
| `update_line_item_name` | Rename a line item |
| `list_line_items_by_order` | List all line items for an order |

### Creative Tools

| Tool | Description |
|------|-------------|
| `upload_creative` | Upload an image creative |
| `associate_creative_with_line_item` | Associate creative with line item |
| `upload_and_associate_creative` | Upload and associate in one step |
| `bulk_upload_creatives` | Upload all creatives from a folder |
| `get_creative` | Get creative details |
| `list_creatives_by_advertiser` | List creatives for an advertiser |

### Advertiser Tools

| Tool | Description |
|------|-------------|
| `find_advertiser` | Find advertiser by name |
| `get_advertiser` | Get advertiser details |
| `list_advertisers` | List all advertisers |
| `create_advertiser` | Create a new advertiser |
| `find_or_create_advertiser` | Find or create advertiser |

### Verification Tools

| Tool | Description |
|------|-------------|
| `verify_line_item_setup` | Verify line item configuration |
| `check_line_item_delivery_status` | Check delivery progress |
| `verify_order_setup` | Verify entire order setup |

### Workflow Tools

| Tool | Description |
|------|-------------|
| `create_campaign` | Complete campaign creation workflow |

## Example Usage with Claude

```
User: List all delivering orders

Claude: [Uses list_delivering_orders tool]
Here are the currently delivering orders:
1. Campaign IPhone 17 Pro 2025/2026 (ID: 123456)
   - Display line item: 45,000 impressions delivered

User: Create a new campaign for "ACME Corp" ending December 31, 2025

Claude: [Uses create_campaign tool]
I'll create the campaign with:
- Advertiser: ACME Corp
- Order: ACME Campaign 2025
- Line Item: Display
- End Date: December 31, 2025

Campaign created successfully!
- Order ID: 789012
- Line Item ID: 345678
- 4 creatives uploaded and associated
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/MatiousCorp/google-ad-manager-mcp.git
cd google-ad-manager-mcp

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gam_mcp --cov-report=html

# Run specific test file
pytest tests/test_utils.py
```

### Code Quality

```bash
# Run linter
ruff check .

# Run linter with auto-fix
ruff check . --fix
```

## Roadmap

The following features are planned for future releases:

### Near-term

- [ ] **Ad Unit Management** - List, get, and create ad units with hierarchy support
- [ ] **Placement Management** - Manage inventory placements and targeting
- [ ] **Line Item Status Control** - Pause, resume, archive, and approve line items
- [ ] **Forecast & Availability** - Check inventory availability and forecast impressions
- [ ] **Creative Preview Links** - Generate preview URLs for creative-line item combinations

### Medium-term

- [ ] **Advanced Targeting** - Geographic, device, daypart, and custom key-value targeting
- [ ] **Reporting Tools** - Generate and retrieve performance reports
- [ ] **Bulk Operations** - Batch updates for line items, creatives, and targeting
- [ ] **HTML5/Video Creatives** - Support for rich media and video creative uploads

### Long-term

- [ ] **Audience Management** - Create and manage audience segments
- [ ] **User & Permissions** - Manage users, roles, and order assignments
- [ ] **Yield Management** - Configure yield groups and optimization
- [ ] **Custom Reporting** - Scheduled reports with export capabilities

### Community Requests

Have a feature request? [Open an issue](https://github.com/MatiousCorp/google-ad-manager-mcp/issues) to suggest new functionality.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## API Version

Uses Google Ad Manager SOAP API version `v202411`.

## License

MIT - see [LICENSE](LICENSE) for details.

---

## Need a Custom MCP Server?

This project is built and maintained by **[Matious](https://matious.com)**.

We specialize in building custom AI tools and MCP servers that integrate with your existing systems. Whether you need to connect Claude to your CRM, ERP, ad platforms, or internal tools — we can help.

**What we build:**
- Custom MCP servers for any API or platform
- AI-powered automation workflows
- Claude integrations for business operations

**Get in touch:** [matious.com](https://matious.com)
