import json
import unittest


class MemoryClaimsSourceTests(unittest.TestCase):
    def test_claim_source_has_unique_ids_and_evidence(self):
        with open("corpus/derived/tier3_memory_claims_20260726.json", encoding="utf-8") as handle:
            payload = json.load(handle)
        claims = payload["claims"]
        ids = [claim["claim_id"] for claim in claims]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(claim["evidence"] for claim in claims))
        self.assertTrue(all(0 <= claim["confidence"] <= 1 for claim in claims))


if __name__ == "__main__":
    unittest.main()
