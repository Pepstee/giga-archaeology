from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from land_monitor.goal_parser import parse_goal_text
from land_monitor.models import Goal, Listing
from land_monitor.pipeline import run_pipeline
from land_monitor.scoring import score_listings
from land_monitor.sources import load_listings


ROOT = Path(__file__).resolve().parents[1]


class GoalParserTests(unittest.TestCase):
    def test_russian_goal_patch(self) -> None:
        goal = parse_goal_text(
            "Ищу от 30 соток, бюджет до 6 млн, ИЖС без взносов, "
            "в радиусе 2 км, дешевле соседей на 25%"
        )
        self.assertEqual(goal.min_area_sotki, 30)
        self.assertEqual(goal.max_budget_rub, 6_000_000)
        self.assertEqual(goal.comparable_radius_km, 2)
        self.assertEqual(goal.underpricing_red_threshold, 0.25)
        self.assertTrue(goal.exclude_mandatory_fees)


class PipelineTests(unittest.TestCase):
    def test_demo_pipeline_produces_three_ranked_sheets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_path = Path(temp) / "report.json"
            report = run_pipeline(
                ROOT / "examples/demo_listings.json",
                ROOT / "config/goal.json",
                report_path,
                feature_points_path=ROOT / "examples/feature_points.json",
                cadastral_values_path=ROOT / "examples/cadastral_values.csv",
            )
            self.assertEqual(
                set(report["sheets"]),
                {"Для души", "Инвест-топ", "Двойной профит"},
            )
            self.assertTrue(report["metadata"]["demo"])
            self.assertGreaterEqual(report["metadata"]["red_count"], 1)
            self.assertEqual(report["sheets"]["Инвест-топ"][0]["status"], "КРАСНЫЙ")
            self.assertTrue(report["sheets"]["Двойной профит"])
            self.assertIn(
                "distance_to_infrastructure_km",
                report["sheets"]["Инвест-топ"][0],
            )
            self.assertTrue(report_path.exists())
            json.loads(report_path.read_text(encoding="utf-8"))

    def test_goal_roundtrip_has_defaults(self) -> None:
        goal = Goal.from_dict({"min_area_sotki": 22})
        self.assertEqual(goal.min_area_sotki, 22)
        self.assertEqual(goal.target_address, "Москва, улица Смоленская, 10")

    def test_cluster_average_excludes_current_listing(self) -> None:
        first = Listing.from_dict(
            {
                "listing_id": "A",
                "source": "test",
                "url": "https://example.test/a",
                "title": "A",
                "address": "A",
                "cluster": "one",
                "lat": 55.7,
                "lon": 37.5,
                "area_sotki": 20,
                "price_rub": 2_000_000,
                "land_category": "ИЖС",
            }
        )
        second = Listing.from_dict(
            {
                "listing_id": "B",
                "source": "test",
                "url": "https://example.test/b",
                "title": "B",
                "address": "B",
                "cluster": "one",
                "lat": 55.7001,
                "lon": 37.5001,
                "area_sotki": 20,
                "price_rub": 4_000_000,
                "land_category": "ИЖС",
            }
        )
        scored = score_listings([first, second], Goal())
        self.assertEqual(scored[0].cluster_average_pps, 200_000)
        self.assertEqual(scored[1].cluster_average_pps, 100_000)
        self.assertEqual(scored[0].comparable_count, 1)

    def test_rejects_duplicate_ids_and_invalid_essentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            duplicate_path = Path(temp) / "duplicates.json"
            duplicate_path.write_text(
                json.dumps(
                    [
                        {
                            "listing_id": "same",
                            "area_sotki": 20,
                            "price_rub": 1_000_000,
                            "lat": 55.7,
                            "lon": 37.5,
                        },
                        {
                            "listing_id": "same",
                            "area_sotki": 20,
                            "price_rub": 1_100_000,
                            "lat": 55.8,
                            "lon": 37.6,
                        },
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate listing_id"):
                load_listings(duplicate_path)

            invalid_path = Path(temp) / "invalid.json"
            invalid_path.write_text(
                json.dumps(
                    [
                        {
                            "listing_id": "invalid",
                            "area_sotki": 0,
                            "price_rub": 1_000_000,
                            "lat": 0,
                            "lon": 0,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "positive area/price"):
                load_listings(invalid_path)


if __name__ == "__main__":
    unittest.main()
