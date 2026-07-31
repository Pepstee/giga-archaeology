import json
from pathlib import Path

from scripts.extract_telegram import extract, flatten_text


def test_flatten_text_preserves_rich_text_order():
    assert flatten_text(["hello ", {"type": "bold", "text": "world"}, "!"]) == "hello world!"


def test_extract_preserves_two_sided_context_and_provenance(tmp_path: Path):
    source = tmp_path / "result.json"
    output = tmp_path / "messages.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text(json.dumps({
        "personal_information": {"user_id": 42, "first_name": "Art", "phone_number": "+1"},
        "chats": {"list": [{
            "name": "Friend", "type": "personal_chat", "id": 7,
            "messages": [
                {"id": 1, "type": "message", "date": "2024-01-01T00:00:00",
                 "date_unixtime": "1704067200", "from": "Friend", "from_id": "user7",
                 "text": "hello", "text_entities": []},
                {"id": 2, "type": "message", "date": "2024-01-01T00:00:01",
                 "date_unixtime": "1704067201", "from": "Art", "from_id": "user42",
                 "reply_to_message_id": 1,
                 "text": ["hi ", {"type": "bold", "text": "back"}],
                 "text_entities": [{"type": "bold", "text": "back"}]},
            ],
        }]},
        "left_chats": {"list": []},
    }), encoding="utf-8")

    result = extract(source, output, manifest, "telegram_primary_20260722")
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["direction"] for row in rows] == ["incoming", "outgoing"]
    assert rows[1]["text"] == "hi back"
    assert rows[1]["reply_to_message_id"] == "1"
    assert result["records"] == 2
    assert result["by_direction"] == {"incoming": 1, "outgoing": 1}
    assert result["direct_sft_authorised"] is False
