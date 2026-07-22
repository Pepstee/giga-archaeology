#!/usr/bin/env python3
"""build_instagram_pairs.py — build fine-tune pairs (incoming context -> Artiom's reply)
from a Meta/Instagram export. Output: chat-format JSONL usable by MLX-LM / axolotl / etc.

Usage: python3 build_instagram_pairs.py <export_root> <out.jsonl> [sender_name]

Design: per thread, messages sorted ascending; consecutive same-sender messages within
15 min merge into one turn (joined by newline). Each of the operator's turns that follows
at least one other-party turn becomes a training example; context = up to 3 preceding
turns. In group threads (>2 participants) context lines carry "Name: " prefixes.
System lines ('Reacted …', 'Liked a message', attachments) are dropped before turning.
"""
import json, glob, os, sys, datetime

MERGE_GAP_MS = 15 * 60 * 1000
CTX_TURNS = 3

def fix(s):
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def keep(txt):
    return txt and txt not in {'Liked a message', 'You sent an attachment.'} \
        and not txt.startswith('Reacted ') and not txt.endswith(' to your message')

def main(root, out_path, me='Artiom'):
    n = 0
    with open(out_path, 'w') as fh:
        for f in glob.glob(os.path.join(root, 'your_instagram_activity/messages/inbox/*/message_*.json')):
            d = json.load(open(f))
            group = len(d.get('participants', [])) > 2
            msgs = []
            for m in d.get('messages', []):
                txt = m.get('content')
                if not txt:
                    continue
                txt = fix(txt)
                if not keep(txt):
                    continue
                msgs.append((m.get('timestamp_ms', 0), fix(m.get('sender_name', '?')), txt))
            msgs.sort()
            # merge into turns
            turns = []
            for ts, who, txt in msgs:
                if turns and turns[-1][1] == who and ts - turns[-1][2] <= MERGE_GAP_MS:
                    turns[-1][0].append(txt); turns[-1][2] = ts
                else:
                    turns.append([[txt], who, ts])
            # emit pairs
            for i, (texts, who, ts) in enumerate(turns):
                if who != me or i == 0:
                    continue
                ctx = turns[max(0, i - CTX_TURNS):i]
                ctx = [t for t in ctx if t[1] != me]
                if not ctx:
                    continue
                if group:
                    user = '\n'.join(f"{t[1]}: {line}" for t in ctx for line in t[0])
                else:
                    user = '\n'.join(line for t in ctx for line in t[0])
                fh.write(json.dumps({'messages': [
                    {'role': 'user', 'content': user},
                    {'role': 'assistant', 'content': '\n'.join(texts)}],
                    'meta': {'thread': fix(d.get('title', '')), 'group': group,
                             'ts': datetime.datetime.utcfromtimestamp(ts / 1000).isoformat() + 'Z'}},
                    ensure_ascii=False) + '\n')
                n += 1
    print(f'{n} pairs -> {out_path}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'Artiom')
