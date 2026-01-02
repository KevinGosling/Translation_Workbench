# Translation Workbench

A desktop application for translating Norwegian novels to English with integrated concordance tools, lemmatization, and workflow management.

## Overview

Translation Workbench is a specialized CAT (Computer-Assisted Translation) tool designed for literary translation from Norwegian Bokmål to English. It provides sentence-level segmentation, automatic lemmatization, concordance building, and integration with external resources like the Norwegian Academy Dictionary (NAOB) and Google Translate.

## Features

### Core Translation Features
- **Sentence-level segmentation** with TMX storage
- **Side-by-side source/target editing** with keyboard navigation
- **Source file organization** with progress tracking per chapter
- **Google Translate integration** for quick suggestions
- **Word document export** with customizable formatting

### Linguistic Analysis
- **Automatic tokenization** using Stanza NLP (Norwegian Bokmål)
- **Lemmatization and POS tagging** for all source text
- **Concordance building** to view all occurrences of lemmas
- **Frequency analysis** to identify common words
- **Lemma suppression** to filter out common/irrelevant words

### Reference Tools
- **NAOB dictionary integration** with custom URL overrides
- **Custom meaning notes** for each lemma
- **Clickable word navigation** to jump between concordances
- **Search functionality** by wordform

### Project Management
- **Dashboard** with translation progress statistics
- **Auto-backup system** (TMX files backed up every 30 minutes)
- **Multiple project support**
- **Preference management** (default view, suppressions)

## System Requirements

### Platform
- Windows 10/11 (primary target)
- Linux/macOS (should work but untested)

### Software Dependencies
- Python 3.8 or higher
- Web browser (Chrome, Firefox, or Edge recommended)

### Hardware Recommendations
- 4GB RAM minimum (8GB+ recommended for large projects)
- 500MB+ free disk space

## Installation

### 1. Install Python
Download and install Python from [python.org](https://www.python.org/downloads/)

Ensure "Add Python to PATH" is checked during installation.

### 2. Install Dependencies

Open Command Prompt in the application folder and run:

```bash
pip install flask --break-system-packages
pip install stanza --break-system-packages
pip install python-docx --break-system-packages
```

### 3. Download Stanza Norwegian Model

Run Python and execute:

```python
import stanza
stanza.download('nb')  # Norwegian Bokmål
```

This downloads the Norwegian language model (~200MB).

## Quick Start

### Running the Application

#### Option 1: Command Line
```bash
cd TranslationWorkbenchApp
python app.py
```

Then open your browser to: `http://127.0.0.1:5000`

#### Option 2: Batch File (Windows)
Create `run_workbench.bat`:

```batch
@echo off
echo Starting Translation Workbench...
echo Please wait while the server starts...
start /B python app.py
timeout /t 5 /nobreak > nul
start http://127.0.0.1:5000
```

Double-click to run.

### Creating Your First Project

1. Create a folder: `TranslationWorkbenchApp/Projects/YourProjectName/`
2. Create a subfolder: `Projects/YourProjectName/source/`
3. Add your source text files (`.txt`) to the `source/` folder
4. Reload the application - your project will appear

### Initial Setup Workflow

1. **Dashboard** → Extract Frequencies (processes all source files)
2. **Dashboard** → Suppress unwanted POS tags (ADP, AUX, DET, etc.)
3. **Dashboard** → Build Concordances (creates searchable concordances)
4. **Workbench** → Select source file and start translating

## Project Structure

```
TranslationWorkbenchApp/
├── app.py                      # Main Flask application
├── lib/
│   └── tmx_processing.py       # TMX and NLP processing
├── templates/
│   ├── index.html             # Project selection
│   ├── dashboard.html         # Project dashboard
│   ├── workbench.html         # Translation interface
│   └── components/
│       ├── editor_panel.html
│       └── reference_panel.html
└── Projects/
    └── YourProject/
        ├── source/             # Source .txt files
        ├── target/
        │   └── project.tmx     # Translation memory
        ├── cache/              # Lemma caches and preferences
        ├── backups/            # Auto TMX backups (max 3)
        └── exports/            # Exported Word documents
```

## File Formats

### Source Files
- Plain text (`.txt`)
- UTF-8 encoding
- Double line breaks between paragraphs
- Named sequentially (e.g., `01_chapter.txt`, `02_chapter.txt`)

### TMX (Translation Memory eXchange)
- XML-based translation memory format
- Stores source/target segments
- Includes tokenization data as properties
- Paragraph-end markers for formatting

## Usage Guide

### Translation Workflow

1. **Select source file** in editor panel dropdown
2. **Click source words** to view concordances in reference panel
3. **Edit target text** in green boxes
4. **Press Enter** to save and move to next segment
5. **Use Google Translate arrow** (▲) for suggestions
6. **Export to Word** when chapter is complete

### Concordance Features

- **Click any lemma** in reference panel to view all occurrences
- **Click words in concordances** to navigate to other lemmas
- **Edit translations** directly in concordance tables
- **Search by wordform** using search box
- **Add custom meanings** and NAOB URLs

### Dashboard Features

- **File statistics** show progress per source file
- **Export buttons** create formatted Word documents
- **Frequency extraction** processes source text (one-time)
- **Concordance building** creates searchable reference data
- **Suppression management** filters out common words

## Word Export Format

Exported documents use the following formatting:

- **Page**: A4 with 2.54cm margins
- **Header**: Project name (8pt, right-aligned, uppercase)
- **Footer**: "CHAPTER {number} - {page}" (8pt, right-aligned)
- **Heading**: Chapter number (12pt bold, 12pt space below)
- **Body**: Times New Roman 12pt, double-spaced, 0.5cm first-line indent
- **Paragraphs**: 12pt space between paragraphs

## Technology Stack & Licenses

### Backend

#### Flask 3.0+
- **License**: BSD-3-Clause
- **Use**: Web application framework
- **Website**: https://flask.palletsprojects.com/

#### Stanza 1.8+
- **License**: Apache License 2.0
- **Use**: Natural language processing (tokenization, POS tagging, lemmatization)
- **Website**: https://stanfordnlp.github.io/stanza/
- **Note**: Includes pre-trained models for Norwegian Bokmål

#### python-docx 1.1+
- **License**: MIT License
- **Use**: Microsoft Word document creation
- **Website**: https://python-docx.readthedocs.io/

### Frontend

#### Vanilla JavaScript
- **License**: N/A (no libraries used)
- **Use**: UI interactions, AJAX, concordance management

### Data Formats

#### TMX (Translation Memory eXchange)
- **License**: Open standard (LISA OSCAR)
- **Use**: Translation memory storage
- **Specification**: https://www.gala-global.org/tmx-14b

### External Integrations

#### NAOB (Norwegian Academy Dictionary)
- **License**: Free to access (external website)
- **Use**: Dictionary lookups for Norwegian words
- **Website**: https://naob.no/

#### Google Translate
- **License**: Terms of Service apply (external website)
- **Use**: Translation suggestions (user-initiated)
- **Website**: https://translate.google.com/

## License Information Summary

This application uses the following open-source components:

- **Flask**: BSD-3-Clause (permissive, commercial use allowed)
- **Stanza**: Apache 2.0 (permissive, commercial use allowed)
- **python-docx**: MIT (permissive, commercial use allowed)

**All licenses allow commercial use, modification, and distribution.**

The application code itself is provided as-is for personal or commercial use. No warranty is provided.

## Data Privacy

### Local Data Storage
- All project data stored locally on your computer
- No data sent to external servers (except user-initiated Google Translate/NAOB lookups)
- TMX files contain your translations

### External Services
- **NAOB lookups**: Opens dictionary website in browser (subject to NAOB terms)
- **Google Translate**: Opens Google Translate in browser (subject to Google terms)
- No automatic data transmission to these services

## Backup & Data Safety

### Automatic Backups
- TMX files backed up every 30 minutes
- Maximum 3 backups kept per project
- Stored in `Projects/{ProjectName}/backups/`

### Manual Backups
Recommended: Periodically copy entire `Projects/` folder to external storage

### Critical Files
- `project.tmx` - Your translation work (backed up automatically)
- `lemmas.json` - Concordance data (can be rebuilt)
- `lemmas_master.json` - Frequency data (can be rebuilt)

## Troubleshooting

### Application won't start
- Check Python is installed: `python --version`
- Verify all dependencies installed: `pip list`
- Check port 5000 is not in use by another application

### Stanza errors
- Ensure Norwegian model downloaded: `python -c "import stanza; stanza.download('nb')"`
- Check internet connection during initial model download

### Slow performance
- Large projects (80,000+ words) may take time to load
- Concordance building can take several minutes for first time
- Consider suppressing more POS tags to reduce concordance size

### TMX file corrupted
- Check `backups/` folder for recent backup
- Copy most recent backup to `target/project.tmx`

### Export fails
- Ensure `python-docx` is installed
- Check write permissions in `exports/` folder
- Verify segments have translations (empty segments skipped)

## Performance Notes

### Initial Processing
- **Frequency extraction**: ~1-5 minutes for 80,000 words
- **Concordance building**: ~2-10 minutes depending on suppressions
- **First load**: Slightly slower as data is parsed

### Ongoing Usage
- **Loading workbench**: Near-instant after v1.12 optimizations
- **Opening concordances**: <100ms per lemma (on-demand loading)
- **Saving segments**: Instant (writes to TMX)
- **Auto-backup**: <1 second (runs in background)

## Known Limitations

- Single user (local application, not multi-user)
- Norwegian Bokmål only (Stanza model specific)
- Requires manual source file preparation
- No built-in spell checker
- No translation memory matching (beyond concordances)
- Browser-based UI (requires web browser)

## Future Enhancements (Potential)

- Nynorsk support
- Translation memory fuzzy matching
- Terminology database
- Quality assurance checks
- Collaborative features
- Cloud backup integration
- Mobile/tablet interface

## Version History

### v1.12 (Current)
- On-demand concordance loading for instant startup
- TMX as single source of truth
- Google Translate integration
- Automatic backup system
- Word export with custom formatting
- File statistics dashboard

### v1.11
- Tokenization stored in TMX
- Eliminated Stanza processing on load

### v1.8
- Server-sent events for progress tracking
- Debug console for troubleshooting

### v1.7
- Batch rendering for large reference panels

### v1.5
- Source file filtering
- Multi-file project support

### v1.1
- Concordance building system
- Suppression management

## Support & Contributing

This is a personal tool developed for literary translation work. No formal support is provided, but suggestions and bug reports are welcome.

For issues or questions, refer to the troubleshooting section above.

## Acknowledgments

- **Stanford NLP Group** for the Stanza library
- **Flask/Pallets team** for the web framework
- **Norwegian Academy** for NAOB dictionary access
- **Translation memory standards community** for TMX format

## Author

Developed for Norwegian-to-English literary translation workflow.

## Disclaimer

This software is provided "as is" without warranty of any kind. Users are responsible for backing up their work and ensuring proper licensing for any external services used (NAOB, Google Translate).

The application facilitates translation work but does not claim rights to any translations produced using it.
