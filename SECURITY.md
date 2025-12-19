# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in GAM MCP Server, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, send a detailed report to: **youssef@matious.com**

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days (depending on severity)

### What to Expect

1. Acknowledgment of your report
2. Assessment of the vulnerability
3. Development and testing of a fix
4. Coordinated disclosure (we'll credit you unless you prefer anonymity)

## Security Best Practices for Users

### Credential Management

- Never commit `credentials.json` or service account keys to version control
- Use environment variables for sensitive configuration
- Rotate authentication tokens periodically

### Deployment

- Always use authentication tokens in production (`GAM_MCP_AUTH_TOKEN`)
- Use HTTPS for remote deployments
- Run the Docker container as non-root (default configuration)
- Restrict network access to the MCP server endpoint

### Google Ad Manager Permissions

- Use service accounts with minimal required permissions
- Regularly audit service account access
- Revoke unused service account keys

## Security Features

This project implements several security measures:

- **Bearer Token Authentication**: All tool calls require valid authentication
- **Constant-Time Comparison**: Prevents timing attacks on token validation
- **Parameterized Queries**: All GAM API queries use bind variables to prevent injection
- **Non-Root Docker**: Container runs as unprivileged user
- **Audit Logging**: Authentication attempts are logged for monitoring

## Acknowledgments

We thank the security researchers who help keep this project secure.
