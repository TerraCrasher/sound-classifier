"""SQLite 태그 DB 관리"""
import sqlite3
import os
from datetime import datetime


_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sound_tags.db")


class TagDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = _DEFAULT_DB
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sound_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_name TEXT,
                duration REAL,
                category_main TEXT,
                tag_1 TEXT,
                tag_2 TEXT,
                tag_3 TEXT,
                confidence REAL,
                analyzed_at DATETIME
            )
        """)
        self.conn.commit()

    def insert(self, file_path, file_name, duration,
               category_main, tag_1, tag_2, tag_3, confidence):
        self.conn.execute("""
            INSERT OR REPLACE INTO sound_tags
            (file_path, file_name, duration, category_main,
             tag_1, tag_2, tag_3, confidence, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_path, file_name, duration, category_main,
              tag_1, tag_2, tag_3, confidence,
              datetime.now().isoformat()))
        self.conn.commit()

    def search(self, keyword: str) -> list:
        cur = self.conn.execute("""
            SELECT * FROM sound_tags
            WHERE tag_1 LIKE ? OR tag_2 LIKE ? OR tag_3 LIKE ?
               OR file_name LIKE ? OR category_main LIKE ?
        """, tuple(f"%{keyword}%" for _ in range(5)))
        return cur.fetchall()

    def get_by_category(self, category: str) -> list:
        cur = self.conn.execute(
            "SELECT * FROM sound_tags WHERE category_main = ?",
            (category,))
        return cur.fetchall()

    def get_all(self) -> list:
        cur = self.conn.execute("SELECT * FROM sound_tags")
        return cur.fetchall()

    def count(self) -> dict:
        cur = self.conn.execute("""
            SELECT category_main, COUNT(*)
            FROM sound_tags GROUP BY category_main
        """)
        return dict(cur.fetchall())

    def exists(self, file_path: str) -> bool:
        """파일이 이미 DB에 있는지 확인"""
        cur = self.conn.execute(
            "SELECT 1 FROM sound_tags WHERE file_path = ?",
            (file_path,))
        return cur.fetchone() is not None

    def get_analyzed_paths(self) -> set:
        """분석 완료된 파일 경로 목록 반환"""
        cur = self.conn.execute("SELECT file_path FROM sound_tags")
        return {row[0] for row in cur.fetchall()}

    def close(self):
        self.conn.close()