## Fakebook Set‑List PDF Builder

Create a single, gig‑ready PDF from a set list by mapping each line to numbered charts in `song-bank/` using GPT‑4.1, then merging the PDFs with a generated title page.

### Features
- Map free‑text set lists (including medleys) to chart indices via GPT‑4.1
- Merge numbered PDFs from `song-bank/` into one download
- Auto‑generated title page (gig name + date)
- Manage song metadata via CSV upload (saves to `song_data.json`)

## Prerequisites
- Python 3.9+
- PDF charts stored as `./song-bank/NNN.pdf` where `NNN` is 3 digits (001–999)
- OpenAI API key (enter in the app sidebar when prompted)

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Usage
1. Place charts in `./song-bank/` named like `001.pdf`, `002.pdf`, …
2. Start the app and open the sidebar:
   - Enter your OpenAI API key
   - Provide the Gig Name and Gig Date
3. Optional: Upload a CSV to update song metadata
   - Expected columns: `index,title,type`
   - Click “Save Song Data” to persist as `song_data.json`
4. Paste your set list (one song or medley per line) and click “Generate PDF”.
5. Download the merged PDF when ready.

### Example set list
```
I Think We're Alone Now/Pretty Woman
Wagon Wheel
Summer of '69
```

## How matching works (high level)
- The app builds a system prompt that includes your current song bank (from `song_data.json` or built‑in defaults).
- It asks GPT‑4.1 to return only the ordered list of 3‑digit indices, matching each line (or each part of a medley) to entries in the song bank.
- The app extracts those indices and merges the corresponding PDFs from `song-bank/`.

## File and data notes
- `song-bank/` must contain the numbered PDFs. Missing files are skipped with a warning in the UI.
- Song metadata lives in `song_data.json` (auto‑created/updated via CSV upload or reset to defaults in the sidebar).

## Troubleshooting
- “Please enter your OpenAI API key”: Enter the key in the sidebar.
- “No valid indices found”: Ensure your set list lines can be matched to entries in the song bank; try clearer spelling.
- “NNN.pdf not found … Skipping”: Add the missing numbered chart into `song-bank/`.
- PDF builds but looks wrong: Confirm filenames are exactly `NNN.pdf` and that each source PDF opens cleanly.

## Configuration and models
- LLM: OpenAI GPT‑4.1 (as specified in the project plan). Temperature 0.45, `max_tokens` 4000.

## Project structure (key files)
- `app.py`: Streamlit UI and core logic
- `song-bank/`: Numbered chart PDFs (not tracked by git by default)
- `song_data.json`: Persisted song metadata (generated at runtime)
- `requirements.txt`: Python dependencies
- `docs/`: Project plan and change log (ignored by git)

## Notes on differences from the project plan
- The current implementation uses PyPDF2 and ReportLab to build the title page and merge PDFs (no WeasyPrint).
- A CSV can be uploaded for metadata, but the app persists it to `song_data.json` and expects charts in `song-bank/`.


