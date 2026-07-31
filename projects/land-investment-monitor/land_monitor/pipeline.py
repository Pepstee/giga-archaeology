from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .analysis import apply_semantics
from .enrichment import enrich_listing, load_cadastral_values, load_feature_points
from .models import Goal, Listing, ScoredListing
from .scoring import score_listings
from .sources import load_listings


def load_goal(path: str | Path) -> Goal:
    return Goal.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_goal(goal: Goal, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(goal.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _record(item: ScoredListing) -> dict:
    payload = item.to_dict()
    positives: list[str] = []
    negatives: list[str] = []
    if item.red_status:
        positives.append(f"ниже локальной медианы на {item.undervaluation_pct:.0%}")
    if item.listing.trees:
        positives.append("деревья: " + ", ".join(item.listing.trees))
    if item.listing.distance_to_water_km is not None:
        positives.append(f"до воды {item.listing.distance_to_water_km:.1f} км")
    if item.listing.cadastral_value_rub and item.listing.price_rub < item.listing.cadastral_value_rub:
        positives.append("цена ниже кадастровой стоимости")
    if item.listing.risk_markers:
        negatives.append("риски: " + ", ".join(item.listing.risk_markers))
    if item.hard_filter_reasons:
        negatives.extend(item.hard_filter_reasons)
    if item.listing.route_is_estimate:
        negatives.append("время доезда пока оценочное")
    payload["positives"] = positives
    payload["negatives"] = negatives
    payload["pros_cons"] = (
        ("Плюсы: " + "; ".join(positives) if positives else "Плюсы не подтверждены")
        + " | "
        + ("Минусы: " + "; ".join(negatives) if negatives else "Явных минусов не найдено")
    )
    return payload


def build_report(scored: list[ScoredListing], goal: Goal) -> dict:
    eligible = [item for item in scored if item.hard_filter_pass]
    soul = sorted(eligible, key=lambda item: (item.soul_score, item.investment_score), reverse=True)
    investment = sorted(
        eligible,
        key=lambda item: (
            item.investment_score,
            item.potential_margin_rub,
            item.undervaluation_pct,
        ),
        reverse=True,
    )[:10]
    double = sorted(
        [item for item in eligible if item.double_profit],
        key=lambda item: (item.investment_score + item.soul_score, item.potential_margin_rub),
        reverse=True,
    )
    demo = bool(scored) and all(item.listing.is_demo for item in scored)
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "demo": demo,
            "source_count": len({item.listing.source for item in scored}),
            "listing_count": len(scored),
            "eligible_count": len(eligible),
            "red_count": sum(item.red_status for item in eligible),
            "route_note": (
                "Маршрут оценён по прямой с коэффициентом 1,35 и средней скоростью 45 км/ч, "
                "если live-routing не включён."
            ),
            "cadastral_note": (
                "Кадастровая стоимость берётся из подключаемого CSV/API-провайдера. "
                "Официальная публичная карта с декабря 2024 года размещена в НСПД; "
                "стабильный открытый программный API в MVP не предполагается."
            ),
        },
        "goal": goal.to_dict(),
        "sheets": {
            "Для души": [_record(item) for item in soul],
            "Инвест-топ": [_record(item) for item in investment],
            "Двойной профит": [_record(item) for item in double],
        },
    }


def run_pipeline(
    input_path: str | Path,
    goal_path: str | Path,
    output_path: str | Path,
    *,
    feature_points_path: str | Path | None = None,
    cadastral_values_path: str | Path | None = None,
    use_openai: bool = False,
    use_live_routing: bool = False,
) -> dict:
    goal = load_goal(goal_path)
    listings = load_listings(input_path)
    points = load_feature_points(feature_points_path)
    cadastral_values = load_cadastral_values(cadastral_values_path)
    if use_openai and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when --use-openai is enabled.")

    enriched: list[Listing] = []
    for listing in listings:
        semantic = apply_semantics(listing, use_openai=use_openai)
        enriched.append(
            enrich_listing(
                semantic,
                goal,
                points,
                cadastral_values,
                use_live_routing=use_live_routing,
            )
        )
    report = build_report(score_listings(enriched, goal), goal)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def make_digest(report: dict) -> str:
    metadata = report["metadata"]
    lines = [
        "Земельный монитор — " + ("ДЕМО" if metadata.get("demo") else "новый отчёт"),
        (
            f"Всего: {metadata['listing_count']} · прошли фильтры: "
            f"{metadata['eligible_count']} · недооценённых: {metadata['red_count']}"
        ),
        "",
        "Инвестиционный топ:",
    ]
    for index, item in enumerate(report["sheets"]["Инвест-топ"][:5], start=1):
        lines.append(
            f"{index}. {item['address']} — {item['price_rub']:,.0f} ₽; "
            f"дисконт {item['undervaluation_pct']:.0%}; "
            f"маржа {item['potential_margin_rub']:,.0f} ₽; "
            f"балл {item['investment_score']:.0f}"
        )
        lines.append(item["url"])
    if report["sheets"]["Двойной профит"]:
        best = report["sheets"]["Двойной профит"][0]
        lines.extend(
            [
                "",
                "Лучший «двойной профит»:",
                f"{best['address']} · душа {best['soul_score']:.0f} · инвестиции {best['investment_score']:.0f}",
                best["url"],
            ]
        )
    return "\n".join(lines)[:4000]

