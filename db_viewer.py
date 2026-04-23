"""Sound Classifier - DB 조회/관리"""
import sys
import os
from sound_classifier.tag_db import TagDB


def db_viewer_main():
    from sound_classifier.tag_db import TagDB
    db = TagDB()

    while True:
        print("\n" + "=" * 50)
        print("📊 Sound Classifier - DB 관리")
        print("=" * 50)
        print("  1. 전체 결과 보기")
        print("  2. 카테고리별 보기")
        print("  3. 키워드 검색")
        print("  4. 분류 요약")
        print("  5. DB 초기화 (전체 삭제)")
        print("  6. CSV 내보내기")
        print("  7. 태그 분포 확인")
        print("  0. 종료")
        print("-" * 50)

        choice = input("선택: ").strip()

        if choice == "1":
            rows = db.get_all()
            print(f"\n📄 전체 {len(rows)}개")
            print(f"{'파일명':40s} | {'대분류':6s} | {'태그1':25s} | {'태그2':25s}")
            print("-" * 105)
            for r in rows:
                name = r[2][:38] if r[2] else "?"
                cat = r[4] or "?"
                t1 = r[5] or ""
                t2 = r[6] or ""
                print(f"{name:40s} | {cat:6s} | {t1:25s} | {t2:25s}")

        elif choice == "2":
            counts = db.count()
            print("\n카테고리 선택:")
            cats = list(counts.keys())
            for i, c in enumerate(cats, 1):
                print(f"  {i}. {c} ({counts[c]}개)")
            sel = input("번호: ").strip()
            try:
                cat = cats[int(sel) - 1]
                rows = db.get_by_category(cat)
                print(f"\n📂 [{cat}] {len(rows)}개")
                for r in rows:
                    print(f"  {r[2]:40s} | {r[5]}")
            except (ValueError, IndexError):
                print("⚠️ 잘못된 입력")

        elif choice == "3":
            keyword = input("검색어: ").strip()
            rows = db.search(keyword)
            print(f"\n🔍 '{keyword}' 결과: {len(rows)}개")
            for r in rows:
                print(f"  {r[2]:40s} | {r[4]:6s} | {r[5]}")

        elif choice == "4":
            counts = db.count()
            total = sum(counts.values())
            print(f"\n📊 총 {total}개")
            for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                bar = "█" * (cnt * 30 // max(counts.values()))
                print(f"  {cat:6s} | {bar} {cnt}개")

        elif choice == "5":
            confirm = input("⚠️ 전체 삭제? (y 입력): ").strip()
            if confirm == "y":
                db.conn.execute("DELETE FROM sound_tags")
                db.conn.commit()
                print("✅ DB 초기화 완료")

        elif choice == "6":
            import csv
            rows = db.get_all()
            if not rows:
                print("⚠️ 데이터 없음")
                continue
            output_path = os.path.join("data", "sound_tags.csv")
            os.makedirs("data", exist_ok=True)
            headers = [
                "id", "file_path", "file_name", "duration",
                "category_main", "tag_1", "tag_2", "tag_3",
                "confidence", "analyzed_at"
            ]
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(row)
            print(f"✅ CSV 내보내기 완료!")
            print(f"📄 {os.path.abspath(output_path)}")
            print(f"📊 {len(rows)}개 레코드")

        elif choice == "7":
            from collections import Counter
            rows = db.get_all()
            if not rows:
                print("⚠️ 데이터 없음")
                continue
            categories = sorted(set(r[4] for r in rows if r[4]))
            for cat in categories:
                tags = [r[5] for r in rows if r[4] == cat and r[5]]
                if tags:
                    print(f"\n=== {cat} ({len(tags)}개) ===")
                    for tag, cnt in Counter(tags).most_common(15):
                        print(f"  {tag:35s} {cnt}개")

        elif choice == "0":
            db.close()
            return


if __name__ == "__main__":
    db_viewer_main()