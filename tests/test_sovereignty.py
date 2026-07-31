from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from twin_core.sovereignty import (
    AUTHORSHIP_COMPONENTS,
    DIMENSIONS,
    INDICATOR_BY_ID,
    INDICATORS,
    INPUT_SCHEMA,
    SovereigntyError,
    calculate,
    canonical_json,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "sovereignty-assessment.synthetic.json"
CONTRACT = ROOT / "contracts" / "sovereignty-observation.v1.schema.json"


def example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def observation(packet: dict, indicator_id: str) -> dict:
    return next(
        item for item in packet["observations"] if item["indicator"] == indicator_id
    )


class SovereigntyTests(unittest.TestCase):
    def test_complete_packet_produces_bounded_provisional_score_and_guardrails(self) -> None:
        result = calculate(example())
        self.assertEqual(result["status"], "provisional")
        self.assertIsInstance(result["sovereignty_index"], float)
        self.assertGreater(result["sovereignty_index"], 0)
        self.assertLessEqual(result["sovereignty_index"], 100)
        self.assertEqual(result["evidence_coverage"], 1.0)
        self.assertEqual(len(result["dimensions"]), 7)
        self.assertEqual(
            result["choice_authenticity"]["choice_state"],
            "authored_choice_supported",
        )
        self.assertEqual(result["choice_authenticity"]["risk_band"], "low")
        self.assertEqual(
            result["companion_indexes"]["effective_voluntariness"],
            70.05,
        )
        self.assertEqual(
            result["guardrails"]["create_relate_inhabit"]["score"],
            57.14,
        )
        self.assertEqual(
            result["guardrails"]["create_relate_inhabit"]["state"],
            "warning",
        )
        self.assertIn("Sovereignty Index", render_markdown(result))
        self.assertEqual(canonical_json(result), canonical_json(result))

    def test_sparse_packet_withholds_headline_instead_of_imputing(self) -> None:
        packet = example()
        packet["observations"] = packet["observations"][:3]
        result = calculate(packet)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["sovereignty_index"])
        self.assertTrue(
            any(item["state"] == "insufficient_evidence" for item in result["dimensions"])
        )

    def test_weakest_dimension_caps_high_headline(self) -> None:
        packet = example()
        for observation in packet["observations"]:
            spec = INDICATOR_BY_ID[observation["indicator"]]
            measurement = observation["measurement"]
            if "denominator" in measurement:
                measurement["numerator"] = (
                    0
                    if spec.normalisation == "inverse_ratio"
                    else measurement["denominator"]
                )
            elif spec.normalisation == "linear":
                measurement["value"] = spec.high
            elif spec.normalisation == "inverse_linear":
                measurement["value"] = spec.low
            else:
                measurement["value"] = 100
        # Recovery is intentionally collapsed while every other headline input is maximal.
        for observation in packet["observations"]:
            if observation["indicator"] == "disruption_recovery_days":
                observation["measurement"]["value"] = 14
            elif observation["indicator"] == "slack_buffer_days":
                observation["measurement"]["value"] = 0
            elif observation["indicator"] == "reversible_major_decisions":
                observation["measurement"]["numerator"] = 0
        result = calculate(packet)
        self.assertEqual(
            next(item for item in result["dimensions"] if item["id"] == "recovery")["score"],
            0.0,
        )
        self.assertLessEqual(result["sovereignty_index"], 20.0)
        self.assertTrue(any("Bottleneck cap" in item for item in result["warnings"]))

    def test_evidence_strength_changes_reliability_not_observed_score(self) -> None:
        strong = example()
        weak = copy.deepcopy(strong)
        for observation in weak["observations"]:
            observation["evidence_class"] = "model_inference"
            observation["confidence"] = 0.5
        strong_result = calculate(strong)
        weak_result = calculate(weak)
        self.assertEqual(
            strong_result["sovereignty_index"],
            weak_result["sovereignty_index"],
        )
        self.assertGreater(
            strong_result["evidence_reliability"],
            weak_result["evidence_reliability"],
        )
        self.assertEqual(
            strong_result["choice_authenticity"]["self_deception_risk"],
            weak_result["choice_authenticity"]["self_deception_risk"],
        )
        self.assertEqual(
            weak_result["choice_authenticity"]["state"],
            "provisional",
        )

    def test_create_relate_inhabit_uses_floor_not_average(self) -> None:
        packet = example()
        replacements = {"create_commitments_met": 10, "relate_commitments_met": 2, "inhabit_commitments_met": 10}
        for observation in packet["observations"]:
            if observation["indicator"] in replacements:
                observation["measurement"] = {
                    "numerator": replacements[observation["indicator"]],
                    "denominator": 10,
                }
        result = calculate(packet)
        guardrail = result["guardrails"]["create_relate_inhabit"]
        self.assertEqual(guardrail["score"], 20.0)
        self.assertEqual(guardrail["state"], "critical")

    def test_invalid_and_future_evidence_fail_closed(self) -> None:
        packet = example()
        packet["observations"][0]["measurement"] = {"numerator": 11, "denominator": 10}
        with self.assertRaisesRegex(SovereigntyError, "numerator"):
            calculate(packet)

        packet = example()
        packet["observations"][0]["observed_at"] = "2026-08-01T00:00:00+01:00"
        with self.assertRaisesRegex(SovereigntyError, "dated after"):
            calculate(packet)

        packet = example()
        packet["observations"].append(copy.deepcopy(packet["observations"][0]))
        with self.assertRaisesRegex(SovereigntyError, "duplicate"):
            calculate(packet)

    def test_trend_requires_compatible_results(self) -> None:
        first = calculate(example())
        second_packet = example()
        second_packet["assessment_id"] = "synthetic-week-02"
        second_packet["period_start"] = "2026-07-27"
        second_packet["period_end"] = "2026-07-27"
        second = calculate(second_packet, previous=first)
        self.assertEqual(second["trend"]["previous_assessment_id"], "synthetic-week-01")
        self.assertIn(
            "self_deception_risk",
            second["trend"]["choice_authenticity_deltas"],
        )
        incompatible = copy.deepcopy(first)
        incompatible["model_version"] = "other"
        with self.assertRaisesRegex(SovereigntyError, "incompatible"):
            calculate(second_packet, previous=incompatible)

    def test_contract_lists_every_example_indicator_once(self) -> None:
        packet = example()
        self.assertEqual(packet["schema_version"], INPUT_SCHEMA)
        ids = [item["indicator"] for item in packet["observations"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {item.id for item in INDICATORS})
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        contract_ids = set(
            contract["properties"]["observations"]["items"]["properties"]["indicator"][
                "enum"
            ]
        )
        self.assertEqual(contract_ids, {item.id for item in INDICATORS})

    def test_assessment_id_rejects_path_traversal(self) -> None:
        packet = example()
        packet["assessment_id"] = "../../escape"
        with self.assertRaisesRegex(SovereigntyError, "assessment_id"):
            calculate(packet)

    def test_cli_can_repeat_same_immutable_assessment(self) -> None:
        script = ROOT / "scripts" / "sovereignty_index.py"
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                str(script),
                str(EXAMPLE),
                "--state-dir",
                str(Path(directory) / "state"),
            ]
            first = subprocess.run(command, check=False, capture_output=True, text=True)
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)

    def test_cli_preserves_but_does_not_compare_incompatible_latest(self) -> None:
        script = ROOT / "scripts" / "sovereignty_index.py"
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            state.mkdir()
            incompatible = calculate(example())
            incompatible["assessment_id"] = "older-model-assessment"
            incompatible["model_version"] = "giga.sovereignty-model.v1"
            (state / "latest.json").write_text(
                canonical_json(incompatible),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(script),
                str(EXAMPLE),
                "--state-dir",
                str(state),
                "--json",
            ]

            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertIsNone(result["trend"])
            history = (
                state
                / "history"
                / result["model_version"]
                / f"{result['period_end']}_{result['assessment_id']}.json"
            )
            self.assertTrue(history.exists())

    def test_apparent_choice_under_constraint_does_not_score_as_authored(self) -> None:
        packet = example()
        for indicator_id in (
            "chosen_major_commitments",
            "intentional_discretionary_time",
        ):
            measurement = observation(packet, indicator_id)["measurement"]
            measurement["numerator"] = measurement["denominator"]
        observation(packet, "refusal_power")["measurement"]["value"] = 5
        for indicator_id in (
            "credible_alternative_coverage",
            "affordable_refusal_coverage",
            "counterfactual_endorsement_rate",
            "cross_environment_stability_rate",
            "delayed_reendorsement_rate",
        ):
            observation(packet, indicator_id)["measurement"]["numerator"] = 0
        origin = observation(packet, "preference_origin_trace_coverage")["measurement"]
        origin["numerator"] = origin["denominator"]
        contradiction = observation(packet, "behavioral_contradiction_rate")[
            "measurement"
        ]
        contradiction["numerator"] = 9
        contradiction["denominator"] = 10

        result = calculate(packet)
        diagnostic = result["choice_authenticity"]
        authorship = next(
            item for item in result["dimensions"] if item["id"] == "authorship"
        )

        self.assertEqual(diagnostic["declared_endorsement"], 100.0)
        self.assertLess(diagnostic["effective_voluntariness"]["score"], 20)
        self.assertEqual(diagnostic["risk_band"], "high")
        self.assertGreater(diagnostic["self_deception_risk"], 70)
        self.assertEqual(
            diagnostic["choice_state"],
            "endorsed_necessity_possible",
        )
        self.assertLess(authorship["score"], 20)
        self.assertTrue(
            any("not a diagnosis" in warning for warning in result["warnings"])
        )

    def test_authorship_component_cap_blocks_compensation(self) -> None:
        packet = example()
        authorship_ids = {
            item.id for item in INDICATORS if item.dimension == "authorship"
        }
        for item in packet["observations"]:
            if item["indicator"] not in authorship_ids:
                continue
            spec = INDICATOR_BY_ID[item["indicator"]]
            measurement = item["measurement"]
            if "denominator" in measurement:
                measurement["numerator"] = (
                    0
                    if spec.normalisation == "inverse_ratio"
                    else measurement["denominator"]
                )
            else:
                measurement["value"] = 100
        observation(packet, "refusal_power")["measurement"]["value"] = 40
        for indicator_id in (
            "credible_alternative_coverage",
            "affordable_refusal_coverage",
        ):
            measurement = observation(packet, indicator_id)["measurement"]
            measurement["numerator"] = 4
            measurement["denominator"] = 10

        result = calculate(packet)
        authorship = next(
            item for item in result["dimensions"] if item["id"] == "authorship"
        )

        self.assertEqual(authorship["score"], 60.0)
        self.assertTrue(authorship["component_cap_applied"])
        self.assertGreater(authorship["raw_score"], authorship["score"])

    def test_unconstrained_stable_choice_can_reach_full_authorship(self) -> None:
        packet = example()
        authorship_ids = {
            item.id for item in INDICATORS if item.dimension == "authorship"
        }
        for item in packet["observations"]:
            if item["indicator"] not in authorship_ids:
                continue
            spec = INDICATOR_BY_ID[item["indicator"]]
            measurement = item["measurement"]
            if "denominator" in measurement:
                measurement["numerator"] = (
                    0
                    if spec.normalisation == "inverse_ratio"
                    else measurement["denominator"]
                )
            else:
                measurement["value"] = 100

        result = calculate(packet)
        diagnostic = result["choice_authenticity"]
        authorship = next(
            item for item in result["dimensions"] if item["id"] == "authorship"
        )

        self.assertEqual(authorship["score"], 100.0)
        self.assertEqual(diagnostic["effective_voluntariness"]["score"], 100.0)
        self.assertEqual(diagnostic["self_deception_risk"], 0.0)
        self.assertEqual(diagnostic["risk_band"], "low")
        self.assertEqual(
            diagnostic["choice_state"],
            "authored_choice_supported",
        )

    def test_missing_choice_authenticity_evidence_withholds_authorship(self) -> None:
        packet = example()
        added_indicators = {
            "credible_alternative_coverage",
            "affordable_refusal_coverage",
            "counterfactual_endorsement_rate",
            "cross_environment_stability_rate",
            "delayed_reendorsement_rate",
            "preference_origin_trace_coverage",
            "behavioral_contradiction_rate",
        }
        packet["observations"] = [
            item
            for item in packet["observations"]
            if item["indicator"] not in added_indicators
        ]

        result = calculate(packet)
        authorship = next(
            item for item in result["dimensions"] if item["id"] == "authorship"
        )

        self.assertIsNone(authorship["score"])
        self.assertIsNone(result["sovereignty_index"])
        self.assertEqual(
            result["choice_authenticity"]["state"],
            "insufficient_evidence",
        )
        self.assertIsNone(result["choice_authenticity"]["self_deception_risk"])

    def test_model_weights_are_normalised(self) -> None:
        self.assertAlmostEqual(sum(item.weight for item in DIMENSIONS), 1.0)
        for dimension in DIMENSIONS:
            self.assertAlmostEqual(
                sum(
                    item.weight
                    for item in INDICATORS
                    if item.dimension == dimension.id
                ),
                1.0,
            )
        for component in AUTHORSHIP_COMPONENTS.values():
            self.assertAlmostEqual(sum(component["indicators"].values()), 1.0)
            for indicator_id, within_component_weight in component[
                "indicators"
            ].items():
                self.assertAlmostEqual(
                    INDICATOR_BY_ID[indicator_id].weight,
                    component["weight"] * within_component_weight,
                )


if __name__ == "__main__":
    unittest.main()
