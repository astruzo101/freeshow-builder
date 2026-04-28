"""Simple GUI for FreeShow Service Builder using PySide6."""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QTextEdit, QMessageBox, QComboBox
)

from .core import (
    TXTParser, SongMatcher, BibleExtractor, VerseFileMatcher,
    TemplateManager, FreeShowBuilder,
)


class BuilderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FreeShow Service Builder")
        self.setMinimumSize(600, 500)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        
        title = QLabel("<h2>FreeShow Service Builder</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addWidget(QLabel("Schedule File (.txt):"))
        row = QHBoxLayout()
        self.schedule_edit = QLineEdit("schedule.txt")
        row.addWidget(self.schedule_edit)
        btn = QPushButton("Browse...")
        btn.clicked.connect(self.browse_schedule)
        row.addWidget(btn)
        layout.addLayout(row)
        
        layout.addWidget(QLabel("Song Database Folder:"))
        row = QHBoxLayout()
        self.song_edit = QLineEdit(self._default_song_db())
        row.addWidget(self.song_edit)
        btn = QPushButton("Browse...")
        btn.clicked.connect(self.browse_songs)
        row.addWidget(btn)
        layout.addLayout(row)
        
        layout.addWidget(QLabel("Bible File (.fsb/.json):"))
        row = QHBoxLayout()
        self.bible_edit = QLineEdit(self._default_bible())
        row.addWidget(self.bible_edit)
        btn = QPushButton("Browse...")
        btn.clicked.connect(self.browse_bible)
        row.addWidget(btn)
        layout.addLayout(row)
        
        layout.addWidget(QLabel("Output Project File:"))
        row = QHBoxLayout()
        self.output_edit = QLineEdit("service_presentation.project")
        row.addWidget(self.output_edit)
        btn = QPushButton("Browse...")
        btn.clicked.connect(self.browse_output)
        row.addWidget(btn)
        layout.addLayout(row)
        
        layout.addWidget(QLabel("Song Template:"))
        self.song_template = QComboBox()
        self.song_template.setEditable(True)
        self.song_template.addItem("0-Canciones")
        self.song_template.setCurrentText("0-Canciones")
        layout.addWidget(self.song_template)
        
        layout.addWidget(QLabel("Bible Template:"))
        self.bible_template = QComboBox()
        self.bible_template.setEditable(True)
        self.bible_template.addItem("0-Biblia")
        self.bible_template.setCurrentText("0-Biblia")
        layout.addWidget(self.bible_template)
        
        refresh = QPushButton("Refresh Templates from FreeShow")
        refresh.clicked.connect(self.load_templates)
        layout.addWidget(refresh)
        
        self.build_btn = QPushButton("BUILD PROJECT")
        self.build_btn.setStyleSheet("font-size: 16px; padding: 12px;")
        self.build_btn.clicked.connect(self.build)
        layout.addWidget(self.build_btn)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        layout.addWidget(QLabel("Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        # PySide6 compatibility: QTextEdit.setMaximumBlockCount not available in all versions
        try:
            self.log.document().setMaximumBlockCount(100)
        except (AttributeError, RuntimeError):
            pass
        layout.addWidget(self.log)
        
        self.load_templates()
    
    def _default_song_db(self):
        docs = os.path.join(os.path.expanduser("~"), "Documents", "FreeShow", "Shows")
        return docs if os.path.isdir(docs) else "./database/songs/"
    
    def _default_bible(self):
        docs = os.path.join(os.path.expanduser("~"), "Documents", "FreeShow", "Bibles")
        if os.path.isdir(docs):
            for f in os.listdir(docs):
                if f.endswith(".fsb"):
                    return os.path.join(docs, f)
        return "./database/Biblia-Dios-Habla-Hoy.fsb"
    
    def browse_schedule(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Schedule", "", "Text Files (*.txt)")
        if path:
            self.schedule_edit.setText(path)
    
    def browse_songs(self):
        path = QFileDialog.getExistingDirectory(self, "Select Song Database")
        if path:
            self.song_edit.setText(path)
    
    def browse_bible(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Bible", "", "Bible Files (*.fsb *.json)")
        if path:
            self.bible_edit.setText(path)
    
    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Project Files (*.project)")
        if path:
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
            self.log.append("Loaded " + str(len(names)) + " templates from FreeShow")
        except Exception as e:
            self.log.append("Could not load templates: " + str(e))
    
    def build(self):
        self.build_btn.setEnabled(False)
        self.progress.setValue(10)
        
        try:
            schedule = self.schedule_edit.text()
            song_db = self.song_edit.text()
            bible = self.bible_edit.text()
            output = self.output_edit.text()
            
            if not os.path.isfile(schedule):
                QMessageBox.critical(self, "Error", "Schedule not found: " + schedule)
                return
            if not os.path.isdir(song_db):
                QMessageBox.critical(self, "Error", "Song folder not found: " + song_db)
                return
            
            song_tmpl = self.song_template.currentText()
            bible_tmpl = self.bible_template.currentText()
            
            self.log.append("Building with templates: " + song_tmpl + ", " + bible_tmpl)
            self.progress.setValue(25)
            
            TemplateManager.ensure([song_tmpl, bible_tmpl])
            self.progress.setValue(40)
            
            songs, verses = TXTParser(schedule).parse()
            self.log.append("Found " + str(len(songs)) + " songs, " + str(len(verses)) + " verses")
            self.progress.setValue(55)
            
            sm = SongMatcher(song_db)
            be = BibleExtractor(bible)
            vm = VerseFileMatcher(song_db)
            
            song_refs, song_data = sm.match(songs)
            self.progress.setValue(70)
            
            bible_refs, bible_data = be.build_shows(verses, vm=vm)
            self.progress.setValue(85)
            
            FreeShowBuilder().build(
                song_refs, song_data, bible_refs, bible_data,
                output, logo_path=""
            )
            self.progress.setValue(100)
            
            self.log.append("SUCCESS: Project saved to " + output)
            QMessageBox.information(self, "Success", "Project built!\n" + output)
            
        except Exception as e:
            self.log.append("ERROR: " + str(e))
            QMessageBox.critical(self, "Build Failed", str(e))
        finally:
            self.build_btn.setEnabled(True)


def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = BuilderWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()