import unittest

from scripts.analyze_unified_memory import signal_hits, style_hits


class UnifiedMemoryAnalysisTests(unittest.TestCase):
    def test_signal_categories_are_retrieval_aids(self):
        hits = signal_hits("Мне нужна точная система и план, чтобы проверить факты.")
        self.assertIn("truth_and_epistemic_clarity", hits["value"])
        self.assertIn("order_and_control", hits["value"])

    def test_style_features(self):
        hits = style_hits("АХАХ, let's check это?")
        self.assertTrue(hits["question"])
        self.assertTrue(hits["laughter"])
        self.assertTrue(hits["code_switch"])


if __name__ == "__main__":
    unittest.main()
