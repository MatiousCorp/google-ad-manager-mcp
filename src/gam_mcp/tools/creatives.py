"""Creative tools for Google Ad Manager."""

import base64
import logging
import re
from pathlib import Path
from typing import Optional, List
from ..client import get_gam_client
from ..utils import safe_get

logger = logging.getLogger(__name__)


def extract_size_from_filename(filename: str) -> tuple[Optional[int], Optional[int]]:
    """Extract size (e.g., '300x250') from filename.

    Args:
        filename: The filename to parse

    Returns:
        Tuple of (width, height) or (None, None) if not found
    """
    match = re.search(r'(\d+)x(\d+)', filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def upload_creative(
    file_path: str,
    advertiser_id: int,
    click_through_url: str,
    creative_name: Optional[str] = None,
    override_size_width: Optional[int] = None,
    override_size_height: Optional[int] = None
) -> dict:
    """Upload an image creative to Ad Manager.

    Args:
        file_path: Path to the image file
        advertiser_id: ID of the advertiser
        click_through_url: Destination URL when creative is clicked
        creative_name: Optional name for the creative (defaults to auto-generated)
        override_size_width: Optional width to override the creative size (for serving into different slot)
        override_size_height: Optional height to override the creative size (for serving into different slot)

    Returns:
        dict with created creative details
    """
    client = get_gam_client()
    creative_service = client.get_service('CreativeService')

    path = Path(file_path)
    filename = path.name

    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    # Read and encode image
    with open(path, 'rb') as f:
        image_data = f.read()

    image_data_base64 = base64.b64encode(image_data).decode('utf-8')

    # Extract size from filename
    width, height = extract_size_from_filename(filename)

    if not width or not height:
        return {"error": f"Could not extract size from filename: {filename}. Expected format like '300x250'"}

    # Determine creative size (use override if provided)
    creative_width = override_size_width if override_size_width else width
    creative_height = override_size_height if override_size_height else height
    use_override = override_size_width is not None and override_size_height is not None

    # Generate name if not provided
    if creative_name is None:
        creative_name = f"Creative - {creative_width}x{creative_height} - {path.stem}"

    creative = {
        'xsi_type': 'ImageCreative',
        'name': creative_name,
        'advertiserId': advertiser_id,
        'destinationUrl': click_through_url,
        'size': {
            'width': creative_width,
            'height': creative_height,
            'isAspectRatio': False
        },
        'primaryImageAsset': {
            'assetByteArray': image_data_base64,
            'fileName': filename
        }
    }

    # Set overrideSize when using different dimensions than the actual image
    if use_override:
        creative['overrideSize'] = True

    created_creatives = creative_service.createCreatives([creative])

    if not created_creatives:
        return {"error": "Failed to create creative"}

    created = created_creatives[0]

    result = {
        "id": safe_get(created, 'id'),
        "name": safe_get(created, 'name'),
        "advertiser_id": advertiser_id,
        "size": f"{creative_width}x{creative_height}",
        "click_through_url": click_through_url,
        "message": f"Creative '{creative_name}' uploaded successfully"
    }

    if use_override:
        result["original_size"] = f"{width}x{height}"
        result["override_size"] = True

    return result


def upload_creative_from_base64(
    image_base64: str,
    filename: str,
    advertiser_id: int,
    click_through_url: str,
    width: int,
    height: int,
    creative_name: Optional[str] = None
) -> dict:
    """Upload an image creative from base64 data.

    Args:
        image_base64: Base64 encoded image data
        filename: Original filename
        advertiser_id: ID of the advertiser
        click_through_url: Destination URL when creative is clicked
        width: Image width
        height: Image height
        creative_name: Optional name for the creative

    Returns:
        dict with created creative details
    """
    client = get_gam_client()
    creative_service = client.get_service('CreativeService')

    if creative_name is None:
        creative_name = f"Creative - {width}x{height}"

    creative = {
        'xsi_type': 'ImageCreative',
        'name': creative_name,
        'advertiserId': advertiser_id,
        'destinationUrl': click_through_url,
        'size': {
            'width': width,
            'height': height,
            'isAspectRatio': False
        },
        'primaryImageAsset': {
            'assetByteArray': image_base64,
            'fileName': filename
        }
    }

    created_creatives = creative_service.createCreatives([creative])

    if not created_creatives:
        return {"error": "Failed to create creative"}

    created = created_creatives[0]

    return {
        "id": created['id'],
        "name": created['name'],
        "advertiser_id": advertiser_id,
        "size": f"{width}x{height}",
        "message": f"Creative uploaded successfully"
    }


def associate_creative_with_line_item(
    creative_id: int,
    line_item_id: int,
    size_override_width: Optional[int] = None,
    size_override_height: Optional[int] = None
) -> dict:
    """Associate a creative with a line item.

    Args:
        creative_id: The creative ID
        line_item_id: The line item ID
        size_override_width: Optional width for size override
        size_override_height: Optional height for size override

    Returns:
        dict with association details
    """
    client = get_gam_client()
    lica_service = client.get_service('LineItemCreativeAssociationService')

    lica = {
        'creativeId': creative_id,
        'lineItemId': line_item_id,
    }

    if size_override_width and size_override_height:
        lica['sizes'] = [{
            'width': size_override_width,
            'height': size_override_height,
            'isAspectRatio': False
        }]

    created_licas = lica_service.createLineItemCreativeAssociations([lica])

    if not created_licas:
        return {"error": "Failed to create creative association"}

    return {
        "creative_id": creative_id,
        "line_item_id": line_item_id,
        "size_override": f"{size_override_width}x{size_override_height}" if size_override_width else None,
        "message": f"Creative {creative_id} associated with line item {line_item_id}"
    }


def upload_and_associate_creative(
    file_path: str,
    advertiser_id: int,
    line_item_id: int,
    click_through_url: str,
    creative_name: Optional[str] = None
) -> dict:
    """Upload a creative and associate it with a line item in one operation.

    Args:
        file_path: Path to the image file
        advertiser_id: ID of the advertiser
        line_item_id: ID of the line item
        click_through_url: Destination URL
        creative_name: Optional name for the creative

    Returns:
        dict with both upload and association results
    """
    # First upload
    upload_result = upload_creative(
        file_path=file_path,
        advertiser_id=advertiser_id,
        click_through_url=click_through_url,
        creative_name=creative_name
    )

    if "error" in upload_result:
        return upload_result

    creative_id = upload_result["id"]

    # Then associate
    assoc_result = associate_creative_with_line_item(
        creative_id=creative_id,
        line_item_id=line_item_id
    )

    if "error" in assoc_result:
        return {
            "creative": upload_result,
            "association_error": assoc_result["error"]
        }

    return {
        "creative_id": creative_id,
        "creative_name": upload_result["name"],
        "size": upload_result["size"],
        "line_item_id": line_item_id,
        "click_through_url": click_through_url,
        "message": f"Creative uploaded and associated with line item {line_item_id}"
    }


def bulk_upload_creatives(
    folder_path: str,
    advertiser_id: int,
    line_item_id: int,
    click_through_url: str,
    name_prefix: Optional[str] = None
) -> dict:
    """Upload all creatives from a folder and associate with a line item.

    Args:
        folder_path: Path to folder containing image files
        advertiser_id: ID of the advertiser
        line_item_id: ID of the line item
        click_through_url: Destination URL
        name_prefix: Optional prefix for creative names

    Returns:
        dict with upload results
    """
    folder = Path(folder_path)

    if not folder.exists():
        return {"error": f"Folder not found: {folder_path}"}

    # Find all image files
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.JPG', '*.JPEG', '*.PNG', '*.GIF']
    files = []
    for ext in extensions:
        files.extend(folder.glob(ext))

    if not files:
        return {"error": f"No image files found in {folder_path}"}

    results = {
        "folder": folder_path,
        "line_item_id": line_item_id,
        "advertiser_id": advertiser_id,
        "uploaded": [],
        "failed": [],
        "total_files": len(files)
    }

    for file_path in sorted(files):
        creative_name = None
        if name_prefix:
            width, height = extract_size_from_filename(file_path.name)
            if width and height:
                creative_name = f"{name_prefix} - {width}x{height}"

        result = upload_and_associate_creative(
            file_path=str(file_path),
            advertiser_id=advertiser_id,
            line_item_id=line_item_id,
            click_through_url=click_through_url,
            creative_name=creative_name
        )

        if "error" in result:
            results["failed"].append({
                "file": file_path.name,
                "error": result["error"]
            })
        else:
            results["uploaded"].append({
                "file": file_path.name,
                "creative_id": result["creative_id"],
                "size": result["size"]
            })

    results["success_count"] = len(results["uploaded"])
    results["fail_count"] = len(results["failed"])
    results["message"] = f"Uploaded {results['success_count']} of {results['total_files']} creatives"

    return results


def get_creative(creative_id: int) -> dict:
    """Get creative details by ID.

    Args:
        creative_id: The creative ID

    Returns:
        dict with creative details
    """
    client = get_gam_client()
    creative_service = client.get_service('CreativeService')

    statement = client.create_statement()
    statement = statement.Where("id = :id").WithBindVariable('id', creative_id)

    response = creative_service.getCreativesByStatement(statement.ToStatement())

    if 'results' not in response or len(response['results']) == 0:
        return {"error": f"Creative {creative_id} not found"}

    creative = response['results'][0]
    size = safe_get(creative, 'size')

    return {
        "id": safe_get(creative, 'id'),
        "name": safe_get(creative, 'name'),
        "advertiser_id": safe_get(creative, 'advertiserId'),
        "size": f"{safe_get(size, 'width')}x{safe_get(size, 'height')}" if size else None,
        "type": safe_get(creative, 'Creative.Type'),
        "destination_url": safe_get(creative, 'destinationUrl')
    }


def list_creatives_by_advertiser(advertiser_id: int, limit: int = 100) -> dict:
    """List creatives for an advertiser.

    Args:
        advertiser_id: The advertiser ID
        limit: Maximum number of creatives to return

    Returns:
        dict with creatives list
    """
    client = get_gam_client()
    creative_service = client.get_service('CreativeService')

    statement = client.create_statement()
    statement = statement.Where(
        "advertiserId = :advertiserId"
    ).WithBindVariable('advertiserId', advertiser_id).Limit(limit)

    response = creative_service.getCreativesByStatement(statement.ToStatement())

    if 'results' not in response:
        return {"creatives": [], "total": 0}

    creatives = []
    for c in response['results']:
        size = safe_get(c, 'size')
        creatives.append({
            "id": safe_get(c, 'id'),
            "name": safe_get(c, 'name'),
            "size": f"{safe_get(size, 'width')}x{safe_get(size, 'height')}" if size else None,
            "type": safe_get(c, 'Creative.Type')
        })

    return {
        "advertiser_id": advertiser_id,
        "creatives": creatives,
        "total": len(creatives)
    }
