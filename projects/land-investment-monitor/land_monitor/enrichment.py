from __future__ import annotations

import csv
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

from .models import FeaturePoint, Goal, Listing


EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))


def load_feature_points(path: str | Path | None) -> list[FeaturePoint]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("points", payload) if isinstance(payload, dict) else payload
    return [FeaturePoint.from_dict(row) for row in rows]


def load_cadastral_values(path: str | Path | None) -> dict[str, float]:
    if not path:
        return {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return {
            row["cadastral_number"].strip(): float(row["cadastral_value_rub"])
            for row in csv.DictReader(handle)
            if row.get("cadastral_number") and row.get("cadastral_value_rub")
        }


def _nearest(
    listing: Listing, points: list[FeaturePoint], kind: str
) -> tuple[float | None, FeaturePoint | None]:
    candidates = [point for point in points if point.kind == kind]
    if not candidates:
        return None, None
    distance, point = min(
        (
            haversine_km(listing.lat, listing.lon, candidate.lat, candidate.lon),
            candidate,
        )
        for candidate in candidates
    )
    return distance, point


def estimate_route(listing: Listing, goal: Goal) -> tuple[float, float, bool]:
    """Conservative offline estimate; flagged so it is never mistaken for routed travel."""
    straight = haversine_km(listing.lat, listing.lon, goal.target_lat, goal.target_lon)
    road_distance = straight * 1.35
    minutes = road_distance / 45.0 * 60.0 + 10.0
    return road_distance, minutes, True


def osrm_route(
    listing: Listing,
    goal: Goal,
    base_url: str = "https://router.project-osrm.org",
    timeout_seconds: int = 20,
) -> tuple[float, float, bool]:
    """Optional live route. The caller must confirm the endpoint's usage policy."""
    coordinates = f"{listing.lon},{listing.lat};{goal.target_lon},{goal.target_lat}"
    url = (
        f"{base_url.rstrip('/')}/route/v1/driving/{coordinates}?"
        + urllib.parse.urlencode({"overview": "false", "steps": "false"})
    )
    request = urllib.request.Request(url, headers={"User-Agent": "land-investment-monitor/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    route = payload["routes"][0]
    return route["distance"] / 1000.0, route["duration"] / 60.0, False


def enrich_listing(
    listing: Listing,
    goal: Goal,
    points: list[FeaturePoint],
    cadastral_values: dict[str, float],
    use_live_routing: bool = False,
) -> Listing:
    water_distance, water_point = _nearest(listing, points, "water")
    station_distance, _ = _nearest(listing, points, "station")
    infrastructure_distance, _ = _nearest(listing, points, "infrastructure")
    future_distance, _ = _nearest(listing, points, "future_growth")
    adverse_distance, _ = _nearest(listing, points, "adverse")

    if use_live_routing:
        try:
            route_distance, route_minutes, route_is_estimate = osrm_route(listing, goal)
        except Exception:
            route_distance, route_minutes, route_is_estimate = estimate_route(listing, goal)
    else:
        route_distance, route_minutes, route_is_estimate = estimate_route(listing, goal)

    cadastral = listing.cadastral_value_rub
    if cadastral is None and listing.cadastral_number:
        cadastral = cadastral_values.get(listing.cadastral_number)

    return listing.with_updates(
        cadastral_value_rub=cadastral,
        distance_to_water_km=(
            listing.distance_to_water_km
            if listing.distance_to_water_km is not None
            else water_distance
        ),
        water_type=listing.water_type or (water_point.subtype if water_point else ""),
        distance_to_station_km=(
            listing.distance_to_station_km
            if listing.distance_to_station_km is not None
            else station_distance
        ),
        distance_to_infrastructure_km=(
            listing.distance_to_infrastructure_km
            if listing.distance_to_infrastructure_km is not None
            else infrastructure_distance
        ),
        distance_to_future_growth_km=(
            listing.distance_to_future_growth_km
            if listing.distance_to_future_growth_km is not None
            else future_distance
        ),
        distance_to_adverse_zone_km=(
            listing.distance_to_adverse_zone_km
            if listing.distance_to_adverse_zone_km is not None
            else adverse_distance
        ),
        route_distance_km=route_distance,
        route_minutes=route_minutes,
        route_is_estimate=route_is_estimate,
    )
