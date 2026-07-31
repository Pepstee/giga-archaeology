#!/usr/bin/env python3
"""Run a local, sanitised persona LoRA generation suite.

This deliberately does not score promotion automatically. It records deterministic outputs
for a human/blind review and keeps the locked train/test examples out of the report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter-path", type=Path)
    parser.add_argument("--adapter-kind", choices=("speech", "reasoning", "all"), default="all")
    parser.add_argument("--max-tokens", type=int, default=160)
    args = parser.parse_args()

    suite: dict[str, Any] = json.loads(args.suite.read_text(encoding="utf-8"))
    cases = [
        case
        for case in suite["cases"]
        if args.adapter_kind == "all" or case["adapter"] == args.adapter_kind
    ]
    model, tokenizer = load(
        args.model,
        adapter_path=str(args.adapter_path) if args.adapter_path else None,
    )
    sampler = make_sampler(temp=0.0)
    outputs = []
    for case in cases:
        prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": case["system"]},
                {"role": "user", "content": case["prompt"]},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )
        response = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=args.max_tokens,
            sampler=sampler,
            verbose=False,
        ).strip()
        outputs.append(
            {
                "id": case["id"],
                "adapter": case["adapter"],
                "expected": case["expected"],
                "forbidden": case["forbidden"],
                "response": response,
                "review_status": "pending_human_or_blind_review",
            }
        )

    result = {
        "suite_id": suite["suite_id"],
        "suite_sha256": sha256(args.suite),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "adapter_path": str(args.adapter_path) if args.adapter_path else None,
        "adapter_kind": args.adapter_kind,
        "decoding": {"temperature": 0.0, "max_tokens": args.max_tokens},
        "promotion_decision": "not_made",
        "outputs": outputs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output.chmod(0o600)


if __name__ == "__main__":
    main()
