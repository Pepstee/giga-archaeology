# Telegram export — first verified read

## Provenance and integrity

- Source: root `result.json`, Telegram Desktop JSON export, 43 MB.
- SHA-256: `cb4d6dfd1ed475a5e531853e6a1e8d8f760a8ac2e3ee96d64fe01a640f9cb4c8`.
- Normalized view: `corpus/raw/telegram_messages_primary_20260722.jsonl`.
- Derived SHA-256: `f34fba1c477eb812208c905e0d3db4a78fc3721f0e07c31c922c7906d78816c4`.
- Extractor: `scripts/extract_telegram.py`; its focused tests pass.
- Raw source was read but not changed. Phone data is acknowledged in the manifest but not copied
  into this report.

## What landed

The export contains 99,411 records across 96 active chats and five left chats; 99 chats contain
messages. There are 98,678 ordinary messages and 733 service events. Of the total, 44,254 are
outgoing, 54,424 incoming, and 86,991 contain visible text. The canonical Unix span is 10 Dec
2022 through 22 Jul 2026. Volume by year is 27 (2022), 10,443 (2023), 29,821 (2024), 43,793
(2025), and 15,327 (2026 to date).

This is not merely another style corpus. It preserves both sides, 4,259 reply links, 3,099
forward records, 1,599 edit markers, 986 reaction-bearing records, and 13,185 records with media
metadata. It is therefore evidence for reciprocity, conversational sequence, relationship events,
and who reopened contact. It still does not prove that every account-sent string was independently
composed by the operator.

## Dominant relationships in the export

Raw message volume is not equivalent to closeness, but the concentration is decisive enough to
set the reading order:

| Chat | Messages | Share | Outgoing / incoming | Retained span |
|---|---:|---:|---:|---|
| Andrei | 49,990 | 50.29% | 21,640 / 28,279 | May 2024–Jul 2026 |
| Serjo | 13,342 | 13.42% | 5,567 / 7,604 | Sep 2023–Jul 2026 |
| Lino | 11,363 | 11.43% | 4,695 / 6,660 | Jun 2023–Jun 2026 |
| Elena | 5,160 | 5.19% | 2,005 / 2,801 | Apr 2024–Jul 2026 |
| Allen | 3,264 | 3.28% | 1,541 / 1,713 | Sep 2023–Jul 2026 |

Andrei is Bottle/Andrei Kavaliou. His bilateral thread alone is larger than the operator's entire
outgoing Telegram corpus and confirms continuous daily-life access: housing, university trouble,
money, work, technology, gaming, politics, jokes and mutual practical updates. This materially
strengthens his position as the most continuously integrated friend in the retained record.

Serjo is a long-running university/offline-social thread, beginning with lectures, parties and
meeting plans, later carrying travel, documents and daily-life coordination. Lino is another
long-duration, high-volume friendship whose retained content is dominated by gaming, politics,
shared absurdist language and ordinary check-ins; it peaks in 2023 and persists at lower frequency.
Elena is clearly a family/maternal relationship, not a peer friendship: welfare checks, passports,
money, investments, opportunities and increasingly project-like requests. Allen combines gaming
history, dry shared humour, difficult practical facts, and recent feedback on the operator's tools.

Several shorter high-density episodes—Moongazing, Valeriya, Mariia and Masha—need their own
chronological passes. Their compressed spans mean they must not be ranked by volume beside
multi-year friendships without reading the event sequence.

## Initial maintenance correction

A rough session boundary was calculated only when a new message followed at least 72 hours of
silence. Across the final three months of the export, Artiom reopened eight Andrei sessions versus
two by Andrei, and nine Allen sessions versus one by Allen. Serjo reopened eleven versus two by
Artiom; Joel's four recent 24-hour-gap sessions were all reopened by Joel. This boundary is a
measurement aid, not a psychological score, but it already disproves a single blanket claim that
Artiom is passively neglecting every close friend. Maintenance differs by relationship and period.

## Content and training boundaries

Outgoing visible text is predominantly Cyrillic/Russian (34,122 records by a simple script
heuristic), with 3,442 Latin-dominant and 80 genuinely mixed records. Median non-empty outgoing
length is 19 characters; 95% are at most 67 characters. The export also includes 739 outgoing
forwards, 288 outgoing URL-bearing records, and 107 outgoing messages of at least 1,000 characters.
Those are strong composition-review signals. Pasted code and long copied/generated passages remain
behavioural evidence when their act and timing matter, but are not automatically style evidence.

The raw and normalized files contain third-party identities, family/financial material, historical
addresses and token-bearing URLs. They must remain local-private. No Telegram message pairs are
authorized for fine-tuning until privacy, composition, function, relationship and leakage labels
have been applied.

## Next analytical pass

The correct next unit is a relationship-event graph, not one global bag of messages. For each major
counterparty: resolve aliases across Telegram/Discord/Instagram; segment conversations into sessions;
link replies and forwards; classify disclosure, planning, play, conflict, care, advice and repair;
then derive monthly relationship state with citations to immutable message IDs. Only after that pass
should the closest-friends map and full characterisation be rewritten.
