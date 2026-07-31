from __future__ import annotations

import csv
import json
import os
import re
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import Any, Iterable

from .models import Listing


def _rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("items", "listings", "results", "data"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
    raise ValueError("Expected a JSON list or an object with items/listings/results/data.")


def load_listings(path: str | Path) -> list[Listing]:
    source_path = Path(path)
    if source_path.suffix.lower() == ".csv":
        with source_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        rows = _rows_from_payload(json.loads(source_path.read_text(encoding="utf-8")))
    listings = [Listing.from_dict(row) for row in rows]
    missing = [index + 1 for index, listing in enumerate(listings) if not listing.listing_id]
    if missing:
        raise ValueError(f"Missing listing_id in rows: {missing[:10]}")
    duplicate_ids = sorted(
        listing_id
        for listing_id in {listing.listing_id for listing in listings}
        if sum(listing.listing_id == listing_id for listing in listings) > 1
    )
    if duplicate_ids:
        raise ValueError(f"Duplicate listing_id values: {duplicate_ids[:10]}")
    invalid_rows = [
        index + 1
        for index, listing in enumerate(listings)
        if listing.area_sotki <= 0
        or listing.price_rub <= 0
        or not (-90 <= listing.lat <= 90)
        or not (-180 <= listing.lon <= 180)
        or (listing.lat == 0 and listing.lon == 0)
    ]
    if invalid_rows:
        raise ValueError(
            "Rows require positive area/price and valid non-zero coordinates: "
            f"{invalid_rows[:10]}"
        )
    return listings


def _walk_json_ld(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json_ld(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_json_ld(value)


def _normalise_json_ld(node: dict[str, Any], source: str, index: int) -> dict[str, Any] | None:
    item_type = str(node.get("@type") or "")
    if item_type not in {"Product", "Offer", "Residence", "Place", "RealEstateListing"}:
        return None
    offer = node.get("offers") if isinstance(node.get("offers"), dict) else node
    geo = node.get("geo") if isinstance(node.get("geo"), dict) else {}
    area = node.get("floorSize") if isinstance(node.get("floorSize"), dict) else {}
    return {
        "listing_id": str(node.get("sku") or node.get("identifier") or f"{source}-{index}"),
        "source": source,
        "url": str(node.get("url") or offer.get("url") or ""),
        "title": str(node.get("name") or ""),
        "address": str(node.get("address") or ""),
        "pool": "Природа",
        "cluster": str(node.get("address") or "Не определён"),
        "lat": geo.get("latitude", 0),
        "lon": geo.get("longitude", 0),
        "area_sotki": area.get("value", 0),
        "price_rub": offer.get("price", 0),
        "land_category": "",
        "description": str(node.get("description") or ""),
        "photo_count": len(node.get("image", [])) if isinstance(node.get("image"), list) else 0,
    }


def collect_json_ld(
    search_urls: list[str],
    source: str,
    *,
    stealth: bool = False,
) -> list[Listing]:
    """
    Collect public JSON-LD only.

    Live mode is an explicit opt-in, robots.txt is checked, authentication/paywalls
    are not bypassed, and no CAPTCHA solver is enabled.
    """
    if os.environ.get("LAND_MONITOR_ALLOW_LIVE_SCRAPING", "").lower() != "true":
        raise RuntimeError("Set LAND_MONITOR_ALLOW_LIVE_SCRAPING=true after confirming authorization.")
    try:
        from scrapling.fetchers import DynamicFetcher, StealthyFetcher
    except ImportError as exc:
        raise RuntimeError("Install optional scraping dependencies: pip install '.[scraping]'") from exc

    rows: list[dict[str, Any]] = []
    for url in search_urls:
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        robots = urllib.robotparser.RobotFileParser()
        robots.set_url(robots_url)
        try:
            robots.read()
        except Exception as exc:
            raise RuntimeError(f"Could not verify robots.txt for {url}: {exc}") from exc
        if not robots.can_fetch("land-investment-monitor/0.1", url):
            raise PermissionError(f"robots.txt does not permit collection: {url}")

        if stealth:
            page = StealthyFetcher.fetch(url, headless=True, block_ads=True)
        else:
            page = DynamicFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                disable_resources=False,
            )
        scripts = page.css('script[type="application/ld+json"]::text').getall()
        for script in scripts:
            try:
                payload = json.loads(script)
            except json.JSONDecodeError:
                continue
            for node in _walk_json_ld(payload):
                row = _normalise_json_ld(node, source, len(rows) + 1)
                if row and row["url"]:
                    rows.append(row)

    deduplicated: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["url"] or row["listing_id"]
        deduplicated[key] = row
    return [Listing.from_dict(row) for row in deduplicated.values()]


def extract_cadastral_number(text: str) -> str:
    match = re.search(r"\b\d{2}:\d{2}:\d{5,7}:\d{1,6}\b", text or "")
    return match.group(0) if match else ""
