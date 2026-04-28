"""Command-line interface for FreeShow Service Builder."""

import argparse
import os
import sys

from .core import (
    TXTParser, SongMatcher, BibleExtractor, VerseFileMatcher,
    TemplateManager, FreeShowBuilder,
    SONG_TEMPLATE_NAME, BIBLE_TEMPLATE_NAME,
)


def get_documents_path():
    """Cross-platform Documents folder detection."""
    home = os.path.expanduser("~")
    # Windows
    docs = os.path.join(home, "Documents")
    if os.path.isdir(docs):
        return docs
    # macOS
    docs = os.path.join(home, "Documents")
    if os.path.isdir(docs):
        return docs
    return home


def get_default_paths():
    """Return sensible defaults for each platform."""
    docs = get_documents_path()
    # FreeShow stores its data in Documents/FreeShow
    freeshow_base = os.path.join(docs, "FreeShow")

    return {
        "schedule": "schedule.txt",
        "song_db": os.path.join(freeshow_base, "Shows"),
        "bible_db": os.path.join(freeshow_base, "Bibles", "Biblia-Dios-Habla-Hoy.fsb"),
        "output": os.path.join(docs, "service_presentation.project"),
        "logo": os.path.join(freeshow_base, "Assets", "logo.png"),
    }


def main():
    defaults = get_default_paths()

    parser = argparse.ArgumentParser(
        description="Build FreeShow .project from a text schedule",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Use all defaults
  %(prog)s --schedule service.txt    # Custom schedule file
  %(prog)s --song-db ./my_songs/     # Custom song database
  %(prog)s --output ./service.project # Custom output path
        """
    )
    parser.add_argument("--schedule", default=defaults["schedule"],
                        help=f"Text schedule file (default: {defaults['schedule']})")
    parser.add_argument("--song-db", default=defaults["song_db"],
                        help=f"Directory with .show song files (default: {defaults['song_db']})")
    parser.add_argument("--bible-db", default=defaults["bible_db"],
                        help=f"Bible file (.fsb or .json) (default: {defaults['bible_db']})")
    parser.add_argument("--output", default=defaults["output"],
                        help=f"Output .project file (default: {defaults['output']})")
    parser.add_argument("--logo", default=defaults["logo"],
                        help=f"Logo image path (default: {defaults['logo']})")
    parser.add_argument("--song-template", default=SONG_TEMPLATE_NAME,
                        help=f"Template name for songs (default: {SONG_TEMPLATE_NAME})")
    parser.add_argument("--bible-template", default=BIBLE_TEMPLATE_NAME,
                        help=f"Template name for verses (default: {BIBLE_TEMPLATE_NAME})")
    parser.add_argument("--gui", action="store_true",
                        help="Launch graphical user interface")

    args = parser.parse_args()

    if args.gui:
        try:
            from .gui import run_gui
            run_gui()
            return
        except ImportError:
            print("GUI dependencies not installed. Install with: pip install freeshow-builder[gui]")
            sys.exit(1)

    # Validate inputs
    if not os.path.isfile(args.schedule):
        print(f"ERROR: Schedule file not found: {args.schedule}")
        sys.exit(1)

    if not os.path.isdir(args.song_db):
        print(f"ERROR: Song database directory not found: {args.song_db}")
        sys.exit(1)

    # Build
    print(f"FreeShow Service Builder v1.0.0")
    print(f"Schedule:   {args.schedule}")
    print(f"Song DB:    {args.song_db}")
    print(f"Bible:      {args.bible_db}")
    print(f"Output:     {args.output}")
    print(f"Song template:  {args.song_template}")
    print(f"Bible template: {args.bible_template}")
    print("-" * 50)

    TemplateManager.ensure([args.song_template, args.bible_template])

    songs, verses = TXTParser(args.schedule).parse()
    sm = SongMatcher(args.song_db)
    be = BibleExtractor(args.bible_db)
    vm = VerseFileMatcher(args.song_db)

    song_refs, song_data = sm.match(songs)
    bible_refs, bible_data = be.build_shows(verses, vm=vm)

    FreeShowBuilder().build(
        song_refs, song_data, bible_refs, bible_data,
        args.output, logo_path=args.logo
    )

    print(f"\nDone! Open {args.output} in FreeShow.")


if __name__ == "__main__":
    main()
