"""Interactive mode for FreeShow Service Builder.
Build a service presentation on the spot without a schedule file.
"""

import os
import sys

from .core import (
    TXTParser, SongMatcher, BibleExtractor, VerseFileMatcher,
    TemplateManager, FreeShowBuilder,
)


def prompt_song(sm: SongMatcher) -> str | None:
    """Interactively search for and select a song."""
    while True:
        query = input("\nSong name (or 'done' to finish songs): ").strip()
        if query.lower() in ('done', 'd', ''):
            return None

        results = sm.search(query, limit=5)
        if not results:
            print("  No matches found. Try again or type 'done'.")
            continue

        print("  Matches:")
        for i, (name, score) in enumerate(results, 1):
            marker = " <<< BEST" if i == 1 else ""
            print(f"    {i}. {name} ({score}%){marker}")
        print("    0. Skip / search again")

        choice = input("  Select (number or Enter for #1): ").strip()
        if choice == '0':
            continue

        idx = 0 if choice == '' else int(choice) - 1
        if 0 <= idx < len(results):
            selected = results[idx][0]
            print(f"  -> Selected: {selected}")
            return selected


def prompt_verse() -> dict | None:
    """Interactively parse a Bible reference."""
    while True:
        ref = input("\nBible reference (e.g. 'John 3:16-18', or 'done'): ").strip()
        if ref.lower() in ('done', 'd', ''):
            return None

        parsed = TXTParser._parse_verse(ref)
        if parsed:
            print(f"  -> Parsed: {parsed['raw']}")
            return parsed
        print("  Invalid format. Use: Book Chapter:Verse-Verse (e.g. Romanos 5:10-20)")


def interactive_build(song_db: str, bible_db: str, output: str,
                      song_template: str = "0-Canciones", bible_template: str = "0-Biblia"):
    """Run interactive service builder with explicit template names."""
    print("=" * 60)
    print("  FreeShow Service Builder — Interactive Mode")
    print("=" * 60)
    print(f"Song DB:      {song_db}")
    print(f"Bible:        {bible_db}")
    print(f"Output:       {output}")
    print(f"Song template:  {song_template}")
    print(f"Bible template: {bible_template}")
    print("-" * 60)

    if not os.path.isdir(song_db):
        print(f"ERROR: Song database not found: {song_db}")
        sys.exit(1)

    sm = SongMatcher(song_db)
    be = BibleExtractor(bible_db)
    vm = VerseFileMatcher(song_db)

    songs: list[str] = []
    verses: list[dict] = []

    # Collect songs
    print("\n[SONGS] Add songs to your service")
    while True:
        song = prompt_song(sm)
        if song is None:
            break
        songs.append(song)

    # Collect verses
    print("\n[VERSES] Add Bible references")
    while True:
        verse = prompt_verse()
        if verse is None:
            break
        preview = be.preview(verse)
        print(f"  Preview: {preview[:100]}...")
        confirm = input("  Add this verse? [Y/n]: ").strip().lower()
        if confirm not in ('n', 'no'):
            verses.append(verse)

    # Show summary
    print("\n" + "=" * 60)
    print("  SERVICE SUMMARY")
    print("=" * 60)
    print(f"Songs ({len(songs)}):")
    for s in songs:
        print(f"  - {s}")
    print(f"\nVerses ({len(verses)}):")
    for v in verses:
        print(f"  - {v['raw']}")

    confirm = input("\nBuild project? [Y/n]: ").strip().lower()
    if confirm in ('n', 'no'):
        print("Cancelled.")
        return

    # Build with explicit template names
    TemplateManager.ensure([song_template, bible_template])

    song_refs, song_data = sm.match(songs, song_template=song_template)
    bible_refs, bible_data = be.build_shows(verses, vm=vm, bible_template=bible_template)

    FreeShowBuilder().build(
        song_refs, song_data, bible_refs, bible_data,
        output, logo_path=""
    )

    print(f"\n✅ Project saved to: {output}")
    print("Open it in FreeShow: File → Import → Project")
