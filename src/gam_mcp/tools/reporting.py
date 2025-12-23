"""Reporting tools for Google Ad Manager."""

import logging
import time
import gzip
import io
from typing import Optional, List
from ..client import get_gam_client
from ..utils import safe_get

logger = logging.getLogger(__name__)

# Common report dimensions
DIMENSIONS = {
    "DATE": "DATE",
    "WEEK": "WEEK",
    "MONTH_AND_YEAR": "MONTH_AND_YEAR",
    "ORDER_ID": "ORDER_ID",
    "ORDER_NAME": "ORDER_NAME",
    "LINE_ITEM_ID": "LINE_ITEM_ID",
    "LINE_ITEM_NAME": "LINE_ITEM_NAME",
    "LINE_ITEM_TYPE": "LINE_ITEM_TYPE",
    "CREATIVE_ID": "CREATIVE_ID",
    "CREATIVE_NAME": "CREATIVE_NAME",
    "CREATIVE_SIZE": "CREATIVE_SIZE",
    "ADVERTISER_ID": "ADVERTISER_ID",
    "ADVERTISER_NAME": "ADVERTISER_NAME",
    "AD_UNIT_ID": "AD_UNIT_ID",
    "AD_UNIT_NAME": "AD_UNIT_NAME",
}

# Common report metrics (columns)
METRICS = {
    "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS": "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS",
    "TOTAL_LINE_ITEM_LEVEL_CLICKS": "TOTAL_LINE_ITEM_LEVEL_CLICKS",
    "TOTAL_LINE_ITEM_LEVEL_CTR": "TOTAL_LINE_ITEM_LEVEL_CTR",
    "TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE": "TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE",
    "TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE": "TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE",
    "TOTAL_INVENTORY_LEVEL_IMPRESSIONS": "TOTAL_INVENTORY_LEVEL_IMPRESSIONS",
    "TOTAL_AD_REQUESTS": "TOTAL_AD_REQUESTS",
    "TOTAL_RESPONSES_SERVED": "TOTAL_RESPONSES_SERVED",
    "TOTAL_FILL_RATE": "TOTAL_FILL_RATE",
}

# Date range types
DATE_RANGE_TYPES = {
    "TODAY": "TODAY",
    "YESTERDAY": "YESTERDAY",
    "LAST_WEEK": "LAST_WEEK",
    "LAST_MONTH": "LAST_MONTH",
    "LAST_3_MONTHS": "LAST_3_MONTHS",
    "REACH_LIFETIME": "REACH_LIFETIME",
    "CUSTOM_DATE": "CUSTOM_DATE",
}


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
) -> dict:
    """Run a delivery report for orders and line items.

    This is a preset report that returns impressions, clicks, CTR, and revenue
    broken down by order and line item.

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

    Returns:
        dict with report data including rows of delivery statistics
    """
    # Build dimensions
    dimensions = ["ORDER_ID", "ORDER_NAME", "LINE_ITEM_ID", "LINE_ITEM_NAME"]
    if include_date_breakdown:
        dimensions.insert(0, "DATE")

    # Build columns (metrics)
    columns = [
        "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS",
        "TOTAL_LINE_ITEM_LEVEL_CLICKS",
        "TOTAL_LINE_ITEM_LEVEL_CTR",
        "TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE",
    ]

    # Build filter
    filter_statement = None
    if order_id:
        filter_statement = f"ORDER_ID = {order_id}"
    if line_item_id:
        if filter_statement:
            filter_statement += f" AND LINE_ITEM_ID = {line_item_id}"
        else:
            filter_statement = f"LINE_ITEM_ID = {line_item_id}"

    return run_custom_report(
        dimensions=dimensions,
        columns=columns,
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
) -> dict:
    """Run an inventory report for ad units.

    This is a preset report that returns ad requests, impressions, fill rate
    broken down by ad unit.

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

    Returns:
        dict with report data including rows of inventory statistics
    """
    dimensions = ["AD_UNIT_ID", "AD_UNIT_NAME"]
    if include_date_breakdown:
        dimensions.insert(0, "DATE")

    columns = [
        "TOTAL_AD_REQUESTS",
        "TOTAL_INVENTORY_LEVEL_IMPRESSIONS",
        "TOTAL_RESPONSES_SERVED",
        "TOTAL_FILL_RATE",
    ]

    filter_statement = None
    if ad_unit_id:
        filter_statement = f"AD_UNIT_ID = {ad_unit_id}"

    return run_custom_report(
        dimensions=dimensions,
        columns=columns,
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


def run_custom_report(
    dimensions: List[str],
    columns: List[str],
    date_range_type: str = "LAST_WEEK",
    start_year: Optional[int] = None,
    start_month: Optional[int] = None,
    start_day: Optional[int] = None,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    end_day: Optional[int] = None,
    filter_statement: Optional[str] = None,
    timeout_seconds: int = 120
) -> dict:
    """Run a custom report with specified dimensions and metrics.

    Args:
        dimensions: List of dimension names (e.g., ["DATE", "ORDER_NAME", "LINE_ITEM_NAME"])
            Valid dimensions: DATE, WEEK, MONTH_AND_YEAR, ORDER_ID, ORDER_NAME,
            LINE_ITEM_ID, LINE_ITEM_NAME, LINE_ITEM_TYPE, CREATIVE_ID, CREATIVE_NAME,
            CREATIVE_SIZE, ADVERTISER_ID, ADVERTISER_NAME, AD_UNIT_ID, AD_UNIT_NAME
        columns: List of metric/column names (e.g., ["TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS"])
            Valid metrics: TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS, TOTAL_LINE_ITEM_LEVEL_CLICKS,
            TOTAL_LINE_ITEM_LEVEL_CTR, TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE,
            TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE, TOTAL_INVENTORY_LEVEL_IMPRESSIONS,
            TOTAL_AD_REQUESTS, TOTAL_RESPONSES_SERVED, TOTAL_FILL_RATE
        date_range_type: Date range type (TODAY, YESTERDAY, LAST_WEEK, LAST_MONTH,
            LAST_3_MONTHS, REACH_LIFETIME, CUSTOM_DATE)
        start_year: Start year for CUSTOM_DATE range
        start_month: Start month (1-12) for CUSTOM_DATE range
        start_day: Start day (1-31) for CUSTOM_DATE range
        end_year: End year for CUSTOM_DATE range
        end_month: End month (1-12) for CUSTOM_DATE range
        end_day: End day (1-31) for CUSTOM_DATE range
        filter_statement: Optional filter (e.g., "ORDER_ID = 12345")
        timeout_seconds: Maximum seconds to wait for report completion

    Returns:
        dict with report data including column headers and data rows
    """
    client = get_gam_client()
    report_service = client.get_service('ReportService')

    # Validate date range
    if date_range_type == "CUSTOM_DATE":
        if not all([start_year, start_month, start_day, end_year, end_month, end_day]):
            return {
                "error": "CUSTOM_DATE requires start_year, start_month, start_day, "
                         "end_year, end_month, and end_day parameters"
            }

    # Build report query
    report_query = {
        'dimensions': dimensions,
        'columns': columns,
        'dateRangeType': date_range_type,
    }

    # Add custom date range if specified
    if date_range_type == "CUSTOM_DATE":
        report_query['startDate'] = {
            'year': start_year,
            'month': start_month,
            'day': start_day
        }
        report_query['endDate'] = {
            'year': end_year,
            'month': end_month,
            'day': end_day
        }

    # Add filter if specified
    if filter_statement:
        report_query['statement'] = {
            'query': f"WHERE {filter_statement}"
        }

    # Create report job
    report_job = {'reportQuery': report_query}

    try:
        # Run the report
        report_job = report_service.runReportJob(report_job)
        report_job_id = report_job['id']
        logger.info(f"Report job started with ID: {report_job_id}")

        # Wait for report to complete
        start_time = time.time()
        status = None
        while time.time() - start_time < timeout_seconds:
            # getReportJobStatus returns a string directly (e.g., 'COMPLETED', 'IN_PROGRESS', 'FAILED')
            status = report_service.getReportJobStatus(report_job_id)

            if status == 'COMPLETED':
                logger.info(f"Report job {report_job_id} completed")
                break
            elif status == 'FAILED':
                return {
                    "error": f"Report job failed",
                    "job_id": report_job_id,
                    "status": status
                }

            time.sleep(2)  # Poll every 2 seconds
        else:
            return {
                "error": f"Report job timed out after {timeout_seconds} seconds",
                "job_id": report_job_id,
                "status": status
            }

        # Download the report
        export_format = 'CSV_DUMP'
        report_downloader = client.get_data_downloader()

        # Download to a BytesIO buffer
        buffer = io.BytesIO()
        report_downloader.DownloadReportToFile(report_job_id, export_format, buffer)

        # Read and decode the content
        buffer.seek(0)
        content = buffer.read()

        # Decompress if gzipped
        try:
            report_data = gzip.decompress(content).decode('utf-8')
        except (gzip.BadGzipFile, OSError):
            report_data = content.decode('utf-8')

        # Parse CSV data
        rows = _parse_csv_report(report_data)

        return {
            "success": True,
            "job_id": report_job_id,
            "date_range_type": date_range_type,
            "dimensions": dimensions,
            "columns": columns,
            "row_count": len(rows) - 1 if rows else 0,  # Exclude header row
            "headers": rows[0] if rows else [],
            "data": rows[1:] if rows else [],
            "message": f"Report completed with {len(rows) - 1 if rows else 0} data rows"
        }

    except Exception as e:
        logger.error(f"Error running report: {e}")
        return {
            "error": f"Failed to run report: {str(e)}"
        }


def _parse_csv_report(report_data: str) -> List[List[str]]:
    """Parse CSV report data into rows.

    Args:
        report_data: Raw CSV string from report download

    Returns:
        List of rows, where each row is a list of column values
    """
    rows = []
    for line in report_data.strip().split('\n'):
        if line:
            # Handle CSV parsing (simple split, handles most cases)
            # For complex CSV with quoted commas, a proper CSV parser would be needed
            values = []
            in_quotes = False
            current_value = ""
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    values.append(current_value.strip())
                    current_value = ""
                else:
                    current_value += char
            values.append(current_value.strip())
            rows.append(values)
    return rows


def get_available_dimensions() -> dict:
    """Get list of available report dimensions.

    Returns:
        dict with available dimension names and descriptions
    """
    return {
        "dimensions": list(DIMENSIONS.keys()),
        "description": "Available dimensions for custom reports"
    }


def get_available_metrics() -> dict:
    """Get list of available report metrics (columns).

    Returns:
        dict with available metric names and descriptions
    """
    return {
        "metrics": list(METRICS.keys()),
        "description": "Available metrics/columns for custom reports"
    }
