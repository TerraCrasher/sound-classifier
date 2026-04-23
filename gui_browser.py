"""
Sound Browser — 검색/미리듣기/정리 GUI (UX 개선)
  - 실시간 필터링 (300ms 디바운스)
  - 카테고리 드롭다운
  - 컬럼 헤더 클릭 정렬
  - 태그 뱃지
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import shutil
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from sound_classifier.tag_db import TagDB

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "sound_tags.db")

COL_INDEX = {
    "file_name": 2, "category": 4,
    "tag_1": 5, "tag_2": 6, "tag_3": 7,
    "confidence": 8, "duration": 3,
}

MAX_BADGES = 20


class BrowserGUI(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("🔎 Sound Browser")
        self.geometry("1050x700")
        self.minsize(850, 550)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.db = None
        self.all_data = []
        self.filtered_data = []
        self.current_file_path = None
        self.sort_col = None
        self.sort_reverse = False
        self._search_after_id = None
        self.hide_missing = ctk.BooleanVar(value=True)

        self._init_db()
        self._build_ui()
        self._refresh_data()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── Init ────────────────────────────

    def _init_db(self):
        try:
            self.db = TagDB(DB_PATH)
        except Exception as e:
            messagebox.showerror("DB 오류", str(e))

    def _set_status(self, text):
        self.status_label.configure(text=text)

    # ─── UI Build ────────────────────────
    #  Row 0: 필터 바 (검색 + 카테고리 + 새로고침)
    #  Row 1: 태그 뱃지
    #  Row 2: 결과 테이블 (weight)
    #  Row 3: 플레이어
    #  Row 4: 하단 (출력폴더 + 복사/이동)
    #  Row 5: 상태바

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_filter_bar()
        self._build_badge_area()
        self._build_table()
        self._build_player()
        self._build_bottom()

        self.status_label = ctk.CTkLabel(
            self, text="Ready", anchor="w",
            font=("", 11), text_color="gray60")
        self.status_label.grid(
            row=5, column=0, sticky="ew", padx=12, pady=(0, 6))

    # ── 필터 바 ──

    def _build_filter_bar(self):
        f = ctk.CTkFrame(self)
        f.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="🔍", font=("", 18)).grid(
            row=0, column=0, padx=(10, 5))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        ctk.CTkEntry(
            f, textvariable=self.search_var,
            placeholder_text="실시간 검색...", height=36
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=8)

        self.category_var = ctk.StringVar(value="전체")
        self.category_menu = ctk.CTkOptionMenu(
            f, variable=self.category_var,
            values=["전체"], width=160, height=36,
            command=lambda _: self._apply_filters())
        self.category_menu.grid(row=0, column=2, padx=5, pady=8)

        ctk.CTkButton(
            f, text="🔄", width=40, height=36,
            command=self._refresh_data
        ).grid(row=0, column=3, padx=5, pady=8)

        self.hide_btn = ctk.CTkButton(
            f, text="🚫 없는 파일 숨김", width=150, height=36,
            fg_color="#2d7d46", hover_color="#3a9956",
            command=self._toggle_hide_missing)
        self.hide_btn.grid(row=0, column=4, padx=5, pady=8)

        self.count_label = ctk.CTkLabel(
            f, text="0건", font=("", 12, "bold"))
        self.count_label.grid(row=0, column=5, padx=(5, 10), pady=8)

        self.count_label = ctk.CTkLabel(
            f, text="0건", font=("", 12, "bold"))
        self.count_label.grid(row=0, column=4, padx=(5, 10), pady=8)

    # ── 태그 뱃지 ──

    def _build_badge_area(self):
        self.badge_frame = ctk.CTkFrame(self, height=45)
        self.badge_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.badge_frame.grid_propagate(False)

    def _update_badges(self):
        for w in self.badge_frame.winfo_children():
            w.destroy()

        tag_counter = Counter()
        for row in self.all_data:
            for idx in [5, 6, 7]:
                if len(row) > idx and row[idx]:
                    tag_counter[row[idx]] += 1

        top_tags = tag_counter.most_common(MAX_BADGES)

        if not top_tags:
            ctk.CTkLabel(
                self.badge_frame, text="태그 없음",
                text_color="gray50"
            ).pack(side="left", padx=10, pady=8)
            return

        ctk.CTkLabel(
            self.badge_frame, text="🔖", font=("", 14)
        ).pack(side="left", padx=(8, 4), pady=8)

        for tag, count in top_tags:
            ctk.CTkButton(
                self.badge_frame,
                text=f"{tag}({count})",
                height=28, width=0,
                font=("", 11),
                fg_color="gray30", hover_color="gray40",
                corner_radius=14,
                command=lambda t=tag: self._on_badge_click(t)
            ).pack(side="left", padx=2, pady=8)

    def _on_badge_click(self, tag):
        if self.search_var.get().strip() == tag:
            self.search_var.set("")
        else:
            self.search_var.set(tag)

    def _toggle_hide_missing(self):
        current = self.hide_missing.get()
        self.hide_missing.set(not current)
        if not current:
            self.hide_btn.configure(
                text="🚫 없는 파일 숨김", fg_color="#2d7d46")
        else:
            self.hide_btn.configure(
                text="👁 전체 표시", fg_color="gray30")
        self._apply_filters()

    # ── 결과 테이블 ──

    def _build_table(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b", foreground="white",
            fieldbackground="#2b2b2b", rowheight=28,
            font=("", 11))
        style.configure(
            "Treeview.Heading",
            background="#1f538d", foreground="white",
            font=("", 11, "bold"))
        style.map("Treeview",
                  background=[("selected", "#1f538d")])

        tf = ctk.CTkFrame(self, fg_color="transparent")
        tf.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        cols = ("file_name", "category", "tag_1", "tag_2",
                "tag_3", "confidence", "duration")
        self.tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            selectmode="browse")

        for col, txt, w in [
            ("file_name", "파일명", 220),
            ("category", "카테고리", 160),
            ("tag_1", "태그1", 110),
            ("tag_2", "태그2", 110),
            ("tag_3", "태그3", 110),
            ("confidence", "신뢰도", 70),
            ("duration", "길이", 60),
        ]:
            self.tree.heading(
                col, text=txt,
                command=lambda c=col: self._sort_by_column(c))
            self.tree.column(col, width=w, minwidth=40)

        sb = ttk.Scrollbar(
            tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.tag_configure("missing", foreground="gray50")
        self.tree.tag_configure("exists", foreground="white")

    # ── 플레이어 ──

    def _build_player(self):
        pf = ctk.CTkFrame(self)
        pf.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        pf.grid_columnconfigure(2, weight=1)

        self.play_btn = ctk.CTkButton(
            pf, text="▶️ 재생", width=90, height=32,
            command=self._play_audio)
        self.play_btn.grid(row=0, column=0, padx=(10, 5), pady=8)

        self.stop_btn = ctk.CTkButton(
            pf, text="⏹ 정지", width=90, height=32,
            fg_color="gray30", hover_color="gray40",
            command=self._stop_audio)
        self.stop_btn.grid(row=0, column=1, padx=5, pady=8)

        self.playing_label = ctk.CTkLabel(
            pf, text="선택된 파일 없음",
            font=("", 12), anchor="w")
        self.playing_label.grid(
            row=0, column=2, sticky="ew", padx=10, pady=8)

    # ── 하단 바 ──

    def _build_bottom(self):
        bf = ctk.CTkFrame(self)
        bf.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 5))
        bf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bf, text="📂 출력",
                     font=("", 12, "bold")).grid(
            row=0, column=0, padx=(10, 5), pady=8)
        self.output_var = ctk.StringVar(
            value=os.path.join(BASE_DIR, "output"))
        ctk.CTkEntry(
            bf, textvariable=self.output_var, height=32
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=8)
        ctk.CTkButton(
            bf, text="찾기", width=60, height=32,
            command=self._pick_output
        ).grid(row=0, column=2, padx=5, pady=8)

        ctk.CTkButton(
            bf, text="📁 복사", width=90, height=36,
            fg_color="#2d7d46", hover_color="#3a9956",
            command=self._copy_files
        ).grid(row=0, column=3, padx=5, pady=8)

        ctk.CTkButton(
            bf, text="📁 이동", width=90, height=36,
            fg_color="#7d5a2d", hover_color="#99703a",
            command=self._move_files
        ).grid(row=0, column=4, padx=(5, 10), pady=8)

    def _pick_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path)

    # ─── Data / Filter / Sort ────────────

    def _refresh_data(self):
        if not self.db:
            return
        try:
            self.all_data = list(self.db.get_all())
            self._update_categories()
            self._update_badges()
            self._apply_filters()
            self._set_status(f"🔄 DB 로드: {len(self.all_data)}건")
        except Exception as e:
            self._set_status(f"❌ 로드 실패: {e}")

    def _update_categories(self):
        cats = set()
        for row in self.all_data:
            if len(row) > 4 and row[4]:
                cats.add(row[4].split("/")[0])
        cat_list = ["전체"] + sorted(cats)
        self.category_menu.configure(values=cat_list)
        self.category_var.set("전체")

    def _on_search_changed(self, *args):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self._apply_filters)

    def _apply_filters(self):
        keyword = self.search_var.get().strip().lower()
        category = self.category_var.get()

        data = self.all_data

        if category and category != "전체":
            data = [r for r in data
                    if len(r) > 4 and r[4]
                    and r[4].split("/")[0] == category]

        if keyword:
            def match(row):
                for idx in [2, 4, 5, 6, 7]:
                    if (len(row) > idx and row[idx]
                            and keyword in str(row[idx]).lower()):
                        return True
                return False
            data = [r for r in data if match(r)]

        if self.hide_missing.get():
            data = [r for r in data
                    if len(r) > 1 and r[1]
                    and os.path.exists(r[1])]

        self.filtered_data = list(data)

        if self.sort_col:
            self._sort_data()

        self._populate_table(self.filtered_data)

    def _sort_by_column(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False

        self._sort_data()
        self._populate_table(self.filtered_data)

        for c in self.tree["columns"]:
            base = self.tree.heading(c)["text"].rstrip(" ▲▼")
            if c == col:
                arrow = " ▼" if self.sort_reverse else " ▲"
                self.tree.heading(c, text=base + arrow)
            else:
                self.tree.heading(c, text=base)

    def _sort_data(self):
        idx = COL_INDEX.get(self.sort_col)
        if idx is None:
            return

        def sort_key(row):
            val = row[idx] if len(row) > idx else None
            if val is None:
                return (1, "")
            if isinstance(val, (int, float)):
                return (0, val)
            return (0, str(val).lower())

        self.filtered_data.sort(
            key=sort_key, reverse=self.sort_reverse)

    def _populate_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            conf = row[8] if len(row) > 8 and row[8] else 0
            dur = row[3] if len(row) > 3 and row[3] else 0
            file_path = row[1] if len(row) > 1 else ""
            file_exists = file_path and os.path.exists(file_path)
            tag = "exists" if file_exists else "missing"

            self.tree.insert("", "end", values=(
                row[2] if len(row) > 2 else "",
                row[4] if len(row) > 4 else "",
                row[5] if len(row) > 5 else "",
                row[6] if len(row) > 6 else "",
                row[7] if len(row) > 7 else "",
                f"{conf * 100:.0f}%",
                f"{dur:.1f}s",
            ), tags=(tag,))

        self.count_label.configure(text=f"{len(rows)}건")

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx < len(self.filtered_data):
            row = self.filtered_data[idx]
            self.current_file_path = (
                row[1] if len(row) > 1 else None)
            self.playing_label.configure(text=f"🎵 {row[2]}")

    def _on_double_click(self, event):
        self._on_select()
        self._play_audio()

    # ─── Playback ────────────────────────

    def _play_audio(self):
        if not self.current_file_path:
            self._set_status("⚠️ 파일을 먼저 선택하세요")
            return
        if not os.path.exists(self.current_file_path):
            self._set_status(
                f"❌ 파일 없음: {self.current_file_path}")
            return
        if not HAS_PYGAME:
            self._set_status("⚠️ pygame 미설치")
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.current_file_path)
            pygame.mixer.music.play()
            self._set_status(
                f"▶️ 재생 중: "
                f"{os.path.basename(self.current_file_path)}")
        except Exception as e:
            self._set_status(f"❌ 재생 오류: {e}")

    def _stop_audio(self):
        if HAS_PYGAME:
            pygame.mixer.music.stop()
        self._set_status("⏹ 정지")

    # ─── File Organize ───────────────────

    def _organize_files(self, move=False):
        output_dir = self.output_var.get().strip()
        if not output_dir:
            messagebox.showwarning("출력 폴더",
                                   "출력 폴더를 선택하세요.")
            return
        if not self.filtered_data:
            messagebox.showinfo("알림", "표시된 결과가 없습니다.")
            return

        action = "이동" if move else "복사"
        if not messagebox.askyesno(
                "확인",
                f"{len(self.filtered_data)}개 파일을 "
                f"{action}할까요?"):
            return

        count = 0
        for row in self.filtered_data:
            file_path = row[1] if len(row) > 1 else ""
            category = row[4] if len(row) > 4 else "Uncategorized"

            if not file_path or not os.path.exists(file_path):
                continue

            cat_parts = category.replace("\\", "/").split("/")
            dest_dir = os.path.join(output_dir, *cat_parts)
            os.makedirs(dest_dir, exist_ok=True)

            dest = os.path.join(
                dest_dir, os.path.basename(file_path))
            if os.path.exists(dest):
                name, ext = os.path.splitext(
                    os.path.basename(file_path))
                n = 1
                while os.path.exists(dest):
                    dest = os.path.join(
                        dest_dir, f"{name}_{n}{ext}")
                    n += 1
            try:
                if move:
                    shutil.move(file_path, dest)
                else:
                    shutil.copy2(file_path, dest)
                count += 1
            except Exception as e:
                print(f"[ERROR] {file_path}: {e}")

        self._set_status(
            f"✅ {count}개 파일 {action} 완료 → {output_dir}")

    def _copy_files(self):
        self._organize_files(move=False)

    def _move_files(self):
        self._organize_files(move=True)

    # ─── Cleanup ─────────────────────────

    def _on_close(self):
        if HAS_PYGAME:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
        if self.db:
            self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = BrowserGUI()
    app.mainloop()