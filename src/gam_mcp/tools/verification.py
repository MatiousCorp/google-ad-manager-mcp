"""Verification tools for Google Ad Manager."""

import logging
from typing import Optional
from ..client import get_gam_client
from ..utils import safe_get, extract_date

logger = logging.getLogger(__name__)


def verify_line_item_setup(line_item_id: int) -> dict:
    """Verify line item setup including creative placeholders and associations.

    Args:
        line_item_id: The line item ID to verify

    Returns:
        dict with verification results
    """
    client = get_gam_client()

    result = {
        "line_item_id": line_item_id,
        "line_item": None,
        "creative_placeholders": [],
        "creative_associations": [],
        "issues": [],
        "status": "OK"
    }

    # Get line item details using bind variable
    line_item_service = client.get_service('LineItemService')
    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', line_item_id)
    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Line item {line_item_id} not found"}

    line_item = response['results'][0]

    result["line_item"] = {
        "id": line_item['id'],
        "name": line_item['name'],
        "status": line_item['status'],
        "type": line_item.get('lineItemType'),
        "order_id": line_item['orderId']
    }

    # Extract creative placeholders
    if line_item.get('creativePlaceholders'):
        for ph in line_item['creativePlaceholders']:
            size = ph.get('size', {})
            result["creative_placeholders"].append({
                "width": size.get('width'),
                "height": size.get('height'),
                "size_string": f"{size.get('width')}x{size.get('height')}"
            })

    # Get creative associations using bind variable
    lica_service = client.get_service('LineItemCreativeAssociationService')
    lica_statement = client.create_statement()
    lica_statement = lica_statement.Where(
        "lineItemId = :lineItemId"
    ).WithBindVariable('lineItemId', line_item_id)
    lica_response = lica_service.getLineItemCreativeAssociationsByStatement(lica_statement.ToStatement())

    creative_service = client.get_service('CreativeService')

    if 'results' in lica_response:
        for lica in lica_response['results']:
            creative_id = lica['creativeId']
            status = lica.get('status', 'UNKNOWN')

            # Get creative details using bind variable
            creative_statement = client.create_statement()
            creative_statement = creative_statement.Where(
                "id = :id"
            ).WithBindVariable('id', creative_id)
            creative_response = creative_service.getCreativesByStatement(creative_statement.ToStatement())

            creative_info = {
                "creative_id": creative_id,
                "association_status": status,
                "creative_name": None,
                "creative_size": None,
                "size_overrides": []
            }

            if 'results' in creative_response and len(creative_response['results']) > 0:
                creative = creative_response['results'][0]
                creative_size = creative.get('size', {})
                creative_info["creative_name"] = creative.get('name')
                creative_info["creative_size"] = f"{creative_size.get('width')}x{creative_size.get('height')}"

            # Check for size overrides in LICA
            if lica.get('sizes'):
                for size in lica['sizes']:
                    creative_info["size_overrides"].append(
                        f"{size.get('width')}x{size.get('height')}"
                    )

            result["creative_associations"].append(creative_info)

    # Analyze for issues
    placeholder_sizes = set(p["size_string"] for p in result["creative_placeholders"])

    for assoc in result["creative_associations"]:
        creative_size = assoc["creative_size"]
        size_overrides = assoc["size_overrides"]

        # Determine effective sizes this creative targets
        effective_sizes = set(size_overrides) if size_overrides else {creative_size}

        # Check if any effective size matches a placeholder
        if not effective_sizes.intersection(placeholder_sizes):
            result["issues"].append({
                "type": "SIZE_MISMATCH",
                "creative_id": assoc["creative_id"],
                "creative_size": creative_size,
                "size_overrides": size_overrides,
                "available_placeholders": list(placeholder_sizes),
                "message": f"Creative {assoc['creative_id']} ({creative_size}) doesn't match any placeholder"
            })

    # Set overall status
    if result["issues"]:
        result["status"] = "ISSUES_FOUND"
    elif not result["creative_associations"]:
        result["status"] = "NO_CREATIVES"
        result["issues"].append({
            "type": "NO_CREATIVES",
            "message": "Line item has no creative associations"
        })

    # Summary
    result["summary"] = {
        "placeholder_count": len(result["creative_placeholders"]),
        "creative_count": len(result["creative_associations"]),
        "issue_count": len(result["issues"]),
        "placeholder_sizes": list(placeholder_sizes)
    }

    return result


def check_line_item_delivery_status(line_item_id: int) -> dict:
    """Check detailed delivery status for a line item.

    Args:
        line_item_id: The line item ID to check

    Returns:
        dict with delivery status details
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', line_item_id)
    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Line item {line_item_id} not found"}

    li = response['results'][0]
    stats = li.get('stats', {}) or {}
    primary_goal = li.get('primaryGoal', {}) or {}

    # Calculate progress
    goal_units = primary_goal.get('units', 0) or 0
    impressions = stats.get('impressionsDelivered', 0) or 0

    progress_pct = 0
    if goal_units > 0:
        progress_pct = round((impressions / goal_units) * 100, 2)

    return {
        "line_item_id": li['id'],
        "name": li['name'],
        "status": li['status'],
        "type": li.get('lineItemType'),
        "delivery": {
            "impressions_delivered": impressions,
            "clicks_delivered": stats.get('clicksDelivered', 0) or 0,
            "goal_type": primary_goal.get('goalType'),
            "goal_unit_type": primary_goal.get('unitType'),
            "goal_units": goal_units,
            "progress_percent": progress_pct
        },
        "needs_creatives": li.get('isMissingCreatives', False),
        "is_set_to_deliver": li.get('isSetTopBoxEnabled', False),
        "delivery_rate_type": li.get('deliveryRateType')
    }


def verify_order_setup(order_id: int) -> dict:
    """Verify complete order setup including all line items.

    Args:
        order_id: The order ID to verify

    Returns:
        dict with complete order verification
    """
    client = get_gam_client()

    # Get order using bind variable
    order_service = client.get_service('OrderService')
    order_statement = client.create_statement()
    order_statement = order_statement.Where("id = :id").WithBindVariable('id', order_id)
    order_response = order_service.getOrdersByStatement(order_statement.ToStatement())

    if 'results' not in order_response or len(order_response['results']) == 0:
        return {"error": f"Order {order_id} not found"}

    order = order_response['results'][0]

    result = {
        "order_id": order['id'],
        "order_name": order['name'],
        "order_status": order['status'],
        "advertiser_id": order.get('advertiserId'),
        "line_items": [],
        "issues": [],
        "overall_status": "OK"
    }

    # Get all line items using bind variable
    line_item_service = client.get_service('LineItemService')
    li_statement = client.create_statement()
    li_statement = li_statement.Where("orderId = :orderId").WithBindVariable('orderId', order_id)
    li_response = line_item_service.getLineItemsByStatement(li_statement.ToStatement())

    if 'results' in li_response:
        for li in li_response['results']:
            li_verification = verify_line_item_setup(li['id'])

            if "error" in li_verification:
                result["line_items"].append({
                    "id": li['id'],
                    "name": li['name'],
                    "error": li_verification["error"]
                })
            else:
                result["line_items"].append({
                    "id": li['id'],
                    "name": li_verification["line_item"]["name"],
                    "status": li_verification["line_item"]["status"],
                    "creative_count": li_verification["summary"]["creative_count"],
                    "issue_count": li_verification["summary"]["issue_count"],
                    "issues": li_verification["issues"]
                })

                if li_verification["issues"]:
                    result["issues"].extend([
                        {**issue, "line_item_id": li['id'], "line_item_name": li['name']}
                        for issue in li_verification["issues"]
                    ])

    # Set overall status
    if result["issues"]:
        result["overall_status"] = "ISSUES_FOUND"

    result["summary"] = {
        "line_item_count": len(result["line_items"]),
        "total_issues": len(result["issues"])
    }

    return result
