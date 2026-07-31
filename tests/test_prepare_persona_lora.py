import unittest

from scripts.prepare_persona_lora import stable_split, unsafe_text


class PersonaLoraPreparationTests(unittest.TestCase):
    def test_split_is_deterministic(self):
        self.assertEqual(stable_split("thread\0month", "seed"), stable_split("thread\0month", "seed"))

    def test_runtime_context_and_credentials_are_quarantined(self):
        self.assertEqual(
            unsafe_text("<recommended_plugins>\nprivate"),
            "injected_runtime_context",
        )
        self.assertEqual(unsafe_text("api_key = abcdefghijkl"), "possible_credential")


if __name__ == "__main__":
    unittest.main()
