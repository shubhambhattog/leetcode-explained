#!/usr/bin/env python3
"""
Adds Striver's (take U forward) explanation videos from his public DSA sheets on
takeuforward.org, and orders every problem's videos NeetCode -> Striver -> rest.

Each sheet row carries both the problem's LeetCode link and Striver's YouTube
link for it, so the mapping comes straight from takeUforward. The sheet pages
are server-rendered (Next.js), so the rows are read out of the page payload; no
API key is needed. Rows that only link to GeeksforGeeks/Coding Ninjas are skipped.

Usage: python3 scripts/refresh_striver_videos.py
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, 'src', 'assets', 'data', 'problem_data.json')
# Earlier sheets win when two sheets map the same problem to different videos.
SHEETS = [
    'https://takeuforward.org/prep-hub/strivers-a2z-dsa-sheet',
    'https://takeuforward.org/prep-hub/strivers-sde-sheet',
]
STRIVER_CHANNEL = 'take U forward'
NEETCODE_CHANNELS = {'NeetCode', 'NeetCodeIO'}
MAX_VIDEOS = 5

ROW_START = re.compile(r'"item","practice"')
LEETCODE_LINK = re.compile(r'https://leetcode\.com/problems/([a-z0-9-]+)')
YOUTUBE_LINK = re.compile(r'https://(?:youtu\.be/|(?:www\.)?youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})')


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode('utf-8')


def parse_sheet(html):
    """Returns {leetcode slug: youtube id} for every row that has both links."""
    payload = html.replace('\\"', '"')
    starts = [m.start() for m in ROW_START.finditer(payload)]
    mapping = {}
    for index, start in enumerate(starts):
        row = payload[start:starts[index + 1] if index + 1 < len(starts) else start + 3000]
        leetcode = LEETCODE_LINK.search(row)
        youtube = YOUTUBE_LINK.search(row)
        if leetcode and youtube:
            mapping.setdefault(leetcode.group(1), youtube.group(1))
    return mapping


def order_videos(videos):
    """One NeetCode video first, then Striver, then the rest in their existing order."""
    neetcode = [v for v in videos if v['channel'] in NEETCODE_CHANNELS][:1]
    striver = [v for v in videos if v['channel'] == STRIVER_CHANNEL][:1]
    rest = [v for v in videos if v not in neetcode and v not in striver and v['channel'] != STRIVER_CHANNEL]
    return (neetcode + striver + rest)[:MAX_VIDEOS]


def main():
    striver = {}
    for url in SHEETS:
        print(f'Reading {url} ...', file=sys.stderr)
        sheet = parse_sheet(fetch(url))
        print(f'  {len(sheet)} LeetCode problems with a video', file=sys.stderr)
        for slug, video_id in sheet.items():
            striver.setdefault(slug, video_id)
    if not striver:
        sys.exit('No rows parsed; the takeuforward.org page format probably changed.')

    with open(DATA_PATH) as f:
        data = json.load(f)

    added = 0
    for question in data['questions']:
        videos = question.get('videos', [])
        video_id = striver.get(question.get('slug'))
        if video_id:
            # The sheet's video is Striver's canonical one; it replaces any other take U forward pick.
            videos = [v for v in videos if v['channel'] != STRIVER_CHANNEL]
            videos.insert(0, {'embedded_url': f'https://www.youtube.com/embed/{video_id}', 'channel': STRIVER_CHANNEL})
            added += 1
        if videos:
            question['videos'] = order_videos(videos)

    with open(DATA_PATH, 'w') as f:
        json.dump(data, f, indent=4)

    matched = sum(1 for slug in striver if any(q.get('slug') == slug for q in data['questions']))
    with_videos = sum(1 for q in data['questions'] if q.get('videos'))
    print(f'{added} problems have a Striver video ({len(striver) - matched} sheet slugs not on LeetCode list); '
          f'{with_videos} problems have videos', file=sys.stderr)


if __name__ == '__main__':
    main()
