from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any


def _float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        value = value.replace(" ", "").replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    parsed = _float(value)
    return default if parsed is None else int(parsed)


def _bool(value: Any, default: bool | None = None) -> bool | None:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "да", "есть"}:
        return True
    if text in {"0", "false", "no", "нет", "не"}:
        return False
    return default


@dataclass(slots=True)
class Goal:
    raw_text: str = ""
    pools: list[str] = field(default_factory=lambda: ["Природа", "Безопасность"])
    locations: list[str] = field(
        default_factory=lambda: [
            "Истринское водохранилище",
            "Алёхново",
            "Лыщево",
            "Лопотово",
            "Новораково",
            "Мичуринец",
            "Переделкино",
            "D4",
        ]
    )
    min_area_sotki: float = 20.0
    ideal_area_sotki: float = 30.0
    max_budget_rub: float | None = 7_000_000.0
    allowed_land_categories: list[str] = field(default_factory=lambda: ["ИЖС"])
    exclude_mandatory_fees: bool = True
    underpricing_red_threshold: float = 0.20
    cluster_anomaly_threshold: float = 0.25
    comparable_radius_km: float = 1.0
    future_growth_bonus_radius_km: float = 1.0
    adverse_exclusion_radius_km: float = 0.5
    target_address: str = "Москва, улица Смоленская, 10"
    target_lat: float = 55.7477
    target_lon: float = 37.5822
    soul_weights: dict[str, float] = field(
        default_factory=lambda: {
            "price": 0.25,
            "water": 0.25,
            "trees": 0.20,
            "area": 0.15,
            "access_and_utilities": 0.15,
        }
    )
    investment_weights: dict[str, float] = field(
        default_factory=lambda: {
            "undervaluation": 0.50,
            "cadastral_discount": 0.15,
            "urgency": 0.10,
            "poor_presentation": 0.10,
            "future_growth": 0.15,
        }
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Listing:
    listing_id: str
    source: str
    url: str
    title: str
    address: str
    pool: str
    cluster: str
    lat: float
    lon: float
    area_sotki: float
    price_rub: float
    land_category: str
    description: str = ""
    photo_count: int = 0
    listing_days: int = 0
    cadastral_number: str = ""
    cadastral_value_rub: float | None = None
    has_mandatory_fees: bool | None = None
    annual_fees_rub: float | None = None
    water_type: str = ""
    distance_to_water_km: float | None = None
    distance_to_station_km: float | None = None
    distance_to_infrastructure_km: float | None = None
    distance_to_future_growth_km: float | None = None
    distance_to_adverse_zone_km: float | None = None
    route_distance_km: float | None = None
    route_minutes: float | None = None
    route_is_estimate: bool = True
    trees: list[str] = field(default_factory=list)
    urgency_markers: list[str] = field(default_factory=list)
    risk_markers: list[str] = field(default_factory=list)
    utilities: list[str] = field(default_factory=list)
    asphalt_access: bool | None = None
    security: bool | None = None
    infrastructure_notes: str = ""
    semantic_summary: str = ""
    is_demo: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Listing":
        return cls(
            listing_id=str(data.get("listing_id") or data.get("id") or ""),
            source=str(data.get("source") or ""),
            url=str(data.get("url") or ""),
            title=str(data.get("title") or ""),
            address=str(data.get("address") or ""),
            pool=str(data.get("pool") or "Природа"),
            cluster=str(data.get("cluster") or data.get("address") or "Не определён"),
            lat=float(_float(data.get("lat"), 0.0) or 0.0),
            lon=float(_float(data.get("lon"), 0.0) or 0.0),
            area_sotki=float(_float(data.get("area_sotki"), 0.0) or 0.0),
            price_rub=float(_float(data.get("price_rub"), 0.0) or 0.0),
            land_category=str(data.get("land_category") or ""),
            description=str(data.get("description") or ""),
            photo_count=_int(data.get("photo_count")),
            listing_days=_int(data.get("listing_days")),
            cadastral_number=str(data.get("cadastral_number") or ""),
            cadastral_value_rub=_float(data.get("cadastral_value_rub")),
            has_mandatory_fees=_bool(data.get("has_mandatory_fees")),
            annual_fees_rub=_float(data.get("annual_fees_rub")),
            water_type=str(data.get("water_type") or ""),
            distance_to_water_km=_float(data.get("distance_to_water_km")),
            distance_to_station_km=_float(data.get("distance_to_station_km")),
            distance_to_infrastructure_km=_float(data.get("distance_to_infrastructure_km")),
            distance_to_future_growth_km=_float(data.get("distance_to_future_growth_km")),
            distance_to_adverse_zone_km=_float(data.get("distance_to_adverse_zone_km")),
            route_distance_km=_float(data.get("route_distance_km")),
            route_minutes=_float(data.get("route_minutes")),
            route_is_estimate=bool(_bool(data.get("route_is_estimate"), True)),
            trees=[str(value) for value in data.get("trees", [])],
            urgency_markers=[str(value) for value in data.get("urgency_markers", [])],
            risk_markers=[str(value) for value in data.get("risk_markers", [])],
            utilities=[str(value) for value in data.get("utilities", [])],
            asphalt_access=_bool(data.get("asphalt_access")),
            security=_bool(data.get("security")),
            infrastructure_notes=str(data.get("infrastructure_notes") or ""),
            semantic_summary=str(data.get("semantic_summary") or ""),
            is_demo=bool(_bool(data.get("is_demo"), False)),
        )

    def with_updates(self, **kwargs: Any) -> "Listing":
        return replace(self, **kwargs)


@dataclass(slots=True)
class FeaturePoint:
    kind: str
    name: str
    lat: float
    lon: float
    subtype: str = ""
    source_url: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeaturePoint":
        return cls(
            kind=str(data["kind"]),
            name=str(data["name"]),
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            subtype=str(data.get("subtype") or ""),
            source_url=str(data.get("source_url") or ""),
        )


@dataclass(slots=True)
class ScoredListing:
    listing: Listing
    price_per_sotka: float
    neighborhood_median_pps: float
    cluster_average_pps: float
    comparable_count: int
    undervaluation_pct: float
    cluster_discount_pct: float
    potential_margin_rub: float
    cadastral_discount_pct: float
    soul_score: float
    investment_score: float
    hard_filter_pass: bool
    hard_filter_reasons: list[str]
    red_status: bool
    double_profit: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self.listing)
        payload.update(
            {
                "price_per_sotka": round(self.price_per_sotka, 2),
                "neighborhood_median_pps": round(self.neighborhood_median_pps, 2),
                "cluster_average_pps": round(self.cluster_average_pps, 2),
                "comparable_count": self.comparable_count,
                "undervaluation_pct": round(self.undervaluation_pct, 6),
                "cluster_discount_pct": round(self.cluster_discount_pct, 6),
                "potential_margin_rub": round(self.potential_margin_rub, 2),
                "cadastral_discount_pct": round(self.cadastral_discount_pct, 6),
                "soul_score": round(self.soul_score, 1),
                "investment_score": round(self.investment_score, 1),
                "hard_filter_pass": self.hard_filter_pass,
                "hard_filter_reasons": self.hard_filter_reasons,
                "status": "КРАСНЫЙ" if self.red_status else "обычный",
                "double_profit": self.double_profit,
            }
        )
        return payload
