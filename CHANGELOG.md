# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-01

### Added

- Initial release of GAM MCP Server
- **Order Management**
  - `list_delivering_orders` - List all orders with delivering line items
  - `get_order` - Get order details by ID or name
  - `create_order` - Create a new order
  - `find_or_create_order` - Find existing or create new order (idempotent)
- **Line Item Management**
  - `get_line_item` - Get line item details
  - `create_line_item` - Create a new line item with customizable sizes, dates, impressions
  - `duplicate_line_item` - Duplicate an existing line item with optional source rename
  - `update_line_item_name` - Rename a line item
  - `list_line_items_by_order` - List all line items for an order
- **Creative Management**
  - `upload_creative` - Upload an image creative (auto-extracts size from filename)
  - `associate_creative_with_line_item` - Associate creative with line item
  - `upload_and_associate_creative` - Upload and associate in one operation
  - `bulk_upload_creatives` - Batch upload all creatives from a folder
  - `get_creative` - Get creative details
  - `list_creatives_by_advertiser` - List creatives for an advertiser with pagination
- **Advertiser Management**
  - `find_advertiser` - Find advertiser by partial name match
  - `get_advertiser` - Get advertiser details by ID
  - `list_advertisers` - List all advertisers with pagination
  - `create_advertiser` - Create a new advertiser
  - `find_or_create_advertiser` - Find or create advertiser (idempotent)
- **Verification Tools**
  - `verify_line_item_setup` - Validate creative placeholders, associations, size mismatches
  - `check_line_item_delivery_status` - Track impressions/clicks vs goals
  - `verify_order_setup` - Comprehensive order validation
- **Workflow Tools**
  - `create_campaign` - End-to-end campaign creation (advertiser → order → line item → creatives)
- **Security Features**
  - Bearer token authentication with FastMCP middleware
  - Cryptographically secure token generation
  - Timing attack prevention with constant-time comparison
- **Infrastructure**
  - Docker support with non-root user
  - Environment-based configuration
  - Comprehensive logging

[Unreleased]: https://github.com/MatiousCorp/google-ad-manager-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MatiousCorp/google-ad-manager-mcp/releases/tag/v0.1.0
