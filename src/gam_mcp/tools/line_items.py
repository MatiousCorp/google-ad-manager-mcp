"""Line item tools for Google Ad Manager."""

import logging
from typing import Optional, List
from ..client import get_gam_client
from ..utils import safe_get, extract_date

logger = logging.getLogger(__name__)


# Standard creative sizes
DEFAULT_CREATIVE_PLACEHOLDERS = [
    {'size': {'width': 300, 'height': 250, 'isAspectRatio': False}},
    {'size': {'width': 300, 'height': 600, 'isAspectRatio': False}},
    {'size': {'width': 728, 'height': 90, 'isAspectRatio': False}},
    {'size': {'width': 1000, 'height': 250, 'isAspectRatio': False}},
]


def get_line_item(line_item_id: int) -> dict:
    """Get line item details by ID.

    Args:
        line_item_id: The line item ID

    Returns:
        dict with line item details
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', line_item_id)

    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Line item {line_item_id} not found"}

    li = response['results'][0]

    # Extract dates
    start_date = extract_date(safe_get(li, 'startDateTime'))
    end_date = extract_date(safe_get(li, 'endDateTime'))

    # Extract creative placeholders
    placeholders = []
    creative_placeholders = safe_get(li, 'creativePlaceholders')
    if creative_placeholders:
        for ph in creative_placeholders:
            size = safe_get(ph, 'size')
            if size:
                placeholders.append(f"{safe_get(size, 'width')}x{safe_get(size, 'height')}")

    # Extract stats
    stats = safe_get(li, 'stats')
    impressions = safe_get(stats, 'impressionsDelivered', 0) or 0
    clicks = safe_get(stats, 'clicksDelivered', 0) or 0

    # Extract targeted ad unit IDs
    targeted_ad_unit_ids = []
    targeting = safe_get(li, 'targeting')
    if targeting:
        inventory_targeting = safe_get(targeting, 'inventoryTargeting')
        if inventory_targeting:
            targeted_ad_units = safe_get(inventory_targeting, 'targetedAdUnits')
            if targeted_ad_units:
                for ad_unit in targeted_ad_units:
                    ad_unit_id = safe_get(ad_unit, 'adUnitId')
                    if ad_unit_id:
                        targeted_ad_unit_ids.append(ad_unit_id)

    return {
        "id": safe_get(li, 'id'),
        "name": safe_get(li, 'name'),
        "order_id": safe_get(li, 'orderId'),
        "status": safe_get(li, 'status'),
        "type": safe_get(li, 'lineItemType'),
        "start_date": start_date,
        "end_date": end_date,
        "cost_type": safe_get(li, 'costType'),
        "creative_placeholders": placeholders,
        "impressions_delivered": impressions,
        "clicks_delivered": clicks,
        "delivery_rate_type": safe_get(li, 'deliveryRateType'),
        "environment_type": safe_get(li, 'environmentType'),
        "targeted_ad_unit_ids": targeted_ad_unit_ids
    }


def create_line_item(
    order_id: int,
    name: str,
    end_year: int,
    end_month: int,
    end_day: int,
    target_ad_unit_id: str,
    line_item_type: str = "STANDARD",
    goal_impressions: int = 100000,
    creative_sizes: Optional[List[dict]] = None,
    cost_per_unit_micro: int = 0,
    currency_code: str = "MAD"
) -> dict:
    """Create a new line item.

    Args:
        order_id: The order ID to add line item to
        name: Line item name
        end_year: End date year
        end_month: End date month
        end_day: End date day
        target_ad_unit_id: Ad unit ID to target (required, find via GAM UI)
        line_item_type: Type (STANDARD, SPONSORSHIP, etc.)
        goal_impressions: Impression goal
        creative_sizes: List of size dicts (optional, uses defaults if not provided)
        cost_per_unit_micro: Cost in micro amounts
        currency_code: Currency code

    Returns:
        dict with created line item details
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    # Use default sizes if not provided
    if creative_sizes is None:
        creative_placeholders = DEFAULT_CREATIVE_PLACEHOLDERS
    else:
        creative_placeholders = [
            {'size': {'width': s['width'], 'height': s['height'], 'isAspectRatio': False}}
            for s in creative_sizes
        ]

    line_item = {
        'name': name,
        'orderId': order_id,
        'lineItemType': line_item_type,
        'startDateTimeType': 'IMMEDIATELY',
        'endDateTime': {
            'date': {'year': end_year, 'month': end_month, 'day': end_day},
            'hour': 23,
            'minute': 59,
            'second': 59,
            'timeZoneId': 'Africa/Casablanca'
        },
        'costType': 'CPM',
        'costPerUnit': {
            'currencyCode': currency_code,
            'microAmount': cost_per_unit_micro
        },
        'creativePlaceholders': creative_placeholders,
        'primaryGoal': {
            'goalType': 'LIFETIME',
            'unitType': 'IMPRESSIONS',
            'units': goal_impressions
        },
        'targeting': {
            'inventoryTargeting': {
                'targetedAdUnits': [
                    {
                        'adUnitId': target_ad_unit_id,
                        'includeDescendants': True
                    }
                ]
            }
        },
        'environmentType': 'BROWSER',
        'creativeRotationType': 'OPTIMIZED',
        'deliveryRateType': 'EVENLY',
        'roadblockingType': 'AS_MANY_AS_POSSIBLE',
    }

    created_line_items = line_item_service.createLineItems([line_item])

    if not created_line_items:
        return {"error": "Failed to create line item"}

    created = created_line_items[0]

    return {
        "id": safe_get(created, 'id'),
        "name": safe_get(created, 'name'),
        "order_id": safe_get(created, 'orderId'),
        "status": safe_get(created, 'status'),
        "type": safe_get(created, 'lineItemType'),
        "end_date": f"{end_year}-{end_month:02d}-{end_day:02d}",
        "message": f"Line item '{name}' created successfully"
    }


def duplicate_line_item(
    source_line_item_id: int,
    new_name: str,
    rename_source: Optional[str] = None
) -> dict:
    """Duplicate an existing line item.

    Args:
        source_line_item_id: ID of line item to duplicate
        new_name: Name for the new line item
        rename_source: Optional new name for the source line item

    Returns:
        dict with both line item details
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    # Fetch source line item using bind variable
    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', source_line_item_id)
    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Line item {source_line_item_id} not found"}

    source = response['results'][0]
    result = {"source_line_item": None, "new_line_item": None}

    # Optionally rename source
    if rename_source:
        source['name'] = rename_source
        updated = line_item_service.updateLineItems([source])
        if updated:
            result["source_line_item"] = {
                "id": safe_get(updated[0], 'id'),
                "name": safe_get(updated[0], 'name'),
                "renamed_to": rename_source
            }

    # Create duplicate
    new_line_item = {
        'name': new_name,
        'orderId': safe_get(source, 'orderId'),
        'lineItemType': safe_get(source, 'lineItemType'),
        'startDateTimeType': 'IMMEDIATELY',
        'costType': safe_get(source, 'costType'),
    }

    # Copy optional fields
    optional_fields = [
        'creativePlaceholders', 'targeting', 'primaryGoal', 'endDateTime',
        'costPerUnit', 'valueCostPerUnit', 'deliveryRateType',
        'roadblockingType', 'creativeRotationType', 'environmentType',
        'companionDeliveryOption'
    ]

    for field in optional_fields:
        value = safe_get(source, field)
        if value is not None:
            new_line_item[field] = value

    # Handle unlimited end date
    if safe_get(source, 'endDateTime') is None:
        new_line_item['unlimitedEndDateTime'] = True

    created = line_item_service.createLineItems([new_line_item])

    if not created:
        return {"error": "Failed to create duplicate line item"}

    result["new_line_item"] = {
        "id": safe_get(created[0], 'id'),
        "name": safe_get(created[0], 'name'),
        "order_id": safe_get(created[0], 'orderId'),
        "status": safe_get(created[0], 'status')
    }

    result["message"] = f"Line item duplicated successfully as '{new_name}'"

    return result


def update_line_item(
    line_item_id: int,
    name: Optional[str] = None,
    line_item_type: Optional[str] = None,
    delivery_rate_type: Optional[str] = None,
    priority: Optional[int] = None,
    cost_per_unit_micro: Optional[int] = None,
    currency_code: Optional[str] = None,
    goal_impressions: Optional[int] = None,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    end_day: Optional[int] = None
) -> dict:
    """Update an existing line item's properties.

    Args:
        line_item_id: The line item ID to update
        name: New name for the line item
        line_item_type: Type of line item (STANDARD, SPONSORSHIP, NETWORK, BULK,
                       PRICE_PRIORITY, HOUSE, etc.)
        delivery_rate_type: How the line item delivers (EVENLY, FRONTLOADED,
                           AS_FAST_AS_POSSIBLE)
        priority: Priority value (1-16, depends on line item type)
        cost_per_unit_micro: Cost per unit in micro amounts (e.g., 1000000 = 1 currency unit)
        currency_code: Currency code (e.g., MAD, USD, EUR)
        goal_impressions: Impression goal (updates primaryGoal.units)
        end_year: End date year
        end_month: End date month (1-12)
        end_day: End date day (1-31)

    Returns:
        dict with updated line item details
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    # Fetch the existing line item
    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', line_item_id)
    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Line item {line_item_id} not found"}

    line_item = response['results'][0]
    changes = []

    # Update name
    if name is not None:
        old_name = safe_get(line_item, 'name')
        line_item['name'] = name
        changes.append(f"name: '{old_name}' -> '{name}'")

    # Update line item type
    if line_item_type is not None:
        old_type = safe_get(line_item, 'lineItemType')
        line_item['lineItemType'] = line_item_type
        changes.append(f"lineItemType: '{old_type}' -> '{line_item_type}'")

    # Update delivery rate type
    if delivery_rate_type is not None:
        old_delivery = safe_get(line_item, 'deliveryRateType')
        line_item['deliveryRateType'] = delivery_rate_type
        changes.append(f"deliveryRateType: '{old_delivery}' -> '{delivery_rate_type}'")

    # Update priority
    if priority is not None:
        old_priority = safe_get(line_item, 'priority')
        line_item['priority'] = priority
        changes.append(f"priority: {old_priority} -> {priority}")

    # Update cost per unit
    if cost_per_unit_micro is not None or currency_code is not None:
        if 'costPerUnit' not in line_item:
            line_item['costPerUnit'] = {}

        if cost_per_unit_micro is not None:
            old_cost = safe_get(line_item.get('costPerUnit', {}), 'microAmount', 0)
            line_item['costPerUnit']['microAmount'] = cost_per_unit_micro
            changes.append(f"costPerUnit.microAmount: {old_cost} -> {cost_per_unit_micro}")

        if currency_code is not None:
            old_currency = safe_get(line_item.get('costPerUnit', {}), 'currencyCode')
            line_item['costPerUnit']['currencyCode'] = currency_code
            changes.append(f"costPerUnit.currencyCode: '{old_currency}' -> '{currency_code}'")

    # Update goal impressions
    if goal_impressions is not None:
        if 'primaryGoal' not in line_item:
            line_item['primaryGoal'] = {
                'goalType': 'LIFETIME',
                'unitType': 'IMPRESSIONS'
            }
        old_goal = safe_get(line_item.get('primaryGoal', {}), 'units', 0)
        line_item['primaryGoal']['units'] = goal_impressions
        changes.append(f"primaryGoal.units: {old_goal} -> {goal_impressions}")

    # Update end date
    if end_year is not None and end_month is not None and end_day is not None:
        old_end = extract_date(safe_get(line_item, 'endDateTime'))
        line_item['endDateTime'] = {
            'date': {'year': end_year, 'month': end_month, 'day': end_day},
            'hour': 23,
            'minute': 59,
            'second': 59,
            'timeZoneId': 'Africa/Casablanca'
        }
        new_end = f"{end_year}-{end_month:02d}-{end_day:02d}"
        changes.append(f"endDateTime: '{old_end}' -> '{new_end}'")

    if not changes:
        return {"error": "No changes specified. Provide at least one field to update."}

    # Perform the update
    updated = line_item_service.updateLineItems([line_item])

    if not updated:
        return {"error": "Failed to update line item"}

    updated_li = updated[0]

    # Extract updated values for response
    end_date = extract_date(safe_get(updated_li, 'endDateTime'))

    return {
        "id": safe_get(updated_li, 'id'),
        "name": safe_get(updated_li, 'name'),
        "order_id": safe_get(updated_li, 'orderId'),
        "status": safe_get(updated_li, 'status'),
        "type": safe_get(updated_li, 'lineItemType'),
        "delivery_rate_type": safe_get(updated_li, 'deliveryRateType'),
        "priority": safe_get(updated_li, 'priority'),
        "cost_type": safe_get(updated_li, 'costType'),
        "cost_per_unit_micro": safe_get(updated_li.get('costPerUnit', {}), 'microAmount'),
        "currency_code": safe_get(updated_li.get('costPerUnit', {}), 'currencyCode'),
        "goal_impressions": safe_get(updated_li.get('primaryGoal', {}), 'units'),
        "end_date": end_date,
        "changes": changes,
        "message": f"Line item {line_item_id} updated successfully"
    }


def list_line_items_by_order(order_id: int) -> dict:
    """List all line items for an order.

    Args:
        order_id: The order ID

    Returns:
        dict with line items
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    statement = client.create_statement()
    statement = statement.Where("orderId = :orderId").WithBindVariable('orderId', order_id)

    response = line_item_service.getLineItemsByStatement(statement.ToStatement())

    if 'results' not in response:
        return {"line_items": [], "total": 0}

    line_items = []
    for li in response['results']:
        stats = safe_get(li, 'stats')
        impressions = safe_get(stats, 'impressionsDelivered', 0) or 0
        clicks = safe_get(stats, 'clicksDelivered', 0) or 0
        line_items.append({
            "id": safe_get(li, 'id'),
            "name": safe_get(li, 'name'),
            "status": safe_get(li, 'status'),
            "type": safe_get(li, 'lineItemType'),
            "impressions_delivered": impressions,
            "clicks_delivered": clicks
        })

    return {
        "order_id": order_id,
        "line_items": line_items,
        "total": len(line_items)
    }


def _perform_line_item_action(line_item_id: int, action_type: str) -> dict:
    """Perform an action on a line item.

    Args:
        line_item_id: The line item ID
        action_type: Action to perform (PauseLineItems, ResumeLineItems,
                     ArchiveLineItems, ApproveLineItems)

    Returns:
        dict with action result
    """
    client = get_gam_client()
    line_item_service = client.get_service('LineItemService')

    # Build statement for the specific line item
    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', line_item_id)

    # Create the action object
    action = {'xsi_type': action_type}

    # Perform the action
    result = line_item_service.performLineItemAction(
        action,
        statement.ToStatement()
    )

    if result and safe_get(result, 'numChanges', 0) > 0:
        # Fetch updated line item to return current status
        response = line_item_service.getLineItemsByStatement(statement.ToStatement())
        if 'results' in response and len(response['results']) > 0:
            li = response['results'][0]
            return {
                "success": True,
                "id": safe_get(li, 'id'),
                "name": safe_get(li, 'name'),
                "status": safe_get(li, 'status'),
                "action": action_type,
                "message": f"Line item {line_item_id} action '{action_type}' completed successfully"
            }

    return {
        "success": False,
        "id": line_item_id,
        "action": action_type,
        "error": f"Failed to perform action '{action_type}' on line item {line_item_id}. "
                 "The line item may not be in a valid state for this action."
    }


def pause_line_item(line_item_id: int) -> dict:
    """Pause a delivering line item.

    Args:
        line_item_id: The line item ID to pause

    Returns:
        dict with result of the pause action
    """
    return _perform_line_item_action(line_item_id, 'PauseLineItems')


def resume_line_item(line_item_id: int) -> dict:
    """Resume a paused line item.

    Args:
        line_item_id: The line item ID to resume

    Returns:
        dict with result of the resume action
    """
    return _perform_line_item_action(line_item_id, 'ResumeLineItems')


def archive_line_item(line_item_id: int) -> dict:
    """Archive a line item.

    Archived line items are hidden from the default UI views but can still
    be retrieved via API. This action cannot be undone via API.

    Args:
        line_item_id: The line item ID to archive

    Returns:
        dict with result of the archive action
    """
    return _perform_line_item_action(line_item_id, 'ArchiveLineItems')


def approve_line_item(line_item_id: int) -> dict:
    """Approve a line item that requires approval.

    This is used when the approval workflow is enabled in GAM.
    Line items in NEEDS_APPROVAL status can be approved to start delivery.

    Args:
        line_item_id: The line item ID to approve

    Returns:
        dict with result of the approve action
    """
    return _perform_line_item_action(line_item_id, 'ApproveLineItems')
