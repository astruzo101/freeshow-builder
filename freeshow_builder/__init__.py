"""FreeShow Service Builder - Build presentations from text schedules."""
__version__ = "1.0.0"

from .core import (
    TXTParser,
    SongMatcher,
    BibleExtractor,
    VerseFileMatcher,
    TemplateManager,
    FreeShowBuilder,
    now,
    RESOLUTION,
    SONG_TEMPLATE_NAME,
    BIBLE_TEMPLATE_NAME,
)
