#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI tools to manage DNS on Cloudflare using Click.
Fully instrumented with logging, validation, and exception handling.

Supports reading CLOUDFLARE_API_TOKEN:
 - from the command line via --api-token
 - from the environment variable CLOUDFLARE_API_TOKEN

Usage:
    python cfmanager.py create-dns-record --zone-name example.com \
        --hostname "host.example.com" --type A --value "192.168.1.10"

    python cfmanager.py list-dns-zones
    python cfmanager.py list-dns-records --zone-name example.com
    python cfmanager.py remove-dns-record --zone-name example.com --record-name host.example.com
    python cfmanager.py export-dns-zone --zone-name example.com [--output example.com.zone]

Requires:
    pip install requests click
"""

import json
import logging
import os
from pathlib import Path
import click
import requests


# ------------------------------------------------------------
# Detailed logging configuration
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Helper for logging JSON responses
# ------------------------------------------------------------
def _log_response_json(response):
    """Pretty-print a JSON response body for logs, fallback to raw text."""
    try:
        parsed = response.json()
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        logger.error("Response JSON:\n%s", pretty)
    except ValueError:
        logger.error("Response text: %s", response.text)


# ------------------------------------------------------------
# Basic argument validation
# ------------------------------------------------------------
def validate_record_type(record_type):
    """Validate the DNS record type provided by the user."""
    valid_types = ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "PTR", "CAA"]
    if record_type.upper() not in valid_types:
        raise ValueError(
            f"Invalid type '{record_type}'. Allowed values: {', '.join(valid_types)}"
        )
    return record_type.upper()


# ------------------------------------------------------------
# Token retrieval (command line or environment variable)
# ------------------------------------------------------------
def get_api_token(cli_token):
    """Retrieve the API token from CLI or environment."""
    token = cli_token or os.getenv("CLOUDFLARE_API_TOKEN")
    if token:
        return token

    message = "No token found! Provide --api-token or set CLOUDFLARE_API_TOKEN."
    logger.error(message)
    raise click.ClickException(message)


# ------------------------------------------------------------
# Create DNS record
# ------------------------------------------------------------
def create_dns_record_api(zone_id, api_token, hostname, record_type, value):
    """Create a DNS record using the Cloudflare API."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

    payload = {
        "type": record_type,
        "name": hostname,
        "content": value,
        "ttl": 300,  # 5 minutes
        "proxied": False,  # change to True if you want Cloudflare proxying
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    logger.info("Starting DNS record creation on Cloudflare...")
    logger.info("Zone (zone_id): %s", zone_id)
    logger.info("Hostname: %s", hostname)
    logger.info("Type: %s", record_type)
    logger.info("Value: %s", value)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.exceptions.RequestException as e:
        message = f"Communication error with Cloudflare: {e}"
        logger.error(message)
        raise click.ClickException(message) from e

    if not response.ok:
        message = f"HTTP error while creating record: {response.status_code}"
        logger.error(message)
        _log_response_json(response)
        raise click.ClickException(message)

    data = response.json()

    if not data.get("success", False):
        message = "Failed to create the DNS record on Cloudflare."
        logger.error(message)
        logger.error("Errors: %s", data.get("errors"))
        _log_response_json(response)
        raise click.ClickException(message)

    logger.info("DNS record created successfully!")
    logger.info("Record ID: %s", data["result"]["id"])
    logger.debug("Full response: %s", data)

    return data


# ------------------------------------------------------------
# List DNS zones
# ------------------------------------------------------------
def list_dns_zones_api(api_token, items_per_page=50, zone_name=None):
    """List DNS zones and return (name, id) pairs, optionally filtered by name."""
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    zones = []
    page = 1
    while True:
        try:
            params = {"page": page, "per_page": items_per_page}
            if zone_name:
                params["name"] = zone_name
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=15,
            )
        except requests.exceptions.RequestException as err:
            logger.error("Communication error with Cloudflare: %s", err)
            raise click.ClickException(
                f"Communication error with Cloudflare: {err}"
            ) from err

        if not response.ok:
            logger.error("HTTP error while listing zones: %s", response.status_code)
            _log_response_json(response)
            raise click.ClickException(
                f"HTTP error while listing zones: {response.status_code}"
            )

        data = response.json()
        if not data.get("success", False):
            logger.error("Failed to list zones on Cloudflare.")
            logger.error("Errors: %s", data.get("errors"))
            _log_response_json(response)
            raise click.ClickException("Failed to list zones on Cloudflare.")

        zones.extend(
            (item.get("name"), item.get("id")) for item in data.get("result", [])
        )

        result_info = data.get("result_info", {})
        if result_info.get("page", page) >= result_info.get(
            "total_pages", result_info.get("page", page)
        ):
            break
        page += 1

    if zone_name and not zones:
        logger.info("No zones found for the name: %s", zone_name)
        return zones

    logger.info("Total zones found: %s", len(zones))
    name_width = max((len(name or "") for name, _ in zones), default=0)
    for name, zone_id in zones:
        logger.info("Zone: %-*s | ID: %s", name_width, name, zone_id)

    return zones


# ------------------------------------------------------------
# Utility to get zone_id by name
# ------------------------------------------------------------
def get_zone_id_by_name(api_token, zone_name):
    """Get the zone_id from the exact zone name."""
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    params = {"name": zone_name, "per_page": 1}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.exceptions.RequestException as err:
        logger.error("Communication error with Cloudflare: %s", err)
        raise click.ClickException(
            f"Communication error with Cloudflare: {err}"
        ) from err

    if not response.ok:
        logger.error("HTTP error while fetching zone: %s", response.status_code)
        _log_response_json(response)
        raise click.ClickException(
            f"HTTP error while fetching zone: {response.status_code}"
        )

    data = response.json()
    if not data.get("success", False):
        logger.error("Failed to fetch zone on Cloudflare.")
        logger.error("Errors: %s", data.get("errors"))
        _log_response_json(response)
        raise click.ClickException("Failed to fetch zone on Cloudflare.")

    results = data.get("result", [])
    if not results:
        raise click.ClickException(f"Zone not found: {zone_name}")

    zone_id = results[0].get("id")
    logger.info("Zone found: %s | ID: %s", zone_name, zone_id)
    return zone_id


# ------------------------------------------------------------
# Find and remove DNS record
# ------------------------------------------------------------
def find_dns_record_by_name(zone_id, api_token, record_name):
    """Find a DNS record by exact name within a zone."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    params = {"name": record_name, "per_page": 100}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.exceptions.RequestException as err:
        logger.error("Communication error with Cloudflare: %s", err)
        raise click.ClickException(
            f"Communication error with Cloudflare: {err}"
        ) from err

    if not response.ok:
        logger.error("HTTP error while fetching DNS record: %s", response.status_code)
        _log_response_json(response)
        raise click.ClickException(
            f"HTTP error while fetching DNS record: {response.status_code}"
        )

    data = response.json()
    if not data.get("success", False):
        logger.error("Failed to fetch DNS record on Cloudflare.")
        _log_response_json(response)
        raise click.ClickException("Failed to fetch DNS record on Cloudflare.")

    records = [rec for rec in data.get("result", []) if rec.get("name") == record_name]

    if not records:
        raise click.ClickException(f"DNS record not found: {record_name}")

    if len(records) > 1:
        raise click.ClickException(
            f"Multiple DNS records found for {record_name}; refine the query."
        )

    record = records[0]
    logger.info(
        "Record found: %s | Type: %s | Content: %s | ID: %s",
        record.get("name"),
        record.get("type"),
        record.get("content"),
        record.get("id"),
    )
    return record


def remove_dns_record_api(zone_id, api_token, record_id):
    """Remove a DNS record using the Cloudflare API."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.delete(url, headers=headers, timeout=15)
    except requests.exceptions.RequestException as err:
        logger.error("Communication error with Cloudflare: %s", err)
        raise click.ClickException(
            f"Communication error with Cloudflare: {err}"
        ) from err

    if not response.ok:
        message = f"HTTP error while deleting record: {response.status_code}"
        logger.error(message)
        _log_response_json(response)
        raise click.ClickException(message)

    data = response.json()
    if not data.get("success", False):
        message = "Failed to delete the DNS record on Cloudflare."
        logger.error(message)
        _log_response_json(response)
        raise click.ClickException(message)

    logger.info("DNS record deleted successfully!")
    return data


def export_dns_zone_api(zone_id, api_token):
    """Export DNS records of a zone in BIND format."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/export"
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.RequestException as err:
        logger.error("Communication error with Cloudflare: %s", err)
        raise click.ClickException(
            f"Communication error with Cloudflare: {err}"
        ) from err

    if not response.ok:
        logger.error("HTTP error while exporting zone: %s", response.status_code)
        _log_response_json(response)
        raise click.ClickException(
            f"HTTP error while exporting zone: {response.status_code}"
        )

    return response.text


def list_dns_records_api(zone_id, api_token, items_per_page=100):
    """List DNS records for a zone."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    records = []
    page = 1
    while True:
        params = {"page": page, "per_page": items_per_page}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.exceptions.RequestException as err:
            logger.error("Communication error with Cloudflare: %s", err)
            raise click.ClickException(
                f"Communication error with Cloudflare: {err}"
            ) from err

        if not response.ok:
            logger.error("HTTP error while listing DNS records: %s", response.status_code)
            _log_response_json(response)
            raise click.ClickException(
                f"HTTP error while listing DNS records: {response.status_code}"
            )

        data = response.json()
        if not data.get("success", False):
            logger.error("Failed to list DNS records on Cloudflare.")
            _log_response_json(response)
            raise click.ClickException("Failed to list DNS records on Cloudflare.")

        records.extend(data.get("result", []))

        info = data.get("result_info", {})
        if info.get("page", page) >= info.get("total_pages", info.get("page", page)):
            break
        page += 1

    logger.info("Total DNS records found: %s", len(records))
    return records


def _print_dns_records_table(records):
    """Pretty-print DNS records as a table."""
    if not records:
        click.echo("No DNS records found.")
        return

    headers = ["HOSTNAME", "TYPE", "DESTINATION"]
    max_dest_width = 80  # avoid overly wide tables for very long values

    def _shorten(value, limit):
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    rows = []
    for rec in records:
        name = str(rec.get("name", ""))
        rtype = str(rec.get("type", ""))
        content_raw = str(rec.get("content", ""))
        if rtype.upper() == "MX":
            priority = rec.get("priority")
            if priority is not None:
                content_raw = f"{priority} {content_raw}"
        content = _shorten(content_raw, max_dest_width)
        rows.append([name, rtype, content])

    col_widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(headers))
    ]
    fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)

    click.echo(fmt.format(*headers))
    click.echo("-+-".join("-" * w for w in col_widths))
    for row in rows:
        click.echo(fmt.format(*row))


# ------------------------------------------------------------
# CLI with Click
# ------------------------------------------------------------
def validate_record_type_callback(_ctx, _param, value):
    """Validate record type for Click options."""
    try:
        return validate_record_type(value)
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from exc


@click.group()
def cli():
    """CLI tools for DNS management on Cloudflare."""


@cli.command(name="create-dns-record")
@click.option("--zone-name", required=True, help="Zone name in Cloudflare.")
@click.option(
    "--api-token",
    envvar="CLOUDFLARE_API_TOKEN",
    help="API token with dns.edit permission (or set CLOUDFLARE_API_TOKEN).",
)
@click.option("--hostname", required=True, help="Full hostname (e.g., api.example.com).")
@click.option(
    "--type",
    "record_type",
    required=True,
    callback=validate_record_type_callback,
    help="Record type (A, AAAA, CNAME, TXT, MX, NS, SRV, PTR, CAA).",
)
@click.option("--value", required=True, help="IP address or target of the DNS record.")
def create_dns_record(zone_name, api_token, hostname, record_type, value):
    """Create a host in a specific DNS zone."""
    ctx = click.get_current_context()
    try:
        token = get_api_token(api_token)
        zone_id = get_zone_id_by_name(token, zone_name)
        response = create_dns_record_api(
            api_token=token,
            hostname=hostname,
            record_type=record_type,
            value=value,
            zone_id=zone_id,
        )
        click.echo(json.dumps(response, indent=2))
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}, indent=2), err=True)
        ctx.exit(1)


@cli.command(name="list-dns-zones")
@click.option(
    "--api-token",
    envvar="CLOUDFLARE_API_TOKEN",
    help="API token with zone read permission (or set CLOUDFLARE_API_TOKEN).",
)
@click.option(
    "--page-size",
    default=50,
    show_default=True,
    help="Number of zones per page in the paginated request.",
)
@click.option(
    "--zone-name",
    help="Exact zone name to filter (e.g., example.com).",
)
def list_dns_zones(api_token, page_size, zone_name):
    """List DNS zones (all or filtered by name) and show their names and IDs."""
    ctx = click.get_current_context()
    try:
        token = get_api_token(api_token)
        zones = list_dns_zones_api(
            api_token=token,
            items_per_page=page_size,
            zone_name=zone_name,
        )
        zones_json = [{"name": name, "id": zone_id} for name, zone_id in zones]
        click.echo(json.dumps(zones_json, indent=2))
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}, indent=2), err=True)
        ctx.exit(1)


@cli.command(name="remove-dns-record")
@click.option("--zone-name", required=True, help="Zone name in Cloudflare.")
@click.option(
    "--api-token",
    envvar="CLOUDFLARE_API_TOKEN",
    help="API token with dns.edit permission (or set CLOUDFLARE_API_TOKEN).",
)
@click.option(
    "--record-name",
    required=True,
    help="Full record name to remove (e.g., passbolt.example.com).",
)
def remove_dns_record(zone_name, api_token, record_name):
    """Remove a DNS record from a specific zone after user confirmation."""
    ctx = click.get_current_context()
    try:
        token = get_api_token(api_token)
        zone_id = get_zone_id_by_name(token, zone_name)
        record = find_dns_record_by_name(zone_id, token, record_name)

        prompt = (
            f"Remove record '{record_name}' (type {record.get('type')}) "
            f"from zone '{zone_name}'?"
        )
        if not click.confirm(prompt, default=False):
            click.echo(json.dumps({"status": "cancelled"}, indent=2))
            return

        response = remove_dns_record_api(zone_id, token, record.get("id"))
        click.echo(json.dumps(response, indent=2))
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}, indent=2), err=True)
        ctx.exit(1)


@cli.command(name="list-dns-records")
@click.option("--zone-name", required=True, help="Zone name in Cloudflare.")
@click.option(
    "--api-token",
    envvar="CLOUDFLARE_API_TOKEN",
    help="API token with dns.read permission (or set CLOUDFLARE_API_TOKEN).",
)
@click.option(
    "--page-size",
    default=100,
    show_default=True,
    help="Number of records per page in the paginated request.",
)
def list_dns_records(zone_name, api_token, page_size):
    """List DNS records of a zone in a table."""
    ctx = click.get_current_context()
    try:
        token = get_api_token(api_token)
        zone_id = get_zone_id_by_name(token, zone_name)
        records = list_dns_records_api(zone_id, token, items_per_page=page_size)
        _print_dns_records_table(records)
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}, indent=2), err=True)
        ctx.exit(1)


@cli.command(name="export-dns-zone")
@click.option("--zone-name", required=True, help="Zone name in Cloudflare.")
@click.option(
    "--api-token",
    envvar="CLOUDFLARE_API_TOKEN",
    help="API token with dns.read permission (or set CLOUDFLARE_API_TOKEN).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output file path (defaults to <zone-name>.zone).",
)
def export_dns_zone(zone_name, api_token, output_path):
    """Export DNS records of a zone to a BIND9-style file."""
    ctx = click.get_current_context()
    try:
        token = get_api_token(api_token)
        zone_id = get_zone_id_by_name(token, zone_name)
        zone_bind = export_dns_zone_api(zone_id, token)

        if output_path:
            path = Path(output_path)
        else:
            safe_name = zone_name.replace("/", "_")
            path = Path(f"{safe_name}.zone")

        path.write_text(zone_bind, encoding="utf-8")
        click.echo(json.dumps({"status": "ok", "file": str(path)}, indent=2))
    except Exception as exc:
        click.echo(json.dumps({"error": str(exc)}, indent=2), err=True)
        ctx.exit(1)


# ------------------------------------------------------------
# Execution
# ------------------------------------------------------------
if __name__ == "__main__":
    cli()
