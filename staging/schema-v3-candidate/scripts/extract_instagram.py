#!/usr/bin/env python3
"""extract_instagram.py — land a Meta/Instagram export as casual-mode corpus.

Usage: python3 extract_instagram.py <export_dir_or_extracted_zip_root> <out.jsonl> [sender_name]

Keeps only the operator's own messages (default sender 'Artiom'), fixes Meta's
latin-1/UTF-8 mojibake, drops media-only and system lines ('Reacted …', 'Liked a
message'), adds post comments, sorts chronologically. Output schema matches
corpus/raw/prompts_*.jsonl plus 'register': 'casual'.
First landed: corpus/raw/instagram_20260717.jsonl (11,749 records, Jul 2025–Jul 2026).
"""
import json, glob, os, sys, datetime

def fix(s):
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def main(root, out_path, sender='Artiom'):
    out = []
    for f in glob.glob(os.path.join(root, 'your_instagram_activity/messages/inbox/*/message_*.json')):
        d = json.load(open(f))
        thread = fix(d.get('title', ''))
        for m in d.get('messages', []):
            if m.get('sender_name') != sender:
                continue
            txt = m.get('content')
            if not txt:
                continue
            txt = fix(txt)
            if txt in {'Liked a message', 'You sent an attachment.'} or txt.startswith('Reacted ') or txt.endswith(' to your message'):
                continue
            ts = m.get('timestamp_ms', 0)
            out.append({'ts': datetime.datetime.utcfromtimestamp(ts / 1000).isoformat() + 'Z',
                        'text': txt, 'thread': thread, 'source': 'instagram_dm', 'register': 'casual'})
    cpath = os.path.join(root, 'your_instagram_activity/comments/post_comments_1.json')
    if os.path.exists(cpath):
        d = json.load(open(cpath))
        items = d if isinstance(d, list) else d.get('comments_media_comments', [])
        for c in items:
            s = c.get('string_map_data', {})
            txt = fix(s.get('Comment', {}).get('value', ''))
            ts = s.get('Time', {}).get('timestamp', 0)
            if txt:
                out.append({'ts': datetime.datetime.utcfromtimestamp(ts).isoformat() + 'Z',
                            'text': txt, 'thread': 'post_comment', 'source': 'instagram_comment', 'register': 'casual'})
    out.sort(key=lambda r: r['ts'])
    with open(out_path, 'w') as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(out)} records -> {out_path}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'Artiom')
