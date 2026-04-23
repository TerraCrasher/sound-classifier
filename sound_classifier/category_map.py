"""
AudioSet Ontology 기반 카테고리 매핑
- AST 527 클래스 → 대분류 / 중분류 자동 매핑
"""

import os
import json
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ONTOLOGY_URL = (
    "https://raw.githubusercontent.com/audioset/ontology/master/ontology.json"
)
ONTOLOGY_PATH = os.path.join(DATA_DIR, "ontology.json")
MAPPING_PATH = os.path.join(DATA_DIR, "category_mapping.json")

# ── 대분류 (AudioSet 최상위 카테고리 ID) ──
TOP_CATEGORIES = {
    "Human sounds":          ["/m/0dgw9r"],
    "Animal":                ["/m/0jbk"],
    "Music":                 ["/m/04rlf"],
    "Natural sounds":        ["/t/dd00092"],
    "Sounds of things":      ["/t/dd00041"],
    "Source-ambiguous":       ["/t/dd00098"],
    "Channel/Environment":   ["/t/dd00123"],
}


def _ensure_ontology():
    """AudioSet Ontology JSON 다운로드 (없을 때만)"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ONTOLOGY_PATH):
        print("📥 AudioSet Ontology 다운로드 중...")
        urllib.request.urlretrieve(ONTOLOGY_URL, ONTOLOGY_PATH)
        print("✅ Ontology 다운로드 완료")


def _load_ontology() -> list:
    _ensure_ontology()
    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_category_map(class_names: list) -> dict:
    """
    클래스명 리스트 → 카테고리 매핑 dict 생성

    Args:
        class_names: 모델의 클래스명 리스트 (AST 527개)

    Returns:
        { "Speech": {"large": "Human sounds", "medium": "Speech"}, ... }
    """
    # ── 캐시 확인 (클래스 수 일치 시 재사용) ──
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached_meta = cached.get("_meta", {})
        if cached_meta.get("num_classes") == len(class_names):
            cached.pop("_meta", None)
            return cached

        # ── Ontology 로드 & 인덱싱 ──
    ontology = _load_ontology()

    name_to_entry = {}
    id_to_entry = {}
    for entry in ontology:
        name_to_entry[entry["name"]] = entry
        # 대소문자 무시 매칭용
        name_to_entry[entry["name"].lower()] = entry
        id_to_entry[entry["id"]] = entry

    # 대분류 ID → 대분류명 역매핑
    top_id_map = {}
    for cat_name, ids in TOP_CATEGORIES.items():
        for mid in ids:
            top_id_map[mid] = cat_name

    def _find_top_category(entry: dict) -> str:
        """재귀적 부모 탐색 → 대분류 반환"""
        visited = set()
        queue = [entry["id"]]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id in top_id_map:
                return top_id_map[current_id]

            current = id_to_entry.get(current_id)
            if current and "parent_ids" in current:
                queue.extend(current["parent_ids"])

        return "기타"

    def _find_medium_category(entry: dict) -> str:
        """중분류 (대분류 바로 아래 레벨) 반환"""
        # 자기 자신의 부모가 대분류이면 → 자기가 중분류
        for pid in entry.get("parent_ids", []):
            if pid in top_id_map:
                return entry["name"]

        # 부모의 부모가 대분류이면 → 부모가 중분류
        for pid in entry.get("parent_ids", []):
            parent = id_to_entry.get(pid)
            if parent:
                for gpid in parent.get("parent_ids", []):
                    if gpid in top_id_map:
                        return parent["name"]

        # 3단계 이상 깊은 경우 → 가장 가까운 상위 반환
        for pid in entry.get("parent_ids", []):
            parent = id_to_entry.get(pid)
            if parent:
                return parent["name"]

        return entry["name"]

    # ── 매핑 생성 ──
    category_map = {}
    matched = 0
    unmatched = []

    for class_name in class_names:
        # 정확 매칭 → 소문자 매칭 순서로 시도
        entry = name_to_entry.get(class_name)
        if not entry:
            entry = name_to_entry.get(class_name.lower())

        if entry:
            category_map[class_name] = {
                "large": _find_top_category(entry),
                "medium": _find_medium_category(entry),
            }
            matched += 1
        else:
            category_map[class_name] = {
                "large": "기타",
                "medium": class_name,
            }
            unmatched.append(class_name)

    # ── 캐시 저장 (메타 정보 포함) ──
    save_data = dict(category_map)
    save_data["_meta"] = {
        "num_classes": len(class_names),
        "matched": matched,
        "unmatched_count": len(unmatched),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 카테고리 매핑 완료 ({matched}/{len(class_names)}개 매칭)")
    if unmatched:
        print(f"   ⚠️ 미매칭 {len(unmatched)}개: {unmatched[:5]}...")

    return category_map


def get_category(category_map: dict, label: str) -> dict:
    """
    단일 라벨의 카테고리 조회 (편의 함수)

    Returns:
        {"large": "대분류", "medium": "중분류"}
    """
    return category_map.get(label, {"large": "기타", "medium": label})


def get_output_path(category_map: dict, label: str) -> str:
    """
    분류 결과 → 출력 폴더 경로 생성

    Returns:
        "대분류/중분류" 형태의 상대 경로
    """
    cat = get_category(category_map, label)
    # 폴더명에 사용 불가 문자 제거
    large = _safe_dirname(cat["large"])
    medium = _safe_dirname(cat["medium"])
    return os.path.join(large, medium)


def _safe_dirname(name: str) -> str:
    """폴더명 안전 변환"""
    for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        name = name.replace(ch, '_')
    return name.strip()