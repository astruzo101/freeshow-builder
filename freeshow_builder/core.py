#!/usr/bin/env python3
"""FreeShow Service Builder — Production Grade"""

import hashlib
import json
import logging
import os
import re
import time
import uuid
from typing import Any

from thefuzz import fuzz, process

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

RESOLUTION = {"width": 1920, "height": 1080}
SONG_MATCH_THRESHOLD = 80
VERSE_MATCH_THRESHOLD = 88
BOOK_MATCH_THRESHOLD = 85

# --- TEMPLATE NAMES (for FreeShow template lookup) ---
SONG_TEMPLATE_NAME = "0-Canciones"
BIBLE_TEMPLATE_NAME = "0-Biblia"

# --- SECTION DISPLAY NAMES (shown in FreeShow project list) ---
SONG_SECTION_NAME = "Canciones"
BIBLE_SECTION_NAME = "Versos Biblicos"
# ---------------------------------------------------------------


def now() -> int:
    return int(time.time())


def strip_notes(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[TEXT OMITTED\]", "", text, flags=re.IGNORECASE)
    return text.strip()


def mk_line(value: str, style: str = "") -> dict:
    return {"align": "", "text": [{"value": value, "style": style}]}


def mk_item(lines: list[dict], style: str = "", align: str = "") -> dict:
    return {"type": "text", "lines": lines, "style": style, "align": align, "language": ""}


def mk_child_slide(text: str, resolution: dict = RESOLUTION) -> dict:
    return {
        "group": None,
        "color": None,
        "settings": {"color": "", "resolution": resolution},
        "notes": "",
        "items": [mk_item([mk_line(text, "font-size:48px;")],
                         "top:60px;left:50px;height:960px;width:1820px;", "")]
    }


def mk_section_show(title: str, resolution: dict = RESOLUTION) -> dict:
    slide_id = str(uuid.uuid4())
    layout_id = str(uuid.uuid4())
    return {
        "name": title,
        "category": None,
        "settings": {"activeLayout": layout_id, "template": None},
        "timestamps": {"created": now(), "modified": now(), "used": None},
        "meta": {},
        "slides": {
            slide_id: {
                "group": "",
                "color": None,
                "settings": {"color": "", "resolution": resolution},
                "notes": "",
                "items": [mk_item([mk_line(title, "font-size:96px;font-weight:bold;")],
                                 "top:300px;left:50px;height:500px;width:1820px;", "")]
            }
        },
        "layouts": {layout_id: {"name": "Default", "notes": "", "slides": [{"id": slide_id}]}},
        "media": {}
    }


class TXTParser:
    SONG_RE = re.compile(r"^#\s*(.+)$")

    def __init__(self, filepath: str):
        self.filepath = filepath

    def parse(self) -> tuple[list[str], list[dict]]:
        songs, verses = [], []
        if not os.path.isfile(self.filepath):
            log.error(f"Schedule not found: {self.filepath}")
            return songs, verses
        with open(self.filepath, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if (m := self.SONG_RE.match(line)):
                    songs.append(m.group(1).strip())
                elif (ref := self._parse_verse(line)):
                    verses.append(ref)
                else:
                    log.warning(f"Treating unrecognized line as song: '{line}'")
                    songs.append(line)
        return songs, verses

    @staticmethod
    def _parse_verse(text: str) -> dict | None:
        text = text.strip().lower().replace("–", "-").replace("—", "-")
        m = re.match(r"^([a-z\d\s]+)\s+([\d:.,\-]+)$", text)
        if not m:
            return None
        book_raw = m.group(1).strip()
        ref_part = m.group(2).strip()
        if ":" in ref_part:
            ch_str, rest = ref_part.split(":", 1)
            ranges = [p.strip() for p in rest.split(",") if p.strip()]
        elif "." in ref_part:
            ch_str, rest = ref_part.split(".", 1)
            ranges = [p.strip() for p in rest.split(",") if p.strip()]
        else:
            parts = ref_part.split(",", 1)
            if len(parts) < 2:
                return None
            ch_str, rest = parts[0].strip(), parts[1].strip()
            ranges = [p.strip() for p in rest.split(",") if p.strip()]
        try:
            chapter = int(ch_str)
        except ValueError:
            return None
        verses = []
        for part in ranges:
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                try:
                    for v in range(int(start_str.strip()), int(end_str.strip()) + 1):
                        if v > 0 and v not in verses:
                            verses.append(v)
                except ValueError:
                    continue
            else:
                try:
                    v = int(part.strip())
                    if v > 0 and v not in verses:
                        verses.append(v)
                except ValueError:
                    continue
        verses.sort()
        return {
            "raw": f"{book_raw.title()} {chapter}:{','.join(ranges)}",
            "book": book_raw,
            "chapter": chapter,
            "verses": verses,
            "ranges": ranges
        }

    _parse_verse_ref = _parse_verse


class SongMatcher:
    def __init__(self, songs_dir: str):
        self._dir = songs_dir
        self.index: dict[str, str] = {}
        self._load()

    def _load(self):
        if not os.path.isdir(self._dir):
            log.error(f"Songs dir not found: {self._dir}")
            return
        for entry in os.listdir(self._dir):
            if not entry.lower().endswith(".show"):
                continue
            fp = os.path.join(self._dir, entry)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                data = raw[1] if isinstance(raw, list) and len(raw) >= 2 else raw if isinstance(raw, dict) else None
                name = str(data.get("name", "")).strip() if data else ""
                if name:
                    self.index[name] = fp
            except Exception as e:
                log.debug(f"Skipping {entry}: {e}")
        log.info(f"Indexed {len(self.index)} songs")

    def search(self, query: str, limit: int = 10) -> list[tuple[str, int]]:
        if not self.index:
            return []
        results = process.extract(query, list(self.index.keys()), scorer=fuzz.WRatio, limit=limit)
        return [(r[0], r[1]) for r in results if isinstance(r, (list, tuple)) and len(r) >= 2 and r[1] >= 30]

    def match(self, queries: list[str], song_template: str | None = None) -> tuple[list[dict], dict[str, dict]]:
        template_name = song_template if song_template else SONG_TEMPLATE_NAME
        tid = TemplateManager.get_id(template_name)
        refs, data = [], {}
        for q in queries:
            best = process.extractOne(q, list(self.index.keys()), scorer=fuzz.ratio)
            if not best or not isinstance(best, (list, tuple)) or len(best) < 2 or best[1] < SONG_MATCH_THRESHOLD:
                log.warning(f"No match for song '{q}'")
                refs.append({"id": None, "raw": q})
                continue
            name, score = best[0], best[1]
            try:
                with open(self.index[name], "r", encoding="utf-8") as f:
                    raw = json.load(f)
                sid = str(raw[0]) if isinstance(raw, list) and len(raw) >= 2 else str(raw.get("id", uuid.uuid4()))
                show = raw[1] if isinstance(raw, list) and len(raw) >= 2 else raw if isinstance(raw, dict) else None
                if not show:
                    refs.append({"id": None, "raw": q})
                    continue
                show["settings"] = show.get("settings", {})
                if not isinstance(show["settings"], dict):
                    show["settings"] = {}
                if tid:
                    show["settings"]["template"] = tid
                    log.info(f"Applied template '{template_name}' (id={tid}) to song '{name}'")
                else:
                    log.warning(f"Template '{template_name}' not found; song '{name}' will not have a template")
                data[sid] = show
                refs.append({"id": sid, "raw": q})
                log.info(f"Song '{q}' -> '{name}' ({score})")
            except Exception as e:
                log.error(f"Failed loading song '{name}': {e}")
                refs.append({"id": None, "raw": q})
        return refs, data

    search_songs = search
    match_songs = match


class BibleExtractor:
    def __init__(self, bible_path: str):
        self.bible_path = bible_path
        self.book_map: dict[str, str] = {}
        self._db: dict[str, Any] = {}
        self._books_list: list[dict] = []
        self._load()

    def _load(self):
        if not os.path.isfile(self.bible_path):
            log.warning(f"Bible not found: {self.bible_path}")
            return
        ext = os.path.splitext(self.bible_path)[1].lower()
        try:
            if ext == ".fsb":
                self._load_fsb()
            elif ext == ".json":
                self._load_json()
            else:
                log.error(f"Unsupported Bible format: {ext}")
        except Exception as e:
            log.error(f"Bible load failed: {e}")

    def _load_fsb(self):
        with open(self.bible_path, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
        idx = text.find("{")
        if idx == -1:
            idx = text.find("[")
        if idx == -1:
            log.error("No JSON payload found inside FSB")
            return
        payload, _ = json.JSONDecoder().raw_decode(text, idx)
        if isinstance(payload, list):
            self._db = payload[1] if len(payload) >= 2 and isinstance(payload[1], dict) else \
                       payload[0] if len(payload) >= 1 and isinstance(payload[0], dict) else {}
        elif isinstance(payload, dict):
            self._db = payload
        self._build_book_map()

    def _load_json(self):
        with open(self.bible_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._db = payload[1] if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], dict) else \
                   payload[0] if isinstance(payload, list) and len(payload) >= 1 and isinstance(payload[0], dict) else \
                   payload if isinstance(payload, dict) else {}
        self._build_book_map()

    def _norm(self, s: str) -> str:
        return s.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

    def _build_book_map(self):
        books = self._db.get("books")
        if isinstance(books, list):
            self._books_list = books
            for i, bk in enumerate(books):
                if not isinstance(bk, dict):
                    continue
                n = self._norm(bk.get("name", ""))
                ab = bk.get("abbreviation", "")
                if n:
                    self.book_map[n] = str(i)
                if ab:
                    self.book_map[self._norm(ab)] = str(i)
        elif isinstance(books, dict):
            for key, info in books.items():
                n = self._norm(info.get("name", "")) if isinstance(info, dict) else self._norm(info) if isinstance(info, str) else ""
                ab = info.get("abbreviation", "") if isinstance(info, dict) else ""
                if n:
                    self.book_map[n] = key
                if ab:
                    self.book_map[self._norm(ab)] = key
        else:
            for key, info in self._db.items():
                if key in ("version", "name", "books") or not isinstance(info, dict):
                    continue
                n = self._norm(info.get("name", ""))
                ab = info.get("abbreviation", "")
                if n:
                    self.book_map[n] = key
                if ab:
                    self.book_map[self._norm(ab)] = key
        log.info(f"Bible loaded: {len(self.book_map)} books")

    def _book_key(self, raw: str) -> str | None:
        n = self._norm(raw)
        if n in self.book_map:
            return self.book_map[n]
        for name, key in self.book_map.items():
            if fuzz.ratio(n, name) >= BOOK_MATCH_THRESHOLD:
                return key
        return None

    def _book_data(self, key: str) -> dict | None:
        if self._books_list:
            try:
                i = int(key)
                return self._books_list[i] if 0 <= i < len(self._books_list) else None
            except ValueError:
                return None
        books = self._db.get("books")
        if isinstance(books, dict):
            return books.get(key)
        return self._db.get(key)

    def _chapter_data(self, book_data: dict, chapter: int) -> Any:
        if not isinstance(book_data, dict):
            return None
        chapters = book_data.get("chapters")
        if isinstance(chapters, dict):
            return chapters.get(str(chapter)) or chapters.get(chapter)
        if isinstance(chapters, list) and chapter - 1 < len(chapters):
            return chapters[chapter - 1]
        return book_data.get(str(chapter)) or book_data.get(chapter)

    def _extract_verse_text(self, verse_obj: Any) -> str:
        if isinstance(verse_obj, str):
            return verse_obj.strip()
        if isinstance(verse_obj, dict):
            for key in ("text", "value", "content", "verse", "scripture"):
                if key in verse_obj and isinstance(verse_obj[key], str):
                    return verse_obj[key].strip()
            for k, v in verse_obj.items():
                if k in ("number", "id", "idx", "ref", "verse_number"):
                    continue
                if isinstance(v, str) and len(v) > 5:
                    return v.strip()
        if isinstance(verse_obj, (list, tuple)) and len(verse_obj) > 0:
            for item in verse_obj:
                if isinstance(item, str) and len(item) > 5:
                    return item.strip()
                if isinstance(item, dict):
                    return self._extract_verse_text(item)
        return ""

    def _verse_text(self, chapter_data: Any, verse_num: int) -> str:
        if chapter_data is None:
            return ""
        if isinstance(chapter_data, dict):
            val = chapter_data.get(str(verse_num))
            val = chapter_data.get(verse_num) if val is None else val
            if val is not None:
                return self._extract_verse_text(val)
            verses = chapter_data.get("verses")
            if isinstance(verses, list) and verse_num - 1 < len(verses):
                return self._extract_verse_text(verses[verse_num - 1])
            if isinstance(verses, dict):
                val = verses.get(str(verse_num)) or verses.get(verse_num)
                if val is not None:
                    return self._extract_verse_text(val)
        if isinstance(chapter_data, list) and verse_num - 1 < len(chapter_data):
            return self._extract_verse_text(chapter_data[verse_num - 1])
        return ""

    def preview(self, parsed: dict) -> str:
        bk, ch, vs = parsed.get("book", ""), parsed.get("chapter"), parsed.get("verses", [])
        key = self._book_key(bk)
        if not key:
            return f"[Book not found: {bk}]"
        bd = self._book_data(key)
        cd = self._chapter_data(bd, ch) if bd else None
        if not cd:
            return f"[Chapter {ch} not found]"
        out = []
        for v in vs:
            t = self._verse_text(cd, v)
            if t:
                out.append(f"{v}. {strip_notes(t)}")
        if not out:
            return "[No verses found]"
        return "\n".join(out[:6]) + ("\n..." if len(out) > 6 else "")

    def build_shows(self, refs: list[dict], vm=None, resolution: dict = RESOLUTION,
                    verse_file_matcher=None, bible_template: str | None = None) -> tuple[list[dict], dict[str, dict]]:
        template_name = bible_template if bible_template else BIBLE_TEMPLATE_NAME
        show_refs, show_data = [], {}
        if verse_file_matcher is not None and vm is None:
            vm = verse_file_matcher
        for p in refs:
            if vm is not None:
                sid, d = vm.find(p)
                if sid is not None:
                    show_refs.append({"id": sid, "raw": p["raw"]})
                    show_data[sid] = d
                    continue
            bk, ch, vs = p.get("book", ""), p.get("chapter"), p.get("verses", [])
            key = self._book_key(bk)
            if not key:
                log.warning(f"Book not found: '{bk}'")
                show_refs.append({"id": None, "raw": p["raw"]})
                continue
            bd = self._book_data(key)
            cd = self._chapter_data(bd, ch) if bd else None
            if not cd:
                log.warning(f"Chapter {ch} not found in {bk}")
                show_refs.append({"id": None, "raw": p["raw"]})
                continue
            sid = str(uuid.uuid4())
            show_refs.append({"id": sid, "raw": p["raw"]})
            show_data[sid] = self._build_verse_show(p, cd, resolution, sid, template_name)
        return show_refs, show_data

    def _build_verse_show(self, parsed: dict, chapter_data: Any, resolution: dict,
                         show_id: str, bible_template: str | None = None) -> dict:
        bk, ch, vs = parsed.get("book", ""), parsed.get("chapter"), parsed.get("verses", [])
        title = parsed.get("raw", f"{bk.title()} {ch}:{min(vs)}-{max(vs)}" if vs else f"{bk.title()} {ch}")
        slides: dict[str, Any] = {}
        layouts: dict[str, Any] = {}
        child_ids: list[str] = []
        pid = str(uuid.uuid4())
        slides[pid] = {
            "group": "",
            "color": "#5825f5",
            "settings": {"color": "", "resolution": resolution},
            "notes": "",
            "items": [mk_item([mk_line(title, "font-size:72px;font-weight:bold;")],
                             "top:400px;left:50px;height:200px;width:1820px;", "")],
            "children": []
        }
        for v in vs:
            cid = str(uuid.uuid4())
            child_ids.append(cid)
            text = strip_notes(self._verse_text(chapter_data, v))
            slides[cid] = mk_child_slide(f"{v}  {text}", resolution)
        if child_ids:
            slides[pid]["children"] = child_ids
        lid = str(uuid.uuid4())
        layouts[lid] = {
            "name": "Default",
            "notes": "",
            "slides": [{"id": pid}] + [{"id": c} for c in child_ids]
        }
        template_name = bible_template if bible_template else BIBLE_TEMPLATE_NAME
        tid = TemplateManager.get_id(template_name)
        settings: dict[str, Any] = {"activeLayout": lid}
        if tid:
            settings["template"] = tid
            log.info(f"Applied template '{template_name}' (id={tid}) to verse '{title}'")
        else:
            log.warning(f"Template '{template_name}' not found for verse '{title}'")
        return {
            "name": title,
            "category": None,
            "settings": settings,
            "timestamps": {"created": now(), "modified": now(), "used": None},
            "meta": {},
            "slides": slides,
            "layouts": layouts,
            "media": {}
        }

    preview_verse = preview
    get_verses_as_show = build_shows


class VerseFileMatcher:
    def __init__(self, songs_dir: str):
        self._dir = songs_dir
        self.index: dict[str, str] = {}
        if not os.path.isdir(self._dir):
            return
        for entry in os.listdir(self._dir):
            if not entry.lower().endswith(".show"):
                continue
            fp = os.path.join(self._dir, entry)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                data = raw[1] if isinstance(raw, list) and len(raw) >= 2 else raw if isinstance(raw, dict) else None
                name = str(data.get("name", "")).strip().lower() if data else ""
                if name and ("biblia" in name or "verso" in name or "scripture" in name):
                    self.index[name] = fp
            except Exception:
                pass

    def _norm(self, book: str, chapter: int, verses: list[int]) -> str:
        b = book.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        return f"{b} {chapter}:{min(verses)}-{max(verses)}" if verses else f"{b} {chapter}"

    def find(self, parsed: dict) -> tuple[str | None, dict | None]:
        n = self._norm(parsed["book"], parsed["chapter"], parsed["verses"])
        if n in self.index:
            try:
                with open(self.index[n], "r", encoding="utf-8") as f:
                    raw = json.load(f)
                sid = str(raw[0]) if isinstance(raw, list) and len(raw) >= 2 else str(raw.get("id", uuid.uuid4()))
                data = raw[1] if isinstance(raw, list) and len(raw) >= 2 else raw if isinstance(raw, dict) else None
                if data:
                    return sid, data
            except Exception:
                pass
        for name, fp in self.index.items():
            if fuzz.ratio(n, name) >= VERSE_MATCH_THRESHOLD:
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    sid = str(raw[0]) if isinstance(raw, list) and len(raw) >= 2 else str(raw.get("id", uuid.uuid4()))
                    data = raw[1] if isinstance(raw, list) and len(raw) >= 2 else raw if isinstance(raw, dict) else None
                    if data:
                        return sid, data
                except Exception:
                    pass
        return None, None

    find_verse_file = find


class TemplateManager:
    _cache: dict[str, str] | None = None

    @staticmethod
    def _config_path() -> str:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        return os.path.join(docs, "FreeShow", "Config", "templates.json")

    @staticmethod
    def load() -> dict[str, Any]:
        path = TemplateManager._config_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            log.warning(f"Failed reading templates.json: {e}")
            return {}

    @classmethod
    def _build_cache(cls) -> dict[str, str]:
        templates = cls.load()
        cache: dict[str, str] = {}
        for tid, info in templates.items():
            if isinstance(info, dict):
                name = info.get("name")
                if name:
                    cache[name] = tid
        cls._cache = cache
        return cache

    @classmethod
    def get_id(cls, name: str) -> str | None:
        if cls._cache is not None:
            return cls._cache.get(name)
        return cls._build_cache().get(name)

    @classmethod
    def ensure(cls, template_names: list[str]) -> dict[str, str]:
        path = cls._config_path()
        templates = cls.load()
        updated = False
        result: dict[str, str] = {}
        for name in template_names:
            tid = None
            for existing_id, info in templates.items():
                if isinstance(info, dict) and info.get("name") == name:
                    tid = existing_id
                    break
            if tid is None:
                tid = hashlib.md5(name.encode()).hexdigest()[:11]
                templates[tid] = cls._make_stub(name)
                updated = True
                log.info(f"Created template stub: {name} (id={tid})")
            result[name] = tid
        if updated:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
            log.info(f"Updated templates.json: {path}")
        else:
            log.info("All templates already present in templates.json")
        cls._cache = result
        return result

    @staticmethod
    def _make_stub(name: str) -> dict:
        return {
            "name": name,
            "color": None,
            "category": None,
            "items": [
                {
                    "style": "top:0.00px;left:0.00px;height:1081.00px;width:1920.00px;",
                    "type": "text",
                    "lines": [
                        {
                            "align": "",
                            "text": [
                                {
                                    "value": "Text",
                                    "style": "font-family:'Arial';font:normal 700 condensed 100px 'Arial';font-size:100px;"
                                }
                            ]
                        }
                    ]
                }
            ],
            "modified": int(time.time() * 1000)
        }

    @classmethod
    def list_templates(cls) -> list[str]:
        return list(cls._build_cache().keys())


class FreeShowBuilder:
    """Builds a FreeShow .project file.

    Two APIs:
      - build_mixed(items, output_path, project_name, logo_path)
        Preserves mixed song/verse order. Used by GUI and interactive CLI.
      - build(song_refs, song_data, bible_refs, bible_data, output_path, logo_path)
        Groups all songs then all verses. Legacy file-based mode.
    """

    def build_mixed(self, items: list[dict], output_path: str,
                    project_name: str = "Service Presentation", logo_path: str = "") -> None:
        """Build project preserving mixed item order.

        items: list of dicts with keys:
            - "type": "song" or "verse"
            - "ref": {"id": str|None, "raw": str}
            - "data": dict (the show object) or None
        """
        shows: dict[str, Any] = {}
        order: list[dict] = []
        last_type: str | None = None

        for item in items:
            itype = item["type"]
            ref = item.get("ref", {})
            data = item.get("data")
            sid = ref.get("id") if ref else None

            if not sid or not data:
                log.warning(f"Skipping unmatched {itype}: {ref.get('raw', '') if ref else ''}")
                continue

            # Add section header when type changes
            if itype != last_type:
                section_name = SONG_SECTION_NAME if itype == "song" else BIBLE_SECTION_NAME
                section_id = str(uuid.uuid4())
                order.append({"id": section_id, "type": "section", "name": section_name, "notes": "", "color": ""})
                shows[section_id] = mk_section_show(section_name)
                last_type = itype

            shows[sid] = data
            order.append({"id": sid})

        # Optional logo
        if logo_path and os.path.isfile(logo_path):
            lid = os.path.basename(logo_path)
            mid = str(uuid.uuid4())
            sid = str(uuid.uuid4())
            lyid = str(uuid.uuid4())
            shows[lid] = {
                "name": "Logo",
                "category": None,
                "settings": {"activeLayout": lyid, "template": None},
                "timestamps": {"created": now(), "modified": now(), "used": None},
                "meta": {},
                "slides": {
                    sid: {
                        "group": "",
                        "color": None,
                        "settings": {},
                        "notes": "",
                        "items": [{"type": "media", "src": mid, "style": "top:0;left:0;height:100%;width:100%;"}]
                    }
                },
                "layouts": {
                    lyid: {"name": "Default", "notes": "", "slides": [{"id": sid, "background": mid}]}
                },
                "media": {mid: {"path": logo_path, "name": os.path.basename(logo_path)}}
            }
            order.insert(0, {"id": lid})

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "project": {
                    "name": project_name,
                    "created": now(),
                    "modified": now(),
                    "parent": "/",
                    "shows": order
                },
                "shows": shows,
                "overlays": {},
                "files": []
            }, f, indent=2, ensure_ascii=False)
        log.info(f"Project '{project_name}' written to {output_path}")

    def build(self, song_refs, song_data, bible_refs, bible_data, output_path, logo_path=""):
        """Legacy API: groups all songs, then all verses."""
        shows: dict[str, Any] = {}
        order: list[dict] = []

        if any(r.get("id") for r in song_refs):
            sid = str(uuid.uuid4())
            order.append({"id": sid, "type": "section", "name": SONG_SECTION_NAME, "notes": "", "color": ""})
            shows[sid] = mk_section_show(SONG_SECTION_NAME)

        for ref in song_refs:
            sid = ref.get("id")
            if not sid or sid not in song_data:
                log.warning(f"Skipping unmatched song: {ref.get('raw', '')}")
                continue
            shows[sid] = song_data[sid]
            order.append({"id": sid})

        if any(r.get("id") for r in bible_refs):
            sid = str(uuid.uuid4())
            order.append({"id": sid, "type": "section", "name": BIBLE_SECTION_NAME, "notes": "", "color": ""})
            shows[sid] = mk_section_show(BIBLE_SECTION_NAME)

        for ref in bible_refs:
            sid = ref.get("id")
            if not sid or sid not in bible_data:
                log.warning(f"Skipping unmatched verse: {ref.get('raw', '')}")
                continue
            shows[sid] = bible_data[sid]
            order.append({"id": sid})

        if logo_path and os.path.isfile(logo_path):
            lid = os.path.basename(logo_path)
            mid = str(uuid.uuid4())
            sid = str(uuid.uuid4())
            lyid = str(uuid.uuid4())
            shows[lid] = {
                "name": "Logo",
                "category": None,
                "settings": {"activeLayout": lyid, "template": None},
                "timestamps": {"created": now(), "modified": now(), "used": None},
                "meta": {},
                "slides": {
                    sid: {
                        "group": "",
                        "color": None,
                        "settings": {},
                        "notes": "",
                        "items": [{"type": "media", "src": mid, "style": "top:0;left:0;height:100%;width:100%;"}]
                    }
                },
                "layouts": {
                    lyid: {"name": "Default", "notes": "", "slides": [{"id": sid, "background": mid}]}
                },
                "media": {mid: {"path": logo_path, "name": os.path.basename(logo_path)}}
            }
            order.insert(0, {"id": lid})

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "project": {
                    "name": "Service Presentation",
                    "created": now(),
                    "modified": now(),
                    "parent": "/",
                    "shows": order
                },
                "shows": shows,
                "overlays": {},
                "files": []
            }, f, indent=2, ensure_ascii=False)
        log.info(f"Project written to {output_path}")
