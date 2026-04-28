# FreeShow Service Builder

Build FreeShow service presentations from a simple text schedule file.

## Features

- **Text-based scheduling** — Write your service in a plain `.txt` file
- **Automatic song matching** — Fuzzy-searches your `.show` song database
- **Bible verse generation** — Builds slides from `.fsb`/`.json` Bible files
- **Template integration** — Auto-applies FreeShow templates by ID
- **Cross-platform** — Windows & macOS executables, plus Python source
- **CLI & GUI** — Command-line for power users, graphical app for everyone else

## Quick Start (Pre-built Executables)

### Windows
1. Download `FreeShowBuilder.exe` from [Releases](../../releases)
2. Double-click to open the GUI
3. Select your schedule file, song folder, Bible file, and templates
4. Click **BUILD PROJECT**

### macOS
1. Download `FreeShowBuilder` from [Releases](../../releases)
2. Open Terminal, `cd` to the download folder, run:
   ```bash
   chmod +x FreeShowBuilder
   ./FreeShowBuilder
   ```
3. Select your files and click **BUILD PROJECT**

## Quick Start (Python)

```bash
pip install freeshow-builder
build-show --schedule service.txt --song-db "~/Documents/FreeShow/Shows"
```

Or launch the GUI:
```bash
pip install freeshow-builder[gui]
build-show --gui
```

## Schedule File Format

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

## Building from Source

```bash
git clone https://github.com/yourusername/freeshow-builder.git
cd freeshow-builder
pip install -e ".[gui,build]"

# Run CLI
build-show --schedule schedule.txt

# Run GUI
build-show --gui

# Build executables
pyinstaller --onefile --name FreeShowBuilder scripts/gui_entry.py
```

## Configuration

Edit these constants in the code (or use `--song-template` / `--bible-template` flags):

```python
SONG_TEMPLATE_NAME = "0-Canciones"    # Template for songs
BIBLE_TEMPLATE_NAME = "0-Biblia"      # Template for verses
```

## Development

| File | Purpose |
|------|---------|
| `freeshow_builder/core.py` | Main engine (parser, matcher, builder) |
| `freeshow_builder/cli.py` | Command-line interface |
| `freeshow_builder/gui.py` | PySide6 graphical interface |
| `scripts/cli_entry.py` | PyInstaller entry point for CLI |
| `scripts/gui_entry.py` | PyInstaller entry point for GUI |
| `.github/workflows/` | Auto-build Windows & macOS executables |

## Auto-Build via GitHub Actions

Push a tag to automatically build and release executables:

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions will build `.exe` (Windows) and standalone binaries (macOS) and attach them to the release.

## License

MIT
