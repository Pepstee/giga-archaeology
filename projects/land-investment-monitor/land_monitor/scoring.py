from __future__ import annotations

import statistics

from .enrichment import haversine_km
from .models import Goal, Listing, ScoredListing


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    denominator = sum(weights.get(key, 0.0) for key in values)
    if denominator <= 0:
        return 0.0
    return sum(values[key] * weights.get(key, 0.0) for key in values) / denominator


def _price_per_sotka(listing: Listing) -> float:
    return listing.price_rub / listing.area_sotki if listing.area_sotki > 0 else 0.0


def _hard_filters(listing: Listing, goal: Goal) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if listing.area_sotki < goal.min_area_sotki:
        reasons.append(f"площадь < {goal.min_area_sotki:g} соток")
    if goal.max_budget_rub is not None and listing.price_rub > goal.max_budget_rub:
        reasons.append("цена выше бюджета")
    if goal.allowed_land_categories and not any(
        allowed.lower() in listing.land_category.lower()
        for allowed in goal.allowed_land_categories
    ):
        reasons.append("категория земли не соответствует фильтру")
    if goal.exclude_mandatory_fees and (
        listing.has_mandatory_fees is True
        or (listing.annual_fees_rub is not None and listing.annual_fees_rub > 0)
    ):
        reasons.append("есть обязательные взносы")
    if (
        listing.distance_to_adverse_zone_km is not None
        and listing.distance_to_adverse_zone_km < goal.adverse_exclusion_radius_km
        and listing.pool == "Безопасность"
    ):
        reasons.append("неблагоприятная зона ближе порога")
    return not reasons, reasons


def _soul_score(listing: Listing, pps: float, local_median: float, goal: Goal) -> float:
    water = (
        _clamp(100 - 25 * listing.distance_to_water_km)
        if listing.distance_to_water_km is not None
        else 0.0
    )
    tree = 100.0 if any("дуб" in tree or "листвен" in tree for tree in listing.trees) else (
        65.0 if listing.trees else 0.0
    )
    area = _clamp(listing.area_sotki / max(goal.ideal_area_sotki, 1) * 100)
    price = _clamp((local_median - pps) / local_median * 100 + 60) if local_median else 50.0
    access = 0.0
    access += 35 if listing.asphalt_access is True else 0
    access += 25 if any("электр" in value for value in listing.utilities) else 0
    access += 25 if any("газ" in value for value in listing.utilities) else 0
    access += 15 if listing.security is True else 0
    return _weighted(
        {
            "price": price,
            "water": water,
            "trees": tree,
            "area": area,
            "access_and_utilities": access,
        },
        goal.soul_weights,
    )


def _investment_score(
    listing: Listing,
    undervaluation: float,
    cadastral_discount: float,
    goal: Goal,
) -> float:
    urgency = _clamp(len(listing.urgency_markers) * 35)
    presentation = 100.0 if listing.photo_count < 3 else 65.0 if listing.photo_count < 5 else 0.0
    future = (
        _clamp(100 - 50 * listing.distance_to_future_growth_km)
        if listing.distance_to_future_growth_km is not None
        else 0.0
    )
    base = _weighted(
        {
            "undervaluation": _clamp(undervaluation / 0.40 * 100),
            "cadastral_discount": _clamp(cadastral_discount / 0.35 * 100),
            "urgency": urgency,
            "poor_presentation": presentation,
            "future_growth": future,
        },
        goal.investment_weights,
    )
    if (
        listing.distance_to_future_growth_km is not None
        and listing.distance_to_future_growth_km <= goal.future_growth_bonus_radius_km
    ):
        base *= 1.5
    risk_penalty = 18.0 * len(listing.risk_markers)
    return _clamp(base - risk_penalty)


def score_listings(listings: list[Listing], goal: Goal) -> list[ScoredListing]:
    pps_by_id = {listing.listing_id: _price_per_sotka(listing) for listing in listings}
    output: list[ScoredListing] = []
    for listing in listings:
        pps = pps_by_id[listing.listing_id]
        nearby = [
            pps_by_id[other.listing_id]
            for other in listings
            if other.listing_id != listing.listing_id
            and other.pool == listing.pool
            and haversine_km(listing.lat, listing.lon, other.lat, other.lon)
            <= goal.comparable_radius_km
            and pps_by_id[other.listing_id] > 0
        ]
        fallback = [
            value
            for other, value in (
                (candidate, pps_by_id[candidate.listing_id]) for candidate in listings
            )
            if other.listing_id != listing.listing_id
            and other.cluster == listing.cluster
            and value > 0
        ]
        comparable_values = nearby if len(nearby) >= 2 else fallback
        comparable_count = len(comparable_values)
        if not comparable_values:
            comparable_values = [pps]
        neighborhood_median = statistics.median(comparable_values)
        cluster_peers = [
            pps_by_id[other.listing_id]
            for other in listings
            if other.listing_id != listing.listing_id
            and other.cluster == listing.cluster
            and pps_by_id[other.listing_id] > 0
        ]
        cluster_average = statistics.fmean(cluster_peers) if cluster_peers else pps
        undervaluation = (
            (neighborhood_median - pps) / neighborhood_median if neighborhood_median > 0 else 0.0
        )
        cluster_discount = (
            (cluster_average - pps) / cluster_average if cluster_average > 0 else 0.0
        )
        margin = max(0.0, neighborhood_median * listing.area_sotki - listing.price_rub)
        cadastral_discount = (
            (listing.cadastral_value_rub - listing.price_rub) / listing.cadastral_value_rub
            if listing.cadastral_value_rub and listing.cadastral_value_rub > 0
            else 0.0
        )
        passed, reasons = _hard_filters(listing, goal)
        soul = _soul_score(listing, pps, neighborhood_median, goal)
        investment = _investment_score(listing, undervaluation, cadastral_discount, goal)
        red = undervaluation >= goal.underpricing_red_threshold
        has_soul_features = bool(listing.trees) or (
            listing.distance_to_water_km is not None and listing.distance_to_water_km <= 1.5
        )
        output.append(
            ScoredListing(
                listing=listing,
                price_per_sotka=pps,
                neighborhood_median_pps=neighborhood_median,
                cluster_average_pps=cluster_average,
                comparable_count=comparable_count,
                undervaluation_pct=undervaluation,
                cluster_discount_pct=cluster_discount,
                potential_margin_rub=margin,
                cadastral_discount_pct=cadastral_discount,
                soul_score=soul,
                investment_score=investment,
                hard_filter_pass=passed,
                hard_filter_reasons=reasons,
                red_status=red,
                double_profit=passed and red and has_soul_features,
            )
        )
    return output
