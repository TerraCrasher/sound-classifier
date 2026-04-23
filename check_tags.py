"""태그 분포 확인"""
from sound_classifier.tag_db import TagDB
from collections import Counter

db = TagDB()
rows = db.get_all()

for cat in ['기타','효과음','음악','생활','기계','동물','자연','사람','악기']:
    tags = [r[5] for r in rows if r[4] == cat]
    if tags:
        print(f"\n=== {cat} ({len(tags)}개) ===")
        for tag, cnt in Counter(tags).most_common(15):
            print(f"  {tag:35s} {cnt}개")

db.close()