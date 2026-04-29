"""Interactive mode for FreeShow Service Builder.
Build a service presentation on the spot without a schedule file.
Preserves mixed item order and supports custom project names.
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
                      song_template: str = "0-Canciones",
                      bible_template: str = "0-Biblia",
                      project_name: str = "Sunday Service"):
    """Run interactive service builder with explicit template names and custom project name."""
    print("=" * 60)
    print("  FreeShow Service Builder — Interactive Mode")
    print("=" * 60)
    print(f"Song DB:        {song_db}")
    print(f"Bible:          {bible_db}")
    print(f"Output:         {output}")
    print(f"Song template:  {song_template}")
    print(f"Bible template: {bible_template}")
    print(f"Project name:   {project_name}")
    print("-" * 60)

    if not os.path.isdir(song_db):
        print(f"ERROR: Song database not found: {song_db}")
        sys.exit(1)

    sm = SongMatcher(song_db)
    be = BibleExtractor(bible_db)
    vm = VerseFileMatcher(song_db)

    items: list[dict] = []  # Ordered mixed items

    # Collect songs and verses in order
    while True:
        print("\n[1] Add song  [2] Add verse  [3] Done")
        choice = input("Choice: ").strip()
        if choice == '1':
            song = prompt_song(sm)
            if song:
                items.append({"type": "song", "name": song})
                print(f"  Added song: {song}")
        elif choice == '2':
            verse = prompt_verse()
            if verse:
                preview = be.preview(verse)
                print(f"  Preview: {preview[:80]}...")
                confirm = input("  Add this verse? [Y/n]: ").strip().lower()
                if confirm not in ('n', 'no'):
                    items.append({"type": "verse", "name": verse['raw'], "data": verse})
                    print(f"  Added verse: {verse['raw']}")
        elif choice == '3':
            break
        else:
            print("  Invalid choice. Use 1, 2, or 3.")

    # Show summary
    print("\n" + "=" * 60)
    print("  SERVICE SUMMARY")
    print("=" * 60)
    for i, item in enumerate(items, 1):
        icon = "SONG" if item["type"] == "song" else "VERSE"
        print(f"  {i}. [{icon}] {item['name']}")

    confirm = input("\nBuild project? [Y/n]: ").strip().lower()
    if confirm in ('n', 'no'):
        print("Cancelled.")
        return

    # Build with mixed order preservation
    TemplateManager.ensure([song_template, bible_template])

    builder_items: list[dict] = []
    for item in items:
        if item["type"] == "song":
            song_refs, song_data = sm.match([item["name"]], song_template=song_template)
            if song_refs and song_refs[0].get("id"):
                ref = song_refs[0]
                data = song_data.get(ref["id"])
                builder_items.append({"type": "song", "ref": ref, "data": data})
        else:
            verse = item["data"]
            verse_refs, verse_data = be.build_shows([verse], vm=vm, bible_template=bible_template)
            if verse_refs and verse_refs[0].get("id"):
                ref = verse_refs[0]
                data = verse_data.get(ref["id"])
                builder_items.append({"type": "verse", "ref": ref, "data": data})

    FreeShowBuilder().build_mixed(
        builder_items,
        output,
        project_name=project_name,
        logo_path=""
    )

    print(f"\n✅ Project '{project_name}' saved to: {output}")
    print("Open it in FreeShow: File → Import → Project")
