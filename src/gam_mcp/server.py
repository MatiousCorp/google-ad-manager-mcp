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

from .client import init_gam_client, get_gam_client, is_gam_client_initialized
from .tools import orders, line_items, creatives, advertisers, verification, reporting

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
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
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
    goal_impressions: int = 100000,
    creative_sizes: Optional[str] = None,
    cost_per_unit_micro: int = 0,
    currency_code: str = "MAD"
) -> str:
    """Create a new line item for an order.

    Args:
        order_id: The order ID to add line item to
        name: Line item name
        end_year: End date year (e.g., 2025)
        end_month: End date month (1-12)
        end_day: End date day (1-31)
        target_ad_unit_id: Ad unit ID to target (find via GAM UI or ad unit tools)
        line_item_type: Type of line item. Valid types:
            - SPONSORSHIP: Guaranteed, time-based (100% share of voice)
            - STANDARD: Guaranteed, goal-based (specific number of impressions)
            - NETWORK: Non-guaranteed, run-of-network
            - BULK: Non-guaranteed, volume-based
            - PRICE_PRIORITY: Non-guaranteed, competes on price
            - HOUSE: Internal/house ads (lowest priority)
            - CLICK_TRACKING: For tracking clicks only
            - ADSENSE: AdSense backfill
            - AD_EXCHANGE: Ad Exchange backfill
            - BUMPER: Short video bumper ads
            - PREFERRED_DEAL: Programmatic preferred deals
        goal_impressions: Impression goal (default: 100000)
        creative_sizes: JSON string of sizes, e.g. '[{"width": 300, "height": 250}, {"width": 728, "height": 90}]'
                       If not provided, uses defaults: 300x250, 300x600, 728x90, 1000x250
        cost_per_unit_micro: Cost per unit in micro amounts (e.g., 1000000 = 1 MAD)
        currency_code: Currency code (default: MAD)

    Returns the created line item details.
    """
    init_client()

    # Parse creative_sizes JSON if provided
    parsed_sizes = None
    if creative_sizes:
        try:
            parsed_sizes = json.loads(creative_sizes)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid creative_sizes JSON: {e}"}, indent=2)

    result = line_items.create_line_item(
        order_id=order_id,
        name=name,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        line_item_type=line_item_type,
        target_ad_unit_id=target_ad_unit_id,
        goal_impressions=goal_impressions,
        creative_sizes=parsed_sizes,
        cost_per_unit_micro=cost_per_unit_micro,
        currency_code=currency_code
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
    init_client()
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
    init_client()
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
    init_client()
    result = line_items.list_line_items_by_order(order_id=order_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def pause_line_item(line_item_id: int) -> str:
    """Pause a delivering line item.

    Pausing stops the line item from delivering ads. The line item
    can be resumed later with resume_line_item.

    Args:
        line_item_id: The line item ID to pause

    Returns the result of the pause action including new status.
    """
    init_client()
    result = line_items.pause_line_item(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def resume_line_item(line_item_id: int) -> str:
    """Resume a paused line item.

    Resuming allows a previously paused line item to start
    delivering ads again based on its schedule and targeting.

    Args:
        line_item_id: The line item ID to resume

    Returns the result of the resume action including new status.
    """
    init_client()
    result = line_items.resume_line_item(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def archive_line_item(line_item_id: int) -> str:
    """Archive a line item.

    Archived line items are hidden from the default UI views but can
    still be retrieved via API. This is useful for cleaning up old
    campaigns. Note: This action cannot be undone via API.

    Args:
        line_item_id: The line item ID to archive

    Returns the result of the archive action including new status.
    """
    init_client()
    result = line_items.archive_line_item(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def approve_line_item(line_item_id: int) -> str:
    """Approve a line item that requires approval.

    This is used when the approval workflow is enabled in Google Ad Manager.
    Line items in NEEDS_APPROVAL status can be approved to allow delivery.

    Args:
        line_item_id: The line item ID to approve

    Returns the result of the approve action including new status.
    """
    init_client()
    result = line_items.approve_line_item(line_item_id=line_item_id)
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
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
    result = creatives.list_creatives_by_advertiser(
        advertiser_id=advertiser_id,
        limit=limit
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def update_creative(
    creative_id: int,
    destination_url: Optional[str] = None,
    name: Optional[str] = None
) -> str:
    """Update an existing creative's properties.

    Args:
        creative_id: The creative ID to update
        destination_url: New destination/click-through URL for the creative
        name: New name for the creative

    At least one of destination_url or name must be provided.
    Returns the updated creative details.
    """
    init_client()
    result = creatives.update_creative(
        creative_id=creative_id,
        destination_url=destination_url,
        name=name
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def list_creatives_by_line_item(line_item_id: int, limit: int = 100) -> str:
    """List creatives associated with a line item.

    Args:
        line_item_id: The line item ID
        limit: Maximum number of creatives to return (default: 100)

    Returns list of creatives with their association status.
    """
    init_client()
    result = creatives.list_creatives_by_line_item(
        line_item_id=line_item_id,
        limit=limit
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def get_creative_preview_url(
    line_item_id: int,
    creative_id: int,
    site_url: str
) -> str:
    """Get a preview URL for a creative associated with a line item.

    This generates a preview URL that shows how the creative will appear
    on the specified site URL. The preview URL loads the site with the
    creative displayed in its ad slots.

    Args:
        line_item_id: The line item ID
        creative_id: The creative ID
        site_url: The URL of the site where you want to preview the creative
            (e.g., "https://abc.com")

    Returns the preview URL that can be opened in a browser.
    """
    init_client()
    result = creatives.get_creative_preview_url(
        line_item_id=line_item_id,
        creative_id=creative_id,
        site_url=site_url
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def create_third_party_creative(
    advertiser_id: int,
    name: str,
    width: int,
    height: int,
    snippet: str,
    expanded_snippet: Optional[str] = None,
    is_safe_frame_compatible: bool = True
) -> str:
    """Create a third-party creative (HTML/JavaScript ad tag).

    Use this for DCM/Campaign Manager tags, custom HTML ads, or any third-party
    ad server tags that need to be served through Google Ad Manager.

    Args:
        advertiser_id: ID of the advertiser
        name: Name for the creative
        width: Creative width in pixels
        height: Creative height in pixels
        snippet: The HTML/JavaScript code snippet (the ad tag)
        expanded_snippet: Optional expanded snippet for expandable creatives
        is_safe_frame_compatible: Whether the creative works in SafeFrame (default: True)

    Returns the created creative details.
    """
    init_client()
    result = creatives.create_third_party_creative(
        advertiser_id=advertiser_id,
        name=name,
        width=width,
        height=height,
        snippet=snippet,
        expanded_snippet=expanded_snippet,
        is_safe_frame_compatible=is_safe_frame_compatible
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
    init_client()
    result = advertisers.find_advertiser(name=name)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_advertiser(advertiser_id: int) -> str:
    """Get advertiser details by ID.

    Args:
        advertiser_id: The advertiser/company ID

    Returns advertiser details.
    """
    init_client()
    result = advertisers.get_advertiser(advertiser_id=advertiser_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_advertisers(limit: int = 100) -> str:
    """List all advertisers.

    Args:
        limit: Maximum number of advertisers to return (default: 100)

    Returns list of advertisers.
    """
    init_client()
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
    init_client()
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
    init_client()
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
    init_client()
    result = verification.verify_line_item_setup(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_line_item_delivery_status(line_item_id: int) -> str:
    """Check detailed delivery status for a line item.

    Args:
        line_item_id: The line item ID to check

    Returns delivery progress including impressions, clicks, and goal progress.
    """
    init_client()
    result = verification.check_line_item_delivery_status(line_item_id=line_item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def verify_order_setup(order_id: int) -> str:
    """Verify complete order setup including all line items.

    Args:
        order_id: The order ID to verify

    Returns comprehensive verification of the order and all its line items.
    """
    init_client()
    result = verification.verify_order_setup(order_id=order_id)
    return json.dumps(result, indent=2)


# =============================================================================
# REPORTING TOOLS
# =============================================================================

@mcp.tool()
def run_delivery_report(
    date_range_type: str = "LAST_WEEK",
    start_year: Optional[int] = None,
    start_month: Optional[int] = None,
    start_day: Optional[int] = None,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    end_day: Optional[int] = None,
    order_id: Optional[int] = None,
    line_item_id: Optional[int] = None,
    include_date_breakdown: bool = True,
    timeout_seconds: int = 120
) -> str:
    """Run a delivery report for orders and line items.

    Returns impressions, clicks, CTR, and revenue broken down by order and line item.

    Args:
        date_range_type: Date range for the report. Valid values:
            - TODAY, YESTERDAY, LAST_WEEK, LAST_MONTH, LAST_3_MONTHS, REACH_LIFETIME
            - CUSTOM_DATE (requires start and end date parameters)
        start_year: Start date year (required if date_range_type is CUSTOM_DATE)
        start_month: Start date month 1-12 (required if date_range_type is CUSTOM_DATE)
        start_day: Start date day 1-31 (required if date_range_type is CUSTOM_DATE)
        end_year: End date year (required if date_range_type is CUSTOM_DATE)
        end_month: End date month 1-12 (required if date_range_type is CUSTOM_DATE)
        end_day: End date day 1-31 (required if date_range_type is CUSTOM_DATE)
        order_id: Optional order ID to filter by
        line_item_id: Optional line item ID to filter by
        include_date_breakdown: If True, includes daily breakdown (default: True)
        timeout_seconds: Maximum time to wait for report (default: 120)

    Returns report data with impressions, clicks, CTR, and revenue statistics.
    """
    init_client()
    result = reporting.run_delivery_report(
        date_range_type=date_range_type,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        order_id=order_id,
        line_item_id=line_item_id,
        include_date_breakdown=include_date_breakdown,
        timeout_seconds=timeout_seconds
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def run_inventory_report(
    date_range_type: str = "LAST_WEEK",
    start_year: Optional[int] = None,
    start_month: Optional[int] = None,
    start_day: Optional[int] = None,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    end_day: Optional[int] = None,
    ad_unit_id: Optional[str] = None,
    include_date_breakdown: bool = True,
    timeout_seconds: int = 120
) -> str:
    """Run an inventory report for ad units.

    Returns ad requests, impressions, and fill rate broken down by ad unit.

    Args:
        date_range_type: Date range for the report (TODAY, YESTERDAY, LAST_WEEK, etc.)
        start_year: Start date year (for CUSTOM_DATE)
        start_month: Start date month 1-12 (for CUSTOM_DATE)
        start_day: Start date day 1-31 (for CUSTOM_DATE)
        end_year: End date year (for CUSTOM_DATE)
        end_month: End date month 1-12 (for CUSTOM_DATE)
        end_day: End date day 1-31 (for CUSTOM_DATE)
        ad_unit_id: Optional ad unit ID to filter by
        include_date_breakdown: If True, includes daily breakdown (default: True)
        timeout_seconds: Maximum time to wait for report (default: 120)

    Returns report data with ad requests, impressions, and fill rate statistics.
    """
    init_client()
    result = reporting.run_inventory_report(
        date_range_type=date_range_type,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        ad_unit_id=ad_unit_id,
        include_date_breakdown=include_date_breakdown,
        timeout_seconds=timeout_seconds
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def run_custom_report(
    dimensions: str,
    columns: str,
    date_range_type: str = "LAST_WEEK",
    start_year: Optional[int] = None,
    start_month: Optional[int] = None,
    start_day: Optional[int] = None,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    end_day: Optional[int] = None,
    filter_statement: Optional[str] = None,
    timeout_seconds: int = 120
) -> str:
    """Run a custom report with specified dimensions and metrics.

    Args:
        dimensions: JSON array of dimension names, e.g. '["DATE", "ORDER_NAME", "LINE_ITEM_NAME"]'
            Valid dimensions: DATE, WEEK, MONTH_AND_YEAR, ORDER_ID, ORDER_NAME,
            LINE_ITEM_ID, LINE_ITEM_NAME, LINE_ITEM_TYPE, CREATIVE_ID, CREATIVE_NAME,
            CREATIVE_SIZE, ADVERTISER_ID, ADVERTISER_NAME, AD_UNIT_ID, AD_UNIT_NAME
        columns: JSON array of metric names, e.g. '["TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS"]'
            Valid metrics: TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS, TOTAL_LINE_ITEM_LEVEL_CLICKS,
            TOTAL_LINE_ITEM_LEVEL_CTR, TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE,
            TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE, TOTAL_INVENTORY_LEVEL_IMPRESSIONS,
            TOTAL_AD_REQUESTS, TOTAL_RESPONSES_SERVED, TOTAL_FILL_RATE
        date_range_type: Date range (TODAY, YESTERDAY, LAST_WEEK, LAST_MONTH,
            LAST_3_MONTHS, REACH_LIFETIME, CUSTOM_DATE)
        start_year: Start year for CUSTOM_DATE range
        start_month: Start month (1-12) for CUSTOM_DATE range
        start_day: Start day (1-31) for CUSTOM_DATE range
        end_year: End year for CUSTOM_DATE range
        end_month: End month (1-12) for CUSTOM_DATE range
        end_day: End day (1-31) for CUSTOM_DATE range
        filter_statement: Optional filter (e.g., "ORDER_ID = 12345")
        timeout_seconds: Maximum seconds to wait for report completion

    Returns report data with specified dimensions and metrics.
    """
    init_client()

    # Parse JSON arrays
    try:
        parsed_dimensions = json.loads(dimensions)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid dimensions JSON: {e}"}, indent=2)

    try:
        parsed_columns = json.loads(columns)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid columns JSON: {e}"}, indent=2)

    result = reporting.run_custom_report(
        dimensions=parsed_dimensions,
        columns=parsed_columns,
        date_range_type=date_range_type,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        filter_statement=filter_statement,
        timeout_seconds=timeout_seconds
    )
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
    goal_impressions: int = 100000,
    line_item_type: str = "STANDARD",
    creative_sizes: Optional[str] = None
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
        line_item_type: Type of line item (STANDARD, SPONSORSHIP, NETWORK, BULK, PRICE_PRIORITY, HOUSE, etc.)
        creative_sizes: JSON string of sizes, e.g. '[{"width": 300, "height": 250}, {"width": 728, "height": 90}]'

    This is a complete workflow that:
    1. Finds or creates the advertiser
    2. Finds or creates the order
    3. Creates the line item
    4. Uploads all creatives from the folder
    5. Associates creatives with the line item

    Returns complete campaign creation results.
    """
    init_client()
    result = {
        "advertiser": None,
        "order": None,
        "line_item": None,
        "creatives": None,
        "errors": []
    }

    # Parse creative_sizes JSON if provided
    parsed_sizes = None
    if creative_sizes:
        try:
            parsed_sizes = json.loads(creative_sizes)
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid creative_sizes JSON: {e}")
            return json.dumps(result, indent=2)

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
            goal_impressions=goal_impressions,
            line_item_type=line_item_type,
            creative_sizes=parsed_sizes
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
    """Initialize the GAM client from environment variables.

    This is called lazily when the first tool is executed, not at server startup.
    This allows the server to start and list tools even without credentials.
    """
    # Check if already initialized
    if is_gam_client_initialized():
        return

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

    # Get transport mode from environment (default: stdio for CLI usage)
    transport = os.environ.get("GAM_MCP_TRANSPORT", "stdio").lower()
    host = os.environ.get("GAM_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("GAM_MCP_PORT", "8000"))

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
