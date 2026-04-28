"""Modern interactive GUI for FreeShow Service Builder.
Build services on the spot — no schedule.txt needed.
"""

import os
import sys
from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QTextEdit, QMessageBox, QComboBox, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QGroupBox
)

from .core import (
    TXTParser, SongMatcher, BibleExtractor, VerseFileMatcher,
    TemplateManager, FreeShowBuilder,
)


class ModernBuilderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FreeShow Service Builder")
        self.setMinimumSize(900, 650)

        self.song_db_path = self._default_song_db()
        self.bible_db_path = self._default_bible()
        self.output_path = "service_presentation.project"

        self.song_matcher: SongMatcher | None = None
        self.bible_extractor: BibleExtractor | None = None
        self.verse_matcher: VerseFileMatcher | None = None

        self.service_items: list[dict] = []  # {"type": "song"/"verse", "name": str, "data": Any}

        self._init_ui()
        self._load_databases()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # === LEFT PANEL: Add Items ===
        left = QVBoxLayout()
        left.setSpacing(12)

        left.addWidget(QLabel("<h2>FreeShow Service Builder</h2>"))

        # Database settings
        db_group = QGroupBox("Databases")
        db_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("Songs:"))
        self.song_db_label = QLabel(self._shorten_path(self.song_db_path))
        self.song_db_label.setStyleSheet("color: #666;")
        row.addWidget(self.song_db_label, 1)
        btn = QPushButton("Browse...")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.browse_song_db)
        row.addWidget(btn)
        db_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Bible:"))
        self.bible_db_label = QLabel(self._shorten_path(self.bible_db_path))
        self.bible_db_label.setStyleSheet("color: #666;")
        row.addWidget(self.bible_db_label, 1)
        btn = QPushButton("Browse...")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.browse_bible_db)
        row.addWidget(btn)
        db_layout.addLayout(row)

        db_group.setLayout(db_layout)
        left.addWidget(db_group)

        # Add Songs
        song_group = QGroupBox("Add Songs")
        song_layout = QVBoxLayout()

        row = QHBoxLayout()
        self.song_search = QLineEdit()
        self.song_search.setPlaceholderText("Type song name...")
        self.song_search.returnPressed.connect(self.search_songs)
        row.addWidget(self.song_search)
        btn = QPushButton("Search")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.search_songs)
        row.addWidget(btn)
        song_layout.addLayout(row)

        self.song_results = QListWidget()
        self.song_results.setMaximumHeight(120)
        self.song_results.itemDoubleClicked.connect(self.add_song_from_result)
        song_layout.addWidget(self.song_results)

        add_song_btn = QPushButton("➕ Add Selected Song")
        add_song_btn.clicked.connect(self.add_song_from_result)
        song_layout.addWidget(add_song_btn)

        song_group.setLayout(song_layout)
        left.addWidget(song_group)

        # Add Verses
        verse_group = QGroupBox("Add Bible Verses")
        verse_layout = QVBoxLayout()

        row = QHBoxLayout()
        self.verse_input = QLineEdit()
        self.verse_input.setPlaceholderText("e.g. John 3:16-18 or Romans 8:28")
        self.verse_input.returnPressed.connect(self.preview_verse)
        row.addWidget(self.verse_input)
        btn = QPushButton("Preview")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.preview_verse)
        row.addWidget(btn)
        verse_layout.addLayout(row)

        self.verse_preview = QTextEdit()
        self.verse_preview.setReadOnly(True)
        self.verse_preview.setMaximumHeight(100)
        self.verse_preview.setPlaceholderText("Verse preview will appear here...")
        verse_layout.addWidget(self.verse_preview)

        add_verse_btn = QPushButton("➕ Add This Verse")
        add_verse_btn.clicked.connect(self.add_verse)
        verse_layout.addWidget(add_verse_btn)

        verse_group.setLayout(verse_layout)
        left.addWidget(verse_group)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMinimumWidth(380)

        # === RIGHT PANEL: Service Lineup ===
        right = QVBoxLayout()
        right.setSpacing(12)

        right.addWidget(QLabel("<h3>📋 Service Lineup</h3>"))

        self.service_list = QListWidget()
        self.service_list.setDragDropMode(QListWidget.InternalMove)
        self.service_list.model().rowsMoved.connect(self.on_items_reordered)
        self.service_list.setMinimumWidth(300)
        right.addWidget(self.service_list)

        # Controls
        ctrl = QHBoxLayout()

        up_btn = QPushButton("⬆ Up")
        up_btn.setFixedWidth(70)
        up_btn.clicked.connect(self.move_up)
        ctrl.addWidget(up_btn)

        down_btn = QPushButton("⬇ Down")
        down_btn.setFixedWidth(70)
        down_btn.clicked.connect(self.move_down)
        ctrl.addWidget(down_btn)

        rm_btn = QPushButton("🗑 Remove")
        rm_btn.setFixedWidth(80)
        rm_btn.clicked.connect(self.remove_item)
        ctrl.addWidget(rm_btn)

        ctrl.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self.clear_all)
        ctrl.addWidget(clear_btn)

        right.addLayout(ctrl)

        # Templates
        tmpl = QHBoxLayout()
        tmpl.addWidget(QLabel("Song template:"))
        self.song_template = QComboBox()
        self.song_template.setEditable(True)
        self.song_template.addItem("0-Canciones")
        tmpl.addWidget(self.song_template, 1)

        tmpl.addWidget(QLabel("Bible template:"))
        self.bible_template = QComboBox()
        self.bible_template.setEditable(True)
        self.bible_template.addItem("0-Biblia")
        tmpl.addWidget(self.bible_template, 1)

        refresh = QPushButton("🔄")
        refresh.setFixedWidth(40)
        refresh.setToolTip("Refresh templates from FreeShow")
        refresh.clicked.connect(self.load_templates)
        tmpl.addWidget(refresh)

        right.addLayout(tmpl)

        # Output
        row = QHBoxLayout()
        row.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit(self.output_path)
        row.addWidget(self.output_edit, 1)
        btn = QPushButton("Browse...")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.browse_output)
        row.addWidget(btn)
        right.addLayout(row)

        # Progress and Build
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        right.addWidget(self.progress)

        self.build_btn = QPushButton("🔨 BUILD PROJECT")
        self.build_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 16px;
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #999; }
        """)
        self.build_btn.clicked.connect(self.build_project)
        right.addWidget(self.build_btn)

        self.status_label = QLabel("Ready. Add songs and verses to build your service.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666;")
        right.addWidget(self.status_label)

        right_widget = QWidget()
        right_widget.setLayout(right)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        main_layout.addWidget(splitter)

        self.load_templates()

    def _default_song_db(self):
        docs = os.path.join(os.path.expanduser("~"), "Documents", "FreeShow", "Shows")
        return docs if os.path.isdir(docs) else ""

    def _default_bible(self):
        docs = os.path.join(os.path.expanduser("~"), "Documents", "FreeShow", "Bibles")
        if os.path.isdir(docs):
            for f in sorted(os.listdir(docs)):
                if f.endswith(".fsb"):
                    return os.path.join(docs, f)
        return ""

    def _shorten_path(self, path: str, max_len: int = 40) -> str:
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len-3):]

    def _load_databases(self):
        if self.song_db_path and os.path.isdir(self.song_db_path):
            self.song_matcher = SongMatcher(self.song_db_path)
            self.status_label.setText(f"Loaded {len(self.song_matcher.index)} songs")
        if self.bible_db_path and os.path.isfile(self.bible_db_path):
            self.bible_extractor = BibleExtractor(self.bible_db_path)
            self.verse_matcher = VerseFileMatcher(self.song_db_path)

    def browse_song_db(self):
        path = QFileDialog.getExistingDirectory(self, "Select Song Database", self.song_db_path)
        if path:
            self.song_db_path = path
            self.song_db_label.setText(self._shorten_path(path))
            self.song_matcher = SongMatcher(path)
            self.verse_matcher = VerseFileMatcher(path)
            self.status_label.setText(f"Loaded {len(self.song_matcher.index)} songs")

    def browse_bible_db(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Bible", "", "Bible Files (*.fsb *.json)")
        if path:
            self.bible_db_path = path
            self.bible_db_label.setText(self._shorten_path(path))
            self.bible_extractor = BibleExtractor(path)
            self.status_label.setText("Bible loaded")

    def search_songs(self):
        if not self.song_matcher:
            QMessageBox.warning(self, "No Database", "Select a song database first.")
            return
        query = self.song_search.text().strip()
        if not query:
            return

        self.song_results.clear()
        results = self.song_matcher.search(query, limit=10)
        for name, score in results:
            item = QListWidgetItem(f"{name}  ({score}%)")
            item.setData(Qt.UserRole, name)
            self.song_results.addItem(item)

        if not results:
            self.song_results.addItem("No matches found")

    def add_song_from_result(self):
        item = self.song_results.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        if not name:
            return

        self.service_items.append({"type": "song", "name": name, "data": None})
        self._refresh_service_list()
        self.song_search.clear()
        self.song_results.clear()
        self.status_label.setText(f"Added song: {name}")

    def preview_verse(self):
        if not self.bible_extractor:
            QMessageBox.warning(self, "No Bible", "Select a Bible file first.")
            return
        text = self.verse_input.text().strip()
        if not text:
            return

        parsed = TXTParser._parse_verse(text)
        if not parsed:
            self.verse_preview.setText("Invalid format. Use: Book Chapter:Verse-Verse\n(e.g. John 3:16-18, Romans 8:28)")
            return

        preview = self.bible_extractor.preview(parsed)
        self.verse_preview.setText(preview)
        self._current_parsed_verse = parsed

    def add_verse(self):
        if not hasattr(self, '_current_parsed_verse') or not self._current_parsed_verse:
            self.preview_verse()
            if not hasattr(self, '_current_parsed_verse') or not self._current_parsed_verse:
                return

        parsed = self._current_parsed_verse
        self.service_items.append({"type": "verse", "name": parsed['raw'], "data": parsed})
        self._refresh_service_list()
        self.verse_input.clear()
        self.verse_preview.clear()
        self.status_label.setText(f"Added verse: {parsed['raw']}")
        del self._current_parsed_verse

    def _refresh_service_list(self):
        self.service_list.clear()
        for item in self.service_items:
            icon = "🎵" if item["type"] == "song" else "📖"
            li = QListWidgetItem(f"{icon} {item['name']}")
            li.setData(Qt.UserRole, item)
            self.service_list.addItem(li)

    def on_items_reordered(self):
        new_order = []
        for i in range(self.service_list.count()):
            item = self.service_list.item(i).data(Qt.UserRole)
            new_order.append(item)
        self.service_items = new_order

    def move_up(self):
        idx = self.service_list.currentRow()
        if idx > 0:
            self.service_items[idx], self.service_items[idx-1] = self.service_items[idx-1], self.service_items[idx]
            self._refresh_service_list()
            self.service_list.setCurrentRow(idx-1)

    def move_down(self):
        idx = self.service_list.currentRow()
        if idx >= 0 and idx < len(self.service_items) - 1:
            self.service_items[idx], self.service_items[idx+1] = self.service_items[idx+1], self.service_items[idx]
            self._refresh_service_list()
            self.service_list.setCurrentRow(idx+1)

    def remove_item(self):
        idx = self.service_list.currentRow()
        if idx >= 0:
            del self.service_items[idx]
            self._refresh_service_list()

    def clear_all(self):
        if QMessageBox.question(self, "Confirm", "Clear all items?") == QMessageBox.Yes:
            self.service_items.clear()
            self._refresh_service_list()

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", self.output_path, "Project Files (*.project)")
        if path:
            self.output_path = path
            self.output_edit.setText(path)

    def load_templates(self):
        try:
            TemplateManager._cache = None
            names = TemplateManager.list_templates()
            self.song_template.clear()
            self.bible_template.clear()
            for name in names:
                self.song_template.addItem(name)
                self.bible_template.addItem(name)
            idx = self.song_template.findText("0-Canciones")
            if idx >= 0:
                self.song_template.setCurrentIndex(idx)
            idx = self.bible_template.findText("0-Biblia")
            if idx >= 0:
                self.bible_template.setCurrentIndex(idx)
        except Exception as e:
            pass

    def build_project(self):
        if not self.service_items:
            QMessageBox.warning(self, "Empty", "Add some songs or verses first.")
            return
        if not self.song_matcher:
            QMessageBox.warning(self, "No Database", "Select a song database first.")
            return

        self.build_btn.setEnabled(False)
        self.progress.setValue(10)

        try:
            song_tmpl = self.song_template.currentText()
            bible_tmpl = self.bible_template.currentText()
            TemplateManager.ensure([song_tmpl, bible_tmpl])
            self.progress.setValue(20)

            # Separate songs and verses
            songs = [item["name"] for item in self.service_items if item["type"] == "song"]
            verses = [item["data"] for item in self.service_items if item["type"] == "verse" and item["data"]]

            song_refs, song_data = self.song_matcher.match(songs)
            self.progress.setValue(50)

            bible_refs, bible_data = [], {}
            if verses and self.bible_extractor:
                bible_refs, bible_data = self.bible_extractor.build_shows(
                    verses, vm=self.verse_matcher
                )
            self.progress.setValue(80)

            FreeShowBuilder().build(
                song_refs, song_data, bible_refs, bible_data,
                self.output_edit.text(), logo_path=""
            )
            self.progress.setValue(100)

            self.status_label.setText(f"✅ Built: {self.output_edit.text()}")
            QMessageBox.information(self, "Success", f"Project saved!\n{self.output_edit.text()}")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_label.setText(f"❌ Error: {e}")
        finally:
            self.build_btn.setEnabled(True)


def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModernBuilderWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
