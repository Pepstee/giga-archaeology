import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_unified_memory import (
    SourceSpec,
    ai_adapter,
    build_monthly_map,
    build_sessions,
    discord_adapter,
    SCHEMA,
)


class UnifiedMemoryTests(unittest.TestCase):
    def test_adapters_preserve_coverage_and_sessions_reconcile(self):
        discord = discord_adapter({
            "ts": "2021-01-01 01:00:00",
            "channel_id": "1",
            "message_id": "2",
            "channel_label": "DM",
            "text": "hello there",
            "composition_status": "unverified",
            "context_available": False,
        }, 1, SourceSpec(Path("x"), "discord", "teen_vstee", "one-sided", discord_adapter))
        ai = ai_adapter({
            "ts": "2024-01-01T00:00:00Z",
            "conv_uuid": "c",
            "conversation": "Test",
            "sender": "human",
            "text": "why?",
        }, 1, SourceSpec(Path("y"), "chatgpt", "test", "two-sided", ai_adapter))

        self.assertEqual(discord["author_role"], "operator")
        self.assertIsNone(discord["timestamp_epoch"])
        self.assertEqual(ai["author_role"], "operator")
        self.assertIsNotNone(ai["timestamp_epoch"])

        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "test.sqlite3"
            connection = sqlite3.connect(db)
            connection.row_factory = sqlite3.Row
            connection.executescript(SCHEMA)
            connection.execute(
                "INSERT INTO source_files(path,sha256,byte_size,platform,namespace,coverage) "
                "VALUES ('x',?,1,'discord','teen_vstee','one-sided')", ("0" * 64,)
            )
            connection.execute(
                "INSERT INTO threads(platform,namespace,thread_id,title,coverage) "
                "VALUES ('discord','teen_vstee','1','DM','one-sided')"
            )
            thread_pk = connection.execute("SELECT thread_pk FROM threads").fetchone()[0]
            source_id = connection.execute("SELECT source_id FROM source_files").fetchone()[0]
            values = []
            for index, timestamp in enumerate(
                ["2021-01-01T01:00:00", "2021-01-01T02:00:00", "2021-01-02T03:00:00"], 1
            ):
                values.append((
                    f"m{index}", "discord", "teen_vstee", str(index), thread_pk, "a", "A",
                    "operator", "outgoing", timestamp, None,
                    "provider_naive_unknown_timezone", "hello", "x", "x", "message",
                    "unverified", 0, source_id, "member", str(index), None, "{}",
                ))
            connection.executemany(
                "INSERT INTO messages VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                values,
            )
            build_sessions(connection)
            build_monthly_map(connection)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 2)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM session_messages").fetchone()[0], 3
            )
            connection.close()


if __name__ == "__main__":
    unittest.main()
