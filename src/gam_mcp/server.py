"""Google Ad Manager MCP Server with HTTP/SSE and stdio transport.

Security: Implements Bearer token authentication following MCP security best practices.
- Uses FastMCP native middleware for proper lifecycle management
- Cryptographically secure token generation (secrets.token_hex)
- Constant-time token comparison to prevent timing attacks
- All authentication decisions logged for audit trail

Reference: https://modelcontextprotocol.io/specification/draft/basic/security_best_practices
Reference: https://gofastmcp.com/python-sdk/fastmcp-server-auth-auth
"""

import os
import json
import logging
import secrets
import hmac
from typing import Optional

# Use the standalone fastmcp package (has full middleware support)
from fastmcp import FastMCP, Context
from fastmcp.server.middleware import Middleware
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

from .client import init_gam_client, get_gam_client
from .tools import orders, line_items, creatives, advertisers, verification

# Authentication token - set via environment variable or generate random
AUTH_TOKEN = os.environ.get("GAM_MCP_AUTH_TOKEN", None)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(name="Google Ad Manager")


# =============================================================================
# AUTHENTICATION MIDDLEWARE (FastMCP Native)
# =============================================================================

class BearerAuthMiddleware(Middleware):
    """FastMCP middleware for Bearer token authentication.

    Validates Authorization header on all tool calls.
    Uses constant-time comparison to prevent timing attacks.

    Reference: https://gelembjuk.com/blog/post/authentication-remote-mcp-server-python/
    """

    async def on_call_tool(self, context, call_next):
        """Validate bearer token before tool execution."""
        global AUTH_TOKEN

        if not AUTH_TOKEN:
            # No auth configured, allow request
            return await call_next(context)

        try:
            headers = get_http_headers()
            auth_header = headers.get("authorization", "")
        except Exception:
            # If we can't get headers (e.g., stdio transport), skip auth
            return await call_next(context)

        if not auth_header:
            logger.warning("Auth failed: Missing Authorization header")
            raise ToolError("Access denied: Missing Authorization header. Use: Authorization: Bearer <token>")

        if not auth_header.startswith("Bearer "):
            logger.warning("Auth failed: Invalid Authorization format")
            raise ToolError("Access denied: Invalid Authorization format. Use: Authorization: Bearer <token>")

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(token.encode('utf-8'), AUTH_TOKEN.encode('utf-8')):
            logger.warning("Auth failed: Invalid token")
            raise ToolError("Access denied: Invalid token")

        logger.debug("Auth successful")
        return await call_next(context)


# Add middleware to MCP server
mcp.add_middleware(BearerAuthMiddleware())
logger.info("Bearer token authentication middleware enabled")


# =============================================================================
# ORDER TOOLS
# =============================================================================

@mcp.tool()
def list_delivering_orders() -> str:
    """List all orders with line items currently delivering ads.

    Returns a list of orders with their delivering line items,
    including impression and click statistics.
    """
    result = orders.list_delivering_orders()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_order(order_id: Optional[int] = None, order_name: Optional[str] = None) -> str:
    """Get order details by ID or name.

    Args:
        order_id: The order ID (optional if order_name provided)
        order_name: The order name to search for (optional if order_id provided)

    Returns order details including all line items.
    """
    result = orders.get_order(order_id=order_id, order_name=order_name)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_order(order_name: str, advertiser_id: int) -> str:
    """Create a new order for an advertiser.

    Args:
        order_name: Name for the new order
        advertiser_id: ID of the advertiser company

    Returns the created order details.
    """
    result = orders.create_order(order_name=order_name, advertiser_id=advertiser_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def find_or_create_order(order_name: str, advertiser_id: int) -> str:
    """Find an existing order by name or create a new one.

    Args:
        order_name: Name of the order
        advertiser_id: ID of the advertiser company

    Returns the existing or newly created order.
    """
    result = orders.find_or_create_order(order_name=order_name, advertiser_id=advertiser_id)
    return json.dumps(result, indent=2)


# =============================================================================
# LINE ITEM TOOLS
# =============================================================================

@mcp.tool()
def get_line_item(line_item_id: int) -> str:
    """Get line item details by ID.

    Args:
        line_item_id: The line item ID

    Returns line item details including status, dates, and statistics.
    """
    result = line_items.get_line_item(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_line_item(
    order_id: int,
    name: str,
    end_year: int,
    end_month: int,
    end_day: int,
    target_ad_unit_id: str,
    line_item_type: str = "STANDARD",
    goal_impressions: int = 100000
) -> str:
    """Create a new line item for an order.

    Args:
        order_id: The order ID to add line item to
        name: Line item name
        end_year: End date year (e.g., 2025)
        end_month: End date month (1-12)
        end_day: End date day (1-31)
        target_ad_unit_id: Ad unit ID to target (find via GAM UI or ad unit tools)
        line_item_type: Type of line item (STANDARD, SPONSORSHIP, etc.)
        goal_impressions: Impression goal (default: 100000)

    Returns the created line item details.
    """
    result = line_items.create_line_item(
        order_id=order_id,
        name=name,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        line_item_type=line_item_type,
        target_ad_unit_id=target_ad_unit_id,
        goal_impressions=goal_impressions
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def duplicate_line_item(
    source_line_item_id: int,
    new_name: str,
    rename_source: Optional[str] = None
) -> str:
    """Duplicate an existing line item.

    Args:
        source_line_item_id: ID of the line item to duplicate
        new_name: Name for the new line item
        rename_source: Optional new name for the source line item

    Returns both the source and new line item details.
    """
    result = line_items.duplicate_line_item(
        source_line_item_id=source_line_item_id,
        new_name=new_name,
        rename_source=rename_source
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def update_line_item_name(line_item_id: int, new_name: str) -> str:
    """Update a line item's name.

    Args:
        line_item_id: The line item ID
        new_name: New name for the line item

    Returns the updated line item details.
    """
    result = line_items.update_line_item_name(
        line_item_id=line_item_id,
        new_name=new_name
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def list_line_items_by_order(order_id: int) -> str:
    """List all line items for an order.

    Args:
        order_id: The order ID

    Returns list of line items with their status and statistics.
    """
    result = line_items.list_line_items_by_order(order_id=order_id)
    return json.dumps(result, indent=2)


# =============================================================================
# CREATIVE TOOLS
# =============================================================================

@mcp.tool()
def upload_creative(
    file_path: str,
    advertiser_id: int,
    click_through_url: str,
    creative_name: Optional[str] = None,
    override_size_width: Optional[int] = None,
    override_size_height: Optional[int] = None
) -> str:
    """Upload an image creative to Ad Manager.

    Args:
        file_path: Path to the image file
        advertiser_id: ID of the advertiser
        click_through_url: Destination URL when clicked
        creative_name: Optional name for the creative
        override_size_width: Optional width to override the creative size (for serving into a different sized slot)
        override_size_height: Optional height to override the creative size (for serving into a different sized slot)

    The creative size is extracted from the filename (e.g., '300x250' in 'banner_300x250.png').
    Use override_size_width and override_size_height together to serve a creative into a different sized placement
    (e.g., serve a 970x250 image into a 1000x250 slot).

    Returns the created creative details.
    """
    result = creatives.upload_creative(
        file_path=file_path,
        advertiser_id=advertiser_id,
        click_through_url=click_through_url,
        creative_name=creative_name,
        override_size_width=override_size_width,
        override_size_height=override_size_height
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def associate_creative_with_line_item(
    creative_id: int,
    line_item_id: int,
    size_override_width: Optional[int] = None,
    size_override_height: Optional[int] = None
) -> str:
    """Associate a creative with a line item.

    Args:
        creative_id: The creative ID
        line_item_id: The line item ID
        size_override_width: Optional width for size override
        size_override_height: Optional height for size override

    Returns the association details.
    """
    result = creatives.associate_creative_with_line_item(
        creative_id=creative_id,
        line_item_id=line_item_id,
        size_override_width=size_override_width,
        size_override_height=size_override_height
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def upload_and_associate_creative(
    file_path: str,
    advertiser_id: int,
    line_item_id: int,
    click_through_url: str,
    creative_name: Optional[str] = None
) -> str:
    """Upload a creative and associate it with a line item in one step.

    Args:
        file_path: Path to the image file
        advertiser_id: ID of the advertiser
        line_item_id: ID of the line item
        click_through_url: Destination URL when clicked
        creative_name: Optional name for the creative

    Returns the creative and association details.
    """
    result = creatives.upload_and_associate_creative(
        file_path=file_path,
        advertiser_id=advertiser_id,
        line_item_id=line_item_id,
        click_through_url=click_through_url,
        creative_name=creative_name
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def bulk_upload_creatives(
    folder_path: str,
    advertiser_id: int,
    line_item_id: int,
    click_through_url: str,
    name_prefix: Optional[str] = None
) -> str:
    """Upload all creatives from a folder and associate with a line item.

    Args:
        folder_path: Path to folder containing image files
        advertiser_id: ID of the advertiser
        line_item_id: ID of the line item
        click_through_url: Destination URL when clicked
        name_prefix: Optional prefix for creative names

    Supported formats: jpg, jpeg, png, gif.
    Returns results for all uploads.
    """
    result = creatives.bulk_upload_creatives(
        folder_path=folder_path,
        advertiser_id=advertiser_id,
        line_item_id=line_item_id,
        click_through_url=click_through_url,
        name_prefix=name_prefix
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def get_creative(creative_id: int) -> str:
    """Get creative details by ID.

    Args:
        creative_id: The creative ID

    Returns creative details including size and destination URL.
    """
    result = creatives.get_creative(creative_id=creative_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_creatives_by_advertiser(advertiser_id: int, limit: int = 100) -> str:
    """List creatives for an advertiser.

    Args:
        advertiser_id: The advertiser ID
        limit: Maximum number of creatives to return (default: 100)

    Returns list of creatives.
    """
    result = creatives.list_creatives_by_advertiser(
        advertiser_id=advertiser_id,
        limit=limit
    )
    return json.dumps(result, indent=2)


# =============================================================================
# ADVERTISER TOOLS
# =============================================================================

@mcp.tool()
def find_advertiser(name: str) -> str:
    """Find an advertiser by name (partial match).

    Args:
        name: Advertiser name to search for

    Returns list of matching advertisers.
    """
    result = advertisers.find_advertiser(name=name)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_advertiser(advertiser_id: int) -> str:
    """Get advertiser details by ID.

    Args:
        advertiser_id: The advertiser/company ID

    Returns advertiser details.
    """
    result = advertisers.get_advertiser(advertiser_id=advertiser_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_advertisers(limit: int = 100) -> str:
    """List all advertisers.

    Args:
        limit: Maximum number of advertisers to return (default: 100)

    Returns list of advertisers.
    """
    result = advertisers.list_advertisers(limit=limit)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_advertiser(
    name: str,
    email: Optional[str] = None,
    address: Optional[str] = None
) -> str:
    """Create a new advertiser.

    Args:
        name: Advertiser name
        email: Optional email address
        address: Optional address

    Returns the created advertiser details.
    """
    result = advertisers.create_advertiser(
        name=name,
        email=email,
        address=address
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def find_or_create_advertiser(name: str, email: Optional[str] = None) -> str:
    """Find an advertiser by exact name or create if not found.

    Args:
        name: Exact advertiser name
        email: Optional email (used if creating)

    Returns the existing or newly created advertiser.
    """
    result = advertisers.find_or_create_advertiser(name=name, email=email)
    return json.dumps(result, indent=2)


# =============================================================================
# VERIFICATION TOOLS
# =============================================================================

@mcp.tool()
def verify_line_item_setup(line_item_id: int) -> str:
    """Verify line item setup including creative placeholders and associations.

    Args:
        line_item_id: The line item ID to verify

    Checks:
    - Creative placeholders (expected sizes)
    - Creative associations
    - Size mismatches between creatives and placeholders

    Returns verification results with any issues found.
    """
    result = verification.verify_line_item_setup(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_line_item_delivery_status(line_item_id: int) -> str:
    """Check detailed delivery status for a line item.

    Args:
        line_item_id: The line item ID to check

    Returns delivery progress including impressions, clicks, and goal progress.
    """
    result = verification.check_line_item_delivery_status(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def verify_order_setup(order_id: int) -> str:
    """Verify complete order setup including all line items.

    Args:
        order_id: The order ID to verify

    Returns comprehensive verification of the order and all its line items.
    """
    result = verification.verify_order_setup(order_id=order_id)
    return json.dumps(result, indent=2)


# =============================================================================
# CAMPAIGN WORKFLOW TOOL
# =============================================================================

@mcp.tool()
def create_campaign(
    advertiser_name: str,
    order_name: str,
    line_item_name: str,
    end_year: int,
    end_month: int,
    end_day: int,
    creatives_folder: str,
    click_through_url: str,
    target_ad_unit_id: str,
    goal_impressions: int = 100000
) -> str:
    """Create a complete campaign: find/create advertiser, order, line item, and upload creatives.

    Args:
        advertiser_name: Name of the advertiser
        order_name: Name for the order
        line_item_name: Name for the line item
        end_year: End date year
        end_month: End date month (1-12)
        end_day: End date day (1-31)
        creatives_folder: Path to folder containing creative images
        click_through_url: Destination URL for all creatives
        target_ad_unit_id: Ad unit ID to target (find via GAM UI or ad unit tools)
        goal_impressions: Impression goal (default: 100000)

    This is a complete workflow that:
    1. Finds or creates the advertiser
    2. Finds or creates the order
    3. Creates the line item
    4. Uploads all creatives from the folder
    5. Associates creatives with the line item

    Returns complete campaign creation results.
    """
    result = {
        "advertiser": None,
        "order": None,
        "line_item": None,
        "creatives": None,
        "errors": []
    }

    try:
        # Step 1: Find or create advertiser
        adv_result = advertisers.find_or_create_advertiser(name=advertiser_name)
        if "error" in adv_result:
            result["errors"].append(f"Advertiser: {adv_result['error']}")
            return json.dumps(result, indent=2)
        result["advertiser"] = adv_result
        advertiser_id = adv_result["id"]

        # Step 2: Find or create order
        order_result = orders.find_or_create_order(
            order_name=order_name,
            advertiser_id=advertiser_id
        )
        if "error" in order_result:
            result["errors"].append(f"Order: {order_result['error']}")
            return json.dumps(result, indent=2)
        result["order"] = order_result
        order_id = order_result["id"]

        # Step 3: Create line item
        li_result = line_items.create_line_item(
            order_id=order_id,
            name=line_item_name,
            end_year=end_year,
            end_month=end_month,
            end_day=end_day,
            target_ad_unit_id=target_ad_unit_id,
            goal_impressions=goal_impressions
        )
        if "error" in li_result:
            result["errors"].append(f"Line Item: {li_result['error']}")
            return json.dumps(result, indent=2)
        result["line_item"] = li_result
        line_item_id = li_result["id"]

        # Step 4: Upload creatives
        creative_result = creatives.bulk_upload_creatives(
            folder_path=creatives_folder,
            advertiser_id=advertiser_id,
            line_item_id=line_item_id,
            click_through_url=click_through_url,
            name_prefix=f"{advertiser_name} - {order_name}"
        )
        result["creatives"] = creative_result

        result["success"] = True
        result["message"] = f"Campaign '{order_name}' created successfully"

    except Exception as e:
        result["errors"].append(str(e))
        result["success"] = False

    return json.dumps(result, indent=2)


def init_client():
    """Initialize the GAM client from environment variables."""
    credentials_path = os.environ.get("GAM_CREDENTIALS_PATH")
    if not credentials_path:
        raise ValueError(
            "GAM_CREDENTIALS_PATH environment variable is required. "
            "Set it to the path of your Google Ad Manager service account JSON file."
        )

    network_code = os.environ.get("GAM_NETWORK_CODE")
    if not network_code:
        raise ValueError(
            "GAM_NETWORK_CODE environment variable is required. "
            "Set it to your Google Ad Manager network code."
        )

    logger.info(f"Initializing GAM client for network {network_code}")
    init_gam_client(
        credentials_path=credentials_path,
        network_code=network_code,
        application_name="GAM MCP Server"
    )


def main():
    """Main entry point for the MCP server."""
    global AUTH_TOKEN

    # Get transport mode from environment (default: http)
    transport = os.environ.get("GAM_MCP_TRANSPORT", "http").lower()
    host = os.environ.get("GAM_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("GAM_MCP_PORT", "8000"))

    init_client()

    if transport == "stdio":
        # Stdio transport - no auth token needed (local process)
        logger.info("Starting GAM MCP Server with stdio transport")
        mcp.run(transport="stdio")
    else:
        # HTTP transport - set up auth token
        if AUTH_TOKEN is None:
            AUTH_TOKEN = secrets.token_hex(32)
            logger.info("Generated auth token (set GAM_MCP_AUTH_TOKEN env var to use a fixed token)")

        logger.info("")
        logger.info("=" * 60)
        logger.info("GAM MCP Server Authentication Token:")
        logger.info(AUTH_TOKEN)
        logger.info("=" * 60)
        logger.info("")
        logger.info("Use this token in the Authorization header:")
        logger.info(f"Authorization: Bearer {AUTH_TOKEN}")
        logger.info("")

        # Run using FastMCP's native runner (proper lifecycle management)
        logger.info(f"Starting GAM MCP Server on http://{host}:{port}/mcp")
        mcp.run(transport="http", host=host, port=port, path="/mcp")


if __name__ == "__main__":
    main()
