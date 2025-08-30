import re
from typing import List


def suggest_hashtags(topic: str, posts: List[str], limit: int = 5) -> List[str]:
    text = ' ' + (topic or '') + ' ' + ' '.join(posts or [])
    # Collect words that could be tags (alnum words longer than 3)
    words = re.findall(r"[A-Za-z]{4,}", text)
    freq = {}
    for w in words:
        k = w.lower()
        freq[k] = freq.get(k, 0) + 1
    # Build hashtags, simple scoring by frequency
    tags = []
    for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0])):
        tag = '#' + re.sub(r"[^A-Za-z0-9]", '', w)
        if len(tag) > 1 and tag not in tags:
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags
