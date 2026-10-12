## Fakebook Set-List PDF Builder

Turn a set list into a gig-ready PDF using GPT-6.1 Sol, numbered charts in
`song-bank/`, a title page, and a clickable table of contents.

### Setup

Install dependencies in your Python environment:

```powershell
python -m pip install -r requirements.txt
```

Save your OpenAI API key in the `.env` file **beside `app.py`**:

```dotenv
OPENAI_API_KEY=your-key-here
```

The key persists between sessions. `.env` is ignored by Git; `.env.example` is a
blank template. The app rereads the file on each interaction, so click Generate PDF
once you save a changed key. A system `OPENAI_API_KEY` is also supported when the
local file has no key. The key is never entered or displayed in the sidebar.

Place chart PDFs in `song-bank/`, named `001.pdf` through `999.pdf`, and run:

```powershell
streamlit run app.py
```

Configuration, metadata, and chart paths resolve relative to the app's folder,
even when launched from another directory.

### Usage

1. Enter the gig name and date in the sidebar.
2. Choose **low, medium, high, xhigh, or max** reasoning. Medium is the default.
   Both agents use the same setting; higher levels may take longer.
3. Optionally upload a CSV with `index,title,type` and click Save Song Data. Numeric
   indices are padded to three digits. Metadata is saved in `song_data.json`.
4. Paste the set list, one song or medley per line, and click Generate PDF.
5. Read the Song selection review and download the PDF.

```text
I Think We're Alone Now/Pretty Woman
Wagon Wheel
Summer of '69
```

### Selection and review

The selection agent maps the set list to ordered chart indices. A separate review
agent independently matches every nonempty input line against the full song bank,
without seeing the first agent's choices. Both use `gpt-6.1-sol` through the OpenAI
Responses API with the sidebar's `reasoning.effort` setting.

The app compares the lists, including order and repetitions. A concise GUI report identifies:

- Requested songs missing from the song bank, including missing medley components.
- Available songs omitted from the initial pull.
- Unexpected selections and ordering disagreements.
- Ambiguous titles or alternate arrangements needing review.
- Unknown chart IDs and missing chart PDF files.

Expand Review details for matches per line. Exact medleys take precedence over
separate charts; otherwise components are matched in order. Headings are ignored.
An all-missing set list still receives a review.

The review checks metadata and file availability, not the musical content of PDFs.
It reports disagreements rather than silently changing the pull. When issues
remain, the download is labeled as having review issues and contains only available,
known charts from the initial selection. If verification fails, a warning accompanies
the unverified download. If no charts are available, only the report is shown.

Results and downloads remain across interactions. Changed inputs produce a note
that the displayed result is previous until you generate again. Each generation uses
two API requests, adding latency and usage compared with one pass.

### Troubleshooting

- Missing key: fill in `OPENAI_API_KEY` in `.env` beside `app.py`.
- Rejected key: check the saved key and your API account.
- Rejected request: confirm your API project has access to `gpt-6.1-sol` and the
  selected reasoning effort. The app does not fall back to a different model.
- Missing song: add its metadata via CSV and its numbered PDF to `song-bank/`.
- Missing PDF: add the corresponding `NNN.pdf` to `song-bank/`.
- Review disagreement: check spelling, arrangement, and metadata, then regenerate.
- PDF build failed: ensure every selected PDF opens and is not encrypted.
- TOC links: open the new PDF in a viewer supporting link annotations.

### Project files

- `app.py`: Streamlit interface and PDF assembly.
- `song_agents.py`: selection, independent review, and comparison logic.
- `config.py`: project paths, model/reasoning settings, and credential loading.
- `.env`: private API key; `.env.example`: blank configuration template.
- `song-bank/`: numbered chart PDFs.
- `song_data.json`: saved metadata; built-in defaults apply until saved.
- `requirements.txt`: dependencies.

Run the offline automated checks:

```powershell
python -m unittest discover -s tests -v
```

Model and reasoning options follow the
[OpenAI GPT-6.1 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
