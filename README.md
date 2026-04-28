# FreeShow Service Builder

Build FreeShow service presentations from a text schedule or interactively — no file editing required.

## Features

- **Interactive GUI** — Search songs live, preview Bible verses, drag-and-drop your service lineup
- **Interactive CLI** — Build services on the spot from the terminal
- **File-based mode** — Still supports plain `.txt` schedule files for repeatable weekly workflows
- **Automatic song matching** — Fuzzy-searches your `.show` song database with ranked results
- **Bible verse generation** — Builds slides from `.fsb`/`.json` Bible files with live preview
- **Template integration** — Auto-applies FreeShow templates by ID; choose templates per-build from the GUI
- **Cross-platform executables** — Windows `.exe` and macOS binaries built automatically via GitHub Actions

## Quick Start (Pre-built Executables)

### Windows
1. Download `FreeShowBuilder.exe` from [Releases](../../releases)
2. Double-click to open the GUI
3. Select your song database folder, Bible file, and templates
4. Search songs, add verses, arrange your lineup
5. Click **BUILD PROJECT**

### macOS
1. Download `FreeShowBuilder` from [Releases](../../releases)
2. Open Terminal, `cd` to the download folder, run:
   ```bash
   chmod +x FreeShowBuilder
   ./FreeShowBuilder
   ```
3. Build your service interactively

## Quick Start (Python)

```bash
pip install freeshow-builder

# Interactive GUI
build-show --gui

# Interactive CLI
build-show --interactive

# File-based mode
build-show --schedule service.txt --song-db "~/Documents/FreeShow/Shows"
```

## Interactive GUI Mode

No schedule file needed. The GUI has two panels:

**Left panel — Add items**
- **Song search**: Type a name, hit Enter, see fuzzy-matched results. Double-click or click "Add Selected Song"
- **Verse entry**: Type a reference like `John 3:16-18`, click **Preview** to see the text, then **Add This Verse**
- **Database selection**: Browse for your song folder and Bible file

**Right panel — Service lineup**
- Drag and drop to reorder songs and verses
- Use **Up/Down/Remove** buttons to fine-tune
- Click **Clear All** to start fresh
- Select **Song template** and **Bible template** from dropdowns (reads from FreeShow's `templates.json`)

Click **BUILD PROJECT** when ready.

## Interactive CLI Mode

Run `build-show --interactive` and follow the prompts:

```
============================================================
  FreeShow Service Builder — Interactive Mode
============================================================

[SONGS] Add songs to your service

Song name (or 'done' to finish songs): hosanna
  Matches:
    1. Hosanna (95%) <<< BEST
    2. Hosanna (Praise is Rising) (78%)
  Select (number or Enter for #1):
  -> Selected: Hosanna

[VERSES] Add Bible references

Bible reference (e.g. 'John 3:16-18', or 'done'): romanos 5:10-20
  -> Parsed: Romanos 5:10-20
  Preview: 10. Porque siendo...
  Add this verse? [Y/n]: y

Build project? [Y/n]: y

✅ Project saved to: service_presentation.project
```

## File-Based Mode (Schedule.txt)

Create a plain text file (`schedule.txt`):

```text
# Amazing Grace
# How Great Thou Art
John 3:16-18
Romans 8:28
# Blessed Assurance
```

- Lines starting with `#` are songs (searched in your song database)
- Other lines are Bible references (e.g. `John 3:16-18`)

Run:
```bash
build-show --schedule schedule.txt
```

Override templates per-run:
```bash
build-show --schedule schedule.txt --song-template "Worship" --bible-template "Scripture"
```

## File Structure

```
FreeShow/
  Config/
    templates.json          # Templates are read from here
  Shows/
    *.show                  # Your song database
  Bibles/
    *.fsb / *.json          # Bible files
  Assets/
    logo.png                # Optional logo
```

## Templates

The builder applies FreeShow templates by their **ID** (not by name), so styling works correctly. The GUI and CLI let you pick template names each time you build.

| Default name | Used for |
|--------------|----------|
| `0-Canciones` | Song slides |
| `0-Biblia` | Bible verse slides |

If these templates don't exist in FreeShow, the builder creates stubs automatically in `templates.json`.

## Building from Source

```bash
git clone https://github.com/astruzo101/freeshow-builder.git
cd freeshow-builder
pip install -e ".[gui,build]"

# Run CLI
build-show --schedule schedule.txt

# Run GUI
build-show --gui

# Run interactive CLI
build-show --interactive

# Build executables locally
pyinstaller --onefile --windowed --name FreeShowBuilder scripts/gui_entry.py
```

## Auto-Build via GitHub Actions

Push a tag to automatically build and release executables:

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions will build `.exe` (Windows) and standalone binaries (macOS) and attach them to the release.

## Project Structure

| File | Purpose |
|------|---------|
| `freeshow_builder/core.py` | Engine: parser, fuzzy matcher, Bible extractor, template manager, project builder |
| `freeshow_builder/gui.py` | PySide6 interactive graphical interface |
| `freeshow_builder/cli.py` | Command-line interface with `--gui`, `--interactive`, and file modes |
| `freeshow_builder/interactive.py` | Interactive CLI prompts for building without a schedule file |
| `scripts/cli_entry.py` | PyInstaller entry point for CLI executable |
| `scripts/gui_entry.py` | PyInstaller entry point for GUI executable |
| `.github/workflows/` | Auto-build Windows & macOS executables, create GitHub releases |

## License

MIT
