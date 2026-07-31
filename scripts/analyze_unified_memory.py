#!/usr/bin/env python3
"""Produce deterministic longitudinal signals from the unified memory database.

This script does not diagnose the operator or infer beliefs. It measures observable language
and activity signals so that later human/LLM interpretation can cite a reproducible baseline.
Every representative excerpt retains its stable unified-memory record ID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")
URL_RE = re.compile(r"https?://", re.I)

# These are deliberately broad lexical signal families. Counts are prompts for close reading,
# not proof that a message expresses a stable value, emotion, or belief.
SIGNALS: dict[str, dict[str, tuple[str, ...]]] = {
    "topic": {
        "gaming_and_performance": (
            r"\b(?:wow|варкрафт|рейд|гильд|дпс|хпс|босс|рога|палад|друид|маг|варлок)\w*",
            r"\b(?:gear|parse|raid|guild|dps|hps)\w*",
        ),
        "relationships_and_sex": (
            r"\b(?:отношен|девуш|женщин|любов|влюб|секс|свидан|поцел|расстал|измен|парн)\w*",
            r"\b(?:relationship|girlfriend|women|woman|love|dating|sex|kiss|breakup)\w*",
        ),
        "work_money_and_sales": (
            r"\b(?:работ|карьер|зарплат|деньг|продаж|клиент|бизнес|ваканси|резюм|доход)\w*",
            r"\b(?:work|career|salary|money|sales|client|business|job|resume|revenue)\w*",
        ),
        "education_and_learning": (
            r"\b(?:учеб|учит|универ|школ|экзам|курс|книг|знан|образован)\w*",
            r"\b(?:study|learn|university|school|exam|course|book|knowledge|education)\w*",
        ),
        "technology_and_building": (
            r"\b(?:код|скрипт|сервер|баз[аыу]|модел|нейросет|автоматиз|оркестратор|датасет)\w*",
            r"\b(?:code|script|server|database|model|neural|automat|orchestrat|dataset|lora)\w*",
        ),
        "politics_and_ideology": (
            r"\b(?:политик|идеолог|либерал|консерват|коммуни|фаши|государств|правительств)\w*",
            r"\b(?:politic|ideolog|liberal|conservative|communis|fascis|government|state)\w*",
        ),
        "travel_and_mobility": (
            r"\b(?:путешеств|поездк|самол[её]т|билет|паспорт|виз[аы]|лондон|вьетнам|коре)\w*",
            r"\b(?:travel|trip|flight|ticket|passport|visa|london|vietnam|korea)\w*",
        ),
        "family_and_home": (
            r"\b(?:семь[яеи]|мам[аые]|пап[аые]|родител|брат|сестр|дом|квартир)\w*",
            r"\b(?:family|mother|father|parent|brother|sister|home|apartment)\w*",
        ),
    },
    "value": {
        "competence_and_mastery": (
            r"\b(?:уметь|навык|компетент|мастер|эффектив|результат|лучше|точн|качеств)\w*",
            r"\b(?:skill|competence|master|effective|result|better|precis|quality|expert)\w*",
        ),
        "truth_and_epistemic_clarity": (
            r"\b(?:правд|лож|честн|доказ|факт|понять|выясн|точно|уверен|заблужд)\w*",
            r"\b(?:truth|lie|honest|evidence|fact|understand|verify|certain|wrong)\w*",
        ),
        "loyalty_and_reciprocity": (
            r"\b(?:верн|лоял|предал|довер|взаим|дружб|друг|поддерж)\w*",
            r"\b(?:loyal|betray|trust|reciproc|friend|support)\w*",
        ),
        "autonomy_and_freedom": (
            r"\b(?:свобод|самостоят|независ|контролир|застав|обязан|право)\w*",
            r"\b(?:freedom|autonom|independen|control|force|oblig|right)\w*",
        ),
        "growth_and_learning": (
            r"\b(?:разви|рост|учит|науч|улучш|прогресс|изменит)\w*",
            r"\b(?:develop|growth|learn|improve|progress|change)\w*",
        ),
        "fairness_and_desert": (
            r"\b(?:справедлив|заслуж|честно|нечестно|вина|винов|ответствен)\w*",
            r"\b(?:fair|deserv|unfair|fault|guilt|responsib|justice)\w*",
        ),
        "care_and_protection": (
            r"\b(?:помо|забот|беречь|защит|беспоко|здоров|безопас)\w*",
            r"\b(?:help|care|protect|worr|health|safe)\w*",
        ),
        "order_and_control": (
            r"\b(?:план|систем|структур|организ|правил|контрол|порядок|процесс)\w*",
            r"\b(?:plan|system|structure|organi|rule|control|order|process)\w*",
        ),
    },
    "affect": {
        "joy_and_excitement": (
            r"\b(?:счаст|рад|кайф|весел|обож|восхит|крут|охуенн)\w*",
            r"\b(?:happy|joy|excited|love|wonderful|amazing|great)\w*",
        ),
        "sadness_and_loss": (
            r"\b(?:груст|печал|потер|тоск|плак|слез|боль|страда)\w*",
            r"\b(?:sad|loss|miss|cry|tear|pain|suffer|grief)\w*",
        ),
        "anger_and_contempt": (
            r"\b(?:ненави|бесит|зл|ярост|противен|мерз|мраз|шлюх|твар)\w*",
            r"\b(?:hate|angry|rage|disgust|contempt|bitch|scum)\w*",
        ),
        "fear_and_anxiety": (
            r"\b(?:страш|боюсь|тревог|беспоко|опас|паник|нерв)\w*",
            r"\b(?:fear|afraid|anxious|worr|danger|panic|nervous)\w*",
        ),
        "shame_and_guilt": (
            r"\b(?:стыд|вин[аыо]|винов|извини|прости|сожале)\w*",
            r"\b(?:shame|guilt|sorry|apologi|regret)\w*",
        ),
        "uncertainty": (
            r"\b(?:не знаю|хз|кажется|возможно|наверн|сомнева|заблужд)\b",
            r"\b(?:i don['’]?t know|maybe|perhaps|seems|uncertain|doubt)\b",
        ),
    },
}

COMPILED_SIGNALS = {
    family: {
        name: tuple(re.compile(pattern, re.I) for pattern in patterns)
        for name, patterns in categories.items()
    }
    for family, categories in SIGNALS.items()
}

STYLE_PATTERNS = {
    "question": re.compile(r"\?"),
    "exclamation": re.compile(r"!"),
    "laughter": re.compile(r"(?:ахах|хаха|хех|лол|кек|lol|lmao|rofl)", re.I),
    "profanity": re.compile(
        r"(?:\b(?:бля|бляд|еба|ебу|ебан|ёбан|нахуй|похуй|хуйн|сука|пизд|мудак)\w*"
        r"|\b(?:fuck|fucking|shit|bitch|cunt)\w*)",
        re.I,
    ),
    "apology": re.compile(r"\b(?:извини|прости|сожале|sorry|apologi)\w*", re.I),
    "directive": re.compile(
        r"\b(?:надо|нужно|должен|давай|сделай|проверь|найди|прочитай|must|need|let['’]?s|"
        r"do|check|find|read)\b",
        re.I,
    ),
    "epistemic_qualifier": re.compile(
        r"\b(?:думаю|кажется|возможно|вероятно|не знаю|хз|i think|seems|maybe|probably|"
        r"i don['’]?t know)\b",
        re.I,
    ),
    "self_correction": re.compile(r"\b(?:точнее|ой|нет,?|вернее|rather|actually|correction)\b", re.I),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[int], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * proportion
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return float(ordered[low])
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def signal_hits(text: str) -> dict[str, list[str]]:
    return {
        family: [
            name
            for name, patterns in categories.items()
            if any(pattern.search(text) for pattern in patterns)
        ]
        for family, categories in COMPILED_SIGNALS.items()
    }


def style_hits(text: str) -> dict[str, bool]:
    cyrillic = bool(CYRILLIC_RE.search(text))
    latin = bool(LATIN_RE.search(text))
    letters = [char for char in text if char.isalpha()]
    upper_share = (
        sum(char.isupper() for char in letters) / len(letters)
        if letters else 0.0
    )
    return {
        **{name: bool(pattern.search(text)) for name, pattern in STYLE_PATTERNS.items()},
        "url": bool(URL_RE.search(text)),
        "code_switch": cyrillic and latin,
        "mostly_uppercase": len(letters) >= 5 and upper_share >= 0.8,
    }


def aggregate(messages: list[sqlite3.Row]) -> dict:
    lengths = [len(row["text"]) for row in messages]
    word_counts = [len(WORD_RE.findall(row["text"])) for row in messages]
    style = Counter()
    signals = {family: Counter() for family in COMPILED_SIGNALS}
    active_days = set()
    threads = set()
    platforms = Counter()
    for row in messages:
        active_days.add(row["timestamp"][:10])
        threads.add((row["namespace"], row["thread_pk"]))
        platforms[row["platform"]] += 1
        style.update(name for name, hit in style_hits(row["text"]).items() if hit)
        for family, names in signal_hits(row["text"]).items():
            signals[family].update(names)
    count = len(messages)
    return {
        "messages": count,
        "characters": sum(lengths),
        "words": sum(word_counts),
        "active_days": len(active_days),
        "threads": len(threads),
        "platforms": dict(platforms.most_common()),
        "length": {
            "median_characters": statistics.median(lengths) if lengths else 0,
            "p90_characters": round(percentile(lengths, 0.9), 2),
            "mean_characters": round(statistics.mean(lengths), 2) if lengths else 0,
            "median_words": statistics.median(word_counts) if word_counts else 0,
        },
        "style_counts": dict(style),
        "style_per_1000": {
            name: round(value * 1000 / count, 2) if count else 0
            for name, value in sorted(style.items())
        },
        "signal_counts": {
            family: dict(counter.most_common())
            for family, counter in signals.items()
        },
        "signal_per_1000": {
            family: {
                name: round(value * 1000 / count, 2) if count else 0
                for name, value in counter.most_common()
            }
            for family, counter in signals.items()
        },
    }


def representative_messages(
    messages: list[sqlite3.Row],
    family: str,
    category: str,
    *,
    limit: int = 3,
) -> list[dict]:
    patterns = COMPILED_SIGNALS[family][category]
    candidates = []
    for row in messages:
        text = row["text"].strip()
        if not text or not any(pattern.search(text) for pattern in patterns):
            continue
        # Prefer substantive self-authored statements, while avoiding huge pasted blocks.
        score = min(len(text), 700)
        score += 180 if any(token in text.casefold() for token in ("я ", "мне ", "мой ", "i ")) else 0
        score -= 250 if URL_RE.search(text) else 0
        candidates.append((score, row))
    candidates.sort(key=lambda item: (-item[0], item[1]["timestamp"], item[1]["record_id"]))
    output = []
    used_normalised = set()
    for _, row in candidates:
        normalised = " ".join(row["text"].casefold().split())
        if normalised in used_normalised:
            continue
        used_normalised.add(normalised)
        output.append({
            "record_id": row["record_id"],
            "timestamp": row["timestamp"],
            "platform": row["platform"],
            "namespace": row["namespace"],
            "thread_title": row["thread_title"],
            "text": row["text"][:1200],
        })
        if len(output) >= limit:
            break
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    connection = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    messages = connection.execute(
        """
        SELECT m.record_id,m.platform,m.namespace,m.thread_pk,t.title AS thread_title,
               m.timestamp,m.text,m.direction,m.composition_status
        FROM messages m JOIN threads t ON t.thread_pk=m.thread_pk
        WHERE m.author_role='operator' AND trim(m.text)<>''
        ORDER BY m.timestamp,m.message_pk
        """
    ).fetchall()

    by_year: dict[str, list[sqlite3.Row]] = defaultdict(list)
    by_month: dict[str, list[sqlite3.Row]] = defaultdict(list)
    by_namespace: dict[str, list[sqlite3.Row]] = defaultdict(list)
    by_day: Counter[str] = Counter()
    thread_counts: Counter[tuple[str, str, str]] = Counter()
    normalised_locations: dict[str, set[str]] = defaultdict(set)
    for row in messages:
        by_year[row["timestamp"][:4]].append(row)
        by_month[row["timestamp"][:7]].append(row)
        by_namespace[row["namespace"]].append(row)
        by_day[row["timestamp"][:10]] += 1
        thread_counts[(row["platform"], row["namespace"], row["thread_title"])] += 1
        normalised = " ".join(row["text"].casefold().split())
        if normalised:
            normalised_locations[normalised].add(row["namespace"])

    cross_namespace_duplicates = {
        text: sorted(namespaces)
        for text, namespaces in normalised_locations.items()
        if len(namespaces) > 1 and len(text) >= 20
    }

    year_data = {}
    for year, rows in sorted(by_year.items()):
        result = aggregate(rows)
        result["top_threads"] = [
            {"platform": platform, "namespace": namespace, "title": title, "messages": count}
            for (platform, namespace, title), count in Counter(
                (row["platform"], row["namespace"], row["thread_title"]) for row in rows
            ).most_common(20)
        ]
        result["representatives"] = {
            family: {
                category: representative_messages(rows, family, category)
                for category in categories
            }
            for family, categories in COMPILED_SIGNALS.items()
        }
        year_data[year] = result

    month_data = {}
    for month, rows in sorted(by_month.items()):
        result = aggregate(rows)
        result["top_threads"] = [
            {"platform": platform, "namespace": namespace, "title": title, "messages": count}
            for (platform, namespace, title), count in Counter(
                (row["platform"], row["namespace"], row["thread_title"]) for row in rows
            ).most_common(8)
        ]
        result["peak_days"] = [
            {"date": day, "messages": count}
            for day, count in Counter(row["timestamp"][:10] for row in rows).most_common(5)
        ]
        month_data[month] = result

    namespace_data = {}
    for namespace, rows in sorted(by_namespace.items()):
        result = aggregate(rows)
        result["span"] = [rows[0]["timestamp"], rows[-1]["timestamp"]]
        namespace_data[namespace] = result

    output = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "scope": "operator-authored text-bearing messages",
            "limitations": [
                "Lexical categories are broad retrieval signals, not diagnoses or proof of belief.",
                "Discord exports contain only the account owner's messages.",
                "Message volume reflects platform availability and export coverage as well as behaviour.",
                "Provider-naive Discord wall-clock timestamps have unknown timezone.",
                "Representative excerpts are deterministic candidates for close reading, not automatic findings.",
            ],
        },
        "database": {
            "path": str(args.db),
            "sha256": sha256_file(args.db),
        },
        "overall": aggregate(messages),
        "by_year": year_data,
        "by_month": month_data,
        "by_namespace": namespace_data,
        "top_active_days": [
            {"date": day, "messages": count}
            for day, count in by_day.most_common(100)
        ],
        "top_threads": [
            {"platform": platform, "namespace": namespace, "title": title, "messages": count}
            for (platform, namespace, title), count in thread_counts.most_common(100)
        ],
        "cross_namespace_exact_text": {
            "unique_texts": len(cross_namespace_duplicates),
            "examples": [
                {"text": text[:500], "namespaces": namespaces}
                for text, namespaces in sorted(
                    cross_namespace_duplicates.items(),
                    key=lambda item: (-len(item[0]), item[0]),
                )[:100]
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    connection.close()
    print(json.dumps({
        "output": str(args.output),
        "operator_text_messages": len(messages),
        "years": len(year_data),
        "months": len(month_data),
        "namespaces": len(namespace_data),
        "sha256": sha256_file(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
