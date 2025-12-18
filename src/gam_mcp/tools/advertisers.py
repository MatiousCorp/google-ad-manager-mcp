"""Advertiser/Company tools for Google Ad Manager."""

import logging
from typing import Optional
from ..client import get_gam_client
from ..utils import safe_get

logger = logging.getLogger(__name__)


def find_advertiser(name: str) -> dict:
    """Find an advertiser by name.

    Args:
        name: Advertiser name to search for (partial match)

    Returns:
        dict with matching advertisers
    """
    client = get_gam_client()
    company_service = client.get_service('CompanyService')

    # Use bind variable for safe query (LIKE requires manual pattern)
    # Note: GAM PQL bind variables don't support LIKE patterns directly,
    # so we use a simple contains check with the bind variable
    statement = client.create_statement()
    statement = statement.Where(
        "name LIKE :name AND type = :type"
    ).WithBindVariable('name', f'%{name}%').WithBindVariable('type', 'ADVERTISER')

    response = company_service.getCompaniesByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"advertisers": [], "message": f"No advertiser found matching '{name}'"}

    advertisers = []
    for adv in response['results']:
        advertisers.append({
            "id": safe_get(adv, 'id'),
            "name": safe_get(adv, 'name'),
            "type": safe_get(adv, 'type'),
            "credit_status": safe_get(adv, 'creditStatus'),
            "external_id": safe_get(adv, 'externalId')
        })

    return {
        "advertisers": advertisers,
        "total": len(advertisers),
        "message": f"Found {len(advertisers)} advertiser(s) matching '{name}'"
    }


def get_advertiser(advertiser_id: int) -> dict:
    """Get advertiser details by ID.

    Args:
        advertiser_id: The advertiser/company ID

    Returns:
        dict with advertiser details
    """
    client = get_gam_client()
    company_service = client.get_service('CompanyService')

    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', advertiser_id)

    response = company_service.getCompaniesByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Advertiser {advertiser_id} not found"}

    adv = response['results'][0]

    return {
        "id": safe_get(adv, 'id'),
        "name": safe_get(adv, 'name'),
        "type": safe_get(adv, 'type'),
        "credit_status": safe_get(adv, 'creditStatus'),
        "external_id": safe_get(adv, 'externalId'),
        "address": safe_get(adv, 'address'),
        "email": safe_get(adv, 'email'),
        "comment": safe_get(adv, 'comment')
    }


def list_advertisers(limit: int = 100) -> dict:
    """List all advertisers.

    Args:
        limit: Maximum number of advertisers to return

    Returns:
        dict with advertisers list
    """
    client = get_gam_client()
    company_service = client.get_service('CompanyService')

    statement = client.create_statement()
    statement = statement.Where(
        "type = :type"
    ).WithBindVariable('type', 'ADVERTISER').Limit(limit)

    response = company_service.getCompaniesByStatement(statement.ToStatement())

    if 'results' not in response:
        return {"advertisers": [], "total": 0}

    advertisers = []
    for adv in response['results']:
        advertisers.append({
            "id": safe_get(adv, 'id'),
            "name": safe_get(adv, 'name'),
            "credit_status": safe_get(adv, 'creditStatus')
        })

    return {
        "advertisers": advertisers,
        "total": len(advertisers)
    }


def create_advertiser(
    name: str,
    email: Optional[str] = None,
    address: Optional[str] = None,
    comment: Optional[str] = None
) -> dict:
    """Create a new advertiser.

    Args:
        name: Advertiser name
        email: Optional email address
        address: Optional address
        comment: Optional comment

    Returns:
        dict with created advertiser details
    """
    client = get_gam_client()
    company_service = client.get_service('CompanyService')

    company = {
        'name': name,
        'type': 'ADVERTISER',
    }

    if email:
        company['email'] = email
    if address:
        company['address'] = address
    if comment:
        company['comment'] = comment

    created_companies = company_service.createCompanies([company])

    if not created_companies:
        return {"error": "Failed to create advertiser"}

    created = created_companies[0]

    return {
        "id": safe_get(created, 'id'),
        "name": safe_get(created, 'name'),
        "type": safe_get(created, 'type'),
        "message": f"Advertiser '{name}' created successfully"
    }


def find_or_create_advertiser(
    name: str,
    email: Optional[str] = None
) -> dict:
    """Find an advertiser by exact name or create if not found.

    Args:
        name: Exact advertiser name
        email: Optional email (used if creating)

    Returns:
        dict with advertiser details
    """
    client = get_gam_client()
    company_service = client.get_service('CompanyService')

    # Use bind variables for safe query
    statement = client.create_statement()
    statement = statement.Where(
        "name = :name AND type = :type"
    ).WithBindVariable('name', name).WithBindVariable('type', 'ADVERTISER')

    response = company_service.getCompaniesByStatement(statement.ToStatement())

    if 'results' in response and len(response['results']) > 0:
        adv = response['results'][0]
        return {
            "id": safe_get(adv, 'id'),
            "name": safe_get(adv, 'name'),
            "type": safe_get(adv, 'type'),
            "created": False,
            "message": f"Found existing advertiser '{name}'"
        }

    # Create new
    result = create_advertiser(name=name, email=email)
    if "error" not in result:
        result["created"] = True
    return result
