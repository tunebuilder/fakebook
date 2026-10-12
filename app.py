import os
import re
import json
import csv
from io import BytesIO, StringIO
from datetime import datetime

import streamlit as st
from openai import OpenAI
from openai import APIError, AuthenticationError, BadRequestError, RateLimitError
from config import PROJECT_DIR, MODEL, REASONING_LEVELS, DEFAULT_REASONING, get_api_key
from song_agents import select_songs, review_selection, check_chart_files
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, DictionaryObject, NumberObject, FloatObject, ArrayObject
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_default_song_data():
    """Return the default song bank data."""
    return {
        "001": {"title": "Ain't too Proud to Beg/My Girl", "type": "medley"},
        "002": {"title": "Alive", "type": "single"},
        "003": {"title": "Are you Gonna Be My Girl", "type": "single"},
        "004": {"title": "Back in the USSR", "type": "single"},
        "005": {"title": "Besame Mucho", "type": "single"},
        "006": {"title": "Brown Eyed Girl/Rockin Robin", "type": "medley"},
        "007": {"title": "Comfortably Numb", "type": "single"},
        "008": {"title": "Faith", "type": "single"},
        "009": {"title": "Fun, Fun, Fun", "type": "single"},
        "010": {"title": "Fat Bottomed Girls", "type": "single"},
        "011": {"title": "Gimme some Lovin", "type": "single"},
        "012": {"title": "Gimme Three Steps", "type": "single"},
        "013": {"title": "Hungry Like the Wolf", "type": "single"},
        "014": {"title": "I Think We're Alone Now", "type": "single"},
        "015": {"title": "I Want to Be Sedated", "type": "single"},
        "016": {"title": "I'm a Believer", "type": "single"},
        "017": {"title": "In the End", "type": "single"},
        "018": {"title": "Keep Your Hands to Yourself", "type": "single"},
        "019": {"title": "Kryptonite", "type": "single"},
        "020": {"title": "Lean on Me", "type": "single"},
        "021": {"title": "Let it Be", "type": "single"},
        "022": {"title": "Mississippi Queen", "type": "single"},
        "023": {"title": "Pink Houses", "type": "single"},
        "024": {"title": "Play That Funky Music", "type": "single"},
        "025": {"title": "Plush", "type": "single"},
        "026": {"title": "Pour Some Sugar on Me", "type": "single"},
        "027": {"title": "Pretty Woman", "type": "single"},
        "028": {"title": "Runaround Sue", "type": "single"},
        "029": {"title": "Santeria", "type": "single"},
        "030": {"title": "Smooth Criminal", "type": "single"},
        "031": {"title": "Summer of '69", "type": "single"},
        "032": {"title": "The Middle", "type": "single"},
        "033": {"title": "Three Little Birds", "type": "single"},
        "034": {"title": "Wagon Wheel", "type": "single"},
        "035": {"title": "What I Like About You", "type": "single"},
        "036": {"title": "Yellow Ledbetter", "type": "single"},
        "037": {"title": "It Don't Matter to Me", "type": "single"},
        "038": {"title": "Ticket to Ride", "type": "single"},
        "039": {"title": "For Lovin' Me", "type": "single"},
        "041": {"title": "Always on My Mind", "type": "single"},
        "042": {"title": "Two of Us", "type": "single"},
        "043": {"title": "Don't Dream It's Over", "type": "single"},
        "044": {"title": "Bad Moon Rising", "type": "single"},
        "045": {"title": "Me and Julio Down By The School Yard", "type": "single"},
        "046": {"title": "Better Together", "type": "single"},
        "048": {"title": "Down Under", "type": "single"},
        "049": {"title": "I Can See Clearly Now", "type": "single"},
        "050": {"title": "The World I Know", "type": "single"},
        "051": {"title": "Mrs. Robinson", "type": "single"},
        "052": {"title": "Fast Car", "type": "single"},
        "053": {"title": "Stick Season", "type": "single"},
        "054": {"title": "Free Fallin'", "type": "single"},
        "055": {"title": "What's Up", "type": "single"},
        "057": {"title": "You May Be Right", "type": "single"},
        "058": {"title": "Fight For Your Right To Party", "type": "single"},
        "059": {"title": "Saturday Night's Alright for Fighting", "type": "single"},
        "060": {"title": "Every Rose Has Its Thorn ", "type": "single"},
        "061": {"title": "The Lion Sleeps Tonight", "type": "single"},
        "062": {"title": "Shipping up to Boston", "type": "single"},
        "063": {"title": "Magic Carpet Ride", "type": "single"},
        "064": {"title": "Fortunate Son", "type": "single"},
        "065": {"title": "Melt with You", "type": "single"},
        "066": {"title": "Bad Decisions", "type": "single"},
        "067": {"title": "Last Nite", "type": "single"},
        "068": {"title": "Birthday", "type": "single"},
        "069": {"title": "One Week", "type": "single"},
        "070": {"title": "With or Without You", "type": "single"},
        "071": {"title": "Just Like Heaven", "type": "single"},
        "072": {"title": "Take it Easy", "type": "single"},
        "073": {"title": "Save a Horse Ride a Cowboy", "type": "single"},
        "074": {"title": "All Right Now", "type": "single"},
        "075": {"title": "I Saw Her Standing There", "type": "single"},
        "076": {"title": "Mr Jones", "type": "single"},
        "077": {"title": "Help", "type": "single"},
        "078": {"title": "Black", "type": "single"},
        "079": {"title": "Riptide", "type": "single"},
        "080": {"title": "Honky Tonk Women", "type": "single"},
        "081": {"title": "ROCK in the USA", "type": "single"},
        "082": {"title": "Ho Hey", "type": "single"},
        "083": {"title": "Boys of Summer", "type": "single"},
        "084": {"title": "Hard to Handle", "type": "single"},
        "085": {"title": "Born to Be Wild", "type": "single"},
        "086": {"title": "If We Stick Together", "type": "single"},
        "087": {"title": "Into the Mystic", "type": "single"},
        "088": {"title": "Sitting, Waiting, Wishing", "type": "single"},
        "089": {"title": "The Thrill is Gone", "type": "single"},
        "090": {"title": "Back on the Chain Gang", "type": "single"},
        "091": {"title": "For What It's Worth", "type": "single"},
        "092": {"title": "And It Stoned Me", "type": "single"},
        "093": {"title": "Wild Night", "type": "single"},
        "094": {"title": "Brandy (Your a fine Girl)", "type": "single"},
        "095": {"title": "American Girl", "type": "single"},
        "096": {"title": "Let Her Cry", "type": "single"},
        "098": {"title": "Can't Find My Way Home", "type": "single"},
        "099": {"title": "Stop Draggin My Heart Around", "type": "single"},
        "100": {"title": "You Wreck Me", "type": "single"},
        "101": {"title": "Mary Jane's Last Dance", "type": "single"},
        "102": {"title": "You Don’t Know How It Feels", "type": "single"},
        "103": {"title": "Bertha", "type": "single"},
        "104": {"title": "Say You Love Me", "type": "single"},
        "105": {"title": "Soulshine", "type": "single"},
        "106": {"title": "Southern Cross", "type": "single"},
        "107": {"title": "Stray Cat Strut", "type": "single"},
        "108": {"title": "Brown Eyed Woman", "type": "single"},
        "109": {"title": "Heart of Gold", "type": "single"},
        "110": {"title": "Breakfast at Tiffany's", "type": "single"},
        "111": {"title": "Superstition", "type": "single"},
        "112": {"title": "Take Me To The River", "type": "single"},
        "113": {"title": "Mustang Sally", "type": "single"},
        "114": {"title": "Closing Time", "type": "single"},
        "115": {"title": "Billie Jean", "type": "single"},
        "116": {"title": "It's Hard", "type": "single"},
        "117": {"title": "Reset Button", "type": "single"},
        "118": {"title": "Smile", "type": "single"},
        "119": {"title": "Piece of Your Mind", "type": "single"},
        "120": {"title": "The Sycamore Tree", "type": "single"},
        "121": {"title": "Country Roads", "type": "single"},
        "122": {"title": "Last Kiss", "type": "single"},
        "123": {"title": "Imagine", "type": "single"},
        "124": {"title": "Can't You See", "type": "single"},
        "125": {"title": "Creep", "type": "single"},
        "126": {"title": "Leaving on a Jet Plane", "type": "single"},
        "127": {"title": "Boys of Summer (LOV)", "type": "single"}
    }

def load_song_data():
    """Load song data from file or return defaults."""
    song_data_file = PROJECT_DIR / "song_data.json"
    if os.path.exists(song_data_file):
        try:
            with open(song_data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return get_default_song_data()

def save_song_data(song_data):
    """Save song data to file."""
    with open(PROJECT_DIR / "song_data.json", "w", encoding="utf-8") as f:
        json.dump(song_data, f, indent=2)

def process_csv_upload(uploaded_file):
    """Process uploaded CSV and return song data dictionary."""
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    csv_reader = csv.DictReader(stringio)

    song_data = {}
    for row in csv_reader:
        index = row.get("index", "").strip().zfill(3)
        title = row.get("title", "").strip()
        song_type = row.get("type", "single").strip()

        if re.fullmatch(r"[0-9]{3}", index) and index != "000" and title:
            song_data[index] = {"title": title, "type": song_type}

    return song_data

def create_title_page(gig_name: str, gig_date: datetime):
    """Generate a one‑page PDF with the gig name & date and return it as BytesIO."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Centre‑aligned title
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height / 2 + 40, gig_name)

    # Centre‑aligned date underneath
    c.setFont("Helvetica", 18)
    c.drawCentredString(
        width / 2,
        height / 2,
        gig_date.strftime("%B %d, %Y"),
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def create_table_of_contents(toc_entries):
    """
    Generate a table‑of‑contents page (multipage if needed) and return (BytesIO, entry_positions).
    entry_positions is a list of dicts: {'page_index': int, 'y': float} relative to the TOC PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Layout constants
    PAGE_1_START_Y = height - 110
    SUBSEQUENT_START_Y = height - 72
    BOTTOM_MARGIN = 50
    LINE_HEIGHT = 18

    entry_positions = []

    # --- First Page Setup ---
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 72, "Table of Contents")

    c.setFont("Helvetica", 12)
    y = PAGE_1_START_Y
    page_index = 0

    for entry in toc_entries:
        # Check if we need a new page
        if y < BOTTOM_MARGIN:
            c.showPage()
            page_index += 1
            y = SUBSEQUENT_START_Y
            c.setFont("Helvetica", 12)  # Reset font for new page

        title = entry["title"]
        page_num = entry["page"]

        # Draw the entry
        c.drawString(72, y, title)
        page_str = str(page_num)
        c.drawRightString(width - 72, y, page_str)

        # Record position for linking later
        entry_positions.append({"page_index": page_index, "y": y})

        y -= LINE_HEIGHT

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer, entry_positions

def calculate_toc_pages(num_entries):
    """
    Calculate how many pages the TOC will take based on the layout logic
    in create_table_of_contents.
    """
    width, height = letter
    PAGE_1_START_Y = height - 110
    SUBSEQUENT_START_Y = height - 72
    BOTTOM_MARGIN = 50
    LINE_HEIGHT = 18

    if num_entries == 0:
        return 1

    pages = 1
    y = PAGE_1_START_Y

    # Simulate the loop
    for _ in range(num_entries):
        if y < BOTTOM_MARGIN:
            pages += 1
            y = SUBSEQUENT_START_Y
        y -= LINE_HEIGHT

    return pages


def build_setlist_pdf(indices, gig_name: str, gig_date: datetime, song_bank_dir: str, song_data):
    """Create the final merged PDF with title, TOC, and charts."""
    writer = PdfWriter()

    # 1. Calculate Song Page Numbers
    # We need to look ahead to see how many pages the TOC will occupy
    # so we can number the songs correctly.

    valid_indices = [idx for idx in indices if os.path.exists(os.path.join(song_bank_dir, f"{idx}.pdf"))]

    # Calculate TOC pages
    toc_page_count = calculate_toc_pages(len(valid_indices))

    # Start page for songs: Title Pge (1) + TOC Pages + 1
    start_song_page_num = 1 + toc_page_count + 1
    current_page_num = start_song_page_num

    toc_entries = []
    song_pdfs = []

    # 2. Prepare Song Data & TOC Entries
    for idx in indices:
        song_path = os.path.join(song_bank_dir, f"{idx}.pdf")
        if not os.path.exists(song_path):
            st.warning(f"⚠️  {idx}.pdf not found in '{song_bank_dir}'. Skipping …")
            continue

        reader = PdfReader(song_path)
        song_pdfs.append((idx, reader))

        title = song_data.get(idx, {}).get("title", idx)
        toc_entries.append({"title": title, "page": current_page_num, "dest": f"song_{idx}"})
        current_page_num += len(reader.pages)

    # 3. Generate Title & TOC PDFs
    title_buffer = create_title_page(gig_name, gig_date)
    title_reader = PdfReader(title_buffer)

    toc_buffer, toc_positions = create_table_of_contents(toc_entries)
    toc_reader = PdfReader(toc_buffer)

    # 4. Assemble the PDF

    # Add Title Page
    writer.add_page(title_reader.pages[0])

    # Add TOC Pages
    for page in toc_reader.pages:
        writer.add_page(page)

    # Add Songs
    for idx, reader in song_pdfs:
        start_page_index = len(writer.pages) # 0-based index in the final PDF
        for page in reader.pages:
            writer.add_page(page)

        dest_name = f"song_{idx}"
        writer.add_named_destination(dest_name, page_number=start_page_index)
        title = song_data.get(idx, {}).get("title", idx)
        writer.add_outline_item(title, page_number=start_page_index)

    # 5. Add Links to TOC
    # We need to map each entry to the correct TOC page and Y coordinate.
    # Title is page 0. TOC starts at page 1.

    if toc_entries and toc_positions:
        line_height = 18

        # Iterate over entries and their corresponding positions
        for i, entry in enumerate(toc_entries):
            pos = toc_positions[i]

            # Which page of the PDF contains this TOC entry?
            # 0 (Title) + 1 (Start of TOC) + pos['page_index']
            target_toc_page_index = 1 + pos['page_index']

            try:
                toc_page = writer.pages[target_toc_page_index]
                page_width = float(toc_page.mediabox.width)

                y = pos['y']

                # Clickable area
                x1 = 72.0
                x2 = page_width - 72.0
                y1 = y - 2.0
                y2 = y + 10.0

                # Calculate destination page index (0-based)
                dest_page_num_display = entry["page"]
                dest_page_index = dest_page_num_display - 1

                # Setup Link Annotation
                if "/Annots" not in toc_page:
                    toc_page[NameObject("/Annots")] = ArrayObject()

                target_page_obj = writer.pages[dest_page_index]
                target_height = float(target_page_obj.mediabox.height)

                link = DictionaryObject()
                link.update({
                    NameObject("/Type"): NameObject("/Annot"),
                    NameObject("/Subtype"): NameObject("/Link"),
                    NameObject("/Rect"): ArrayObject([
                        FloatObject(x1), FloatObject(y1), FloatObject(x2), FloatObject(y2)
                    ]),
                    NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
                    NameObject("/Dest"): ArrayObject([
                        writer.pages[dest_page_index].indirect_reference,
                        NameObject("/XYZ"),
                        NumberObject(0),
                        NumberObject(target_height),
                        NumberObject(0)
                    ])
                })

                writer._add_object(link)
                toc_page["/Annots"].append(link.indirect_reference)

            except Exception as e:
                # Fallback purely for robustness
                print(f"Error adding link for {entry['title']}: {e}")
                continue

    # Output to in‑memory buffer
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_result(result):
    st.subheader("Song selection review")
    review = result.get("review")
    file_checks = result["file_checks"]
    issues = bool(result.get("review_error") or file_checks["missing_files"]
                  or file_checks["unknown_indices"] or result.get("pdf_error"))
    if review:
        issues = issues or not review["matches"] or bool(
            review["missing_songs"] or review["uncertainties"]
        )
        if not issues and result.get("pdf"):
            st.success(f"Verified {review['song_lines']} set-list entries. "
                       f"All {len(result['indices'])} selected charts match and are available.")
        else:
            st.warning(f"Reviewed {review['song_lines']} set-list entries. See the issues below.")
        for label, field in (("Missing from song bank", "missing_songs"),
                             ("Available songs omitted from the pull", "omitted"),
                             ("Unexpected selections", "unexpected"),
                             ("Needs your review", "uncertainties")):
            if review[field]:
                st.markdown(f"**{label}**")
                for item in review[field]:
                    st.write("• " + item)
        if review["order_issue"]:
            st.warning("All chart counts match, but the selected order differs from the set list.")
        with st.expander("Review details"):
            st.table([{
                "Line": entry["line_number"], "Requested": entry["requested"],
                "Expected charts": ", ".join(entry["expected_indices"]) or "—",
                "Notes": "; ".join(entry["missing_songs"] + entry["uncertainties"])
                         or ("Heading" if entry["is_heading"] else "Matched"),
            } for entry in review["entries"]])
    if result.get("review_error"):
        st.error("Verification unavailable: " + result["review_error"])
    if file_checks["unknown_indices"]:
        st.warning("Unknown chart indices excluded: " + ", ".join(file_checks["unknown_indices"]))
    if file_checks["missing_files"]:
        st.markdown("**Missing chart PDFs**")
        for item in file_checks["missing_files"]:
            st.write("• " + item)
    st.caption("Selected charts: " + (", ".join(result["indices"]) or "None"))
    if result.get("pdf_error"):
        st.error(result["pdf_error"])
    if result.get("pdf"):
        if issues:
            st.warning("The PDF contains the available charts from the initial pull. "
                       "Review the issues above before using it.")
        st.download_button(
            label="📥 Download Set List PDF" if not issues else "📥 Download PDF with review issues",
            data=result["pdf"], file_name=result["filename"], mime="application/pdf",
        )
    elif not result.get("pdf_error"):
        st.info("No selected charts are available to build a PDF. Update the song bank or set list.")
    st.caption("Verification checks song-bank metadata and chart file availability. "
               "Ambiguous matches still need your review.")


def agent_error_message(error):
    if isinstance(error, AuthenticationError):
        return "OpenAI rejected the API key. Update OPENAI_API_KEY in the project's .env file."
    if isinstance(error, RateLimitError):
        return "OpenAI usage or rate limits were reached. Check your API account or try again later."
    if isinstance(error, BadRequestError):
        return (f"OpenAI could not accept the request. Check API access to {MODEL} "
                "and the selected reasoning level, or shorten the set list.")
    if isinstance(error, APIError):
        return "OpenAI could not finish the request. Check your connection and try again."
    if isinstance(error, ValueError):
        return "The agent returned an incomplete or invalid result. Please try again."
    return "The agent could not finish. Please try again."


def main():
    st.set_page_config(page_title="Set‑List PDF Builder", layout="centered")
    st.title("🎵 Set‑List PDF Builder")
    current_song_data = load_song_data()
    api_key = get_api_key()
    song_bank_dir = PROJECT_DIR / "song-bank"

    with st.sidebar:
        st.header("Configuration")
        st.caption(f"Model: {MODEL}")
        reasoning_effort = st.selectbox(
            "Reasoning level", REASONING_LEVELS,
            index=REASONING_LEVELS.index(DEFAULT_REASONING),
            help="Applies to both the selection and review agents. Higher levels may take longer.",
        )
        st.caption("API key loaded from local configuration." if api_key else
                   "Add OPENAI_API_KEY to .env beside app.py.")
        gig_name = st.text_input("Gig Name", placeholder="e.g. The Midnight Showcase")
        gig_date = st.date_input("Gig Date", format="MM/DD/YYYY")
        st.markdown("Song charts must reside in `./song-bank/` named **001.pdf – 999.pdf**.")
        st.header("🎵 Song Data Management")
        uploaded_file = st.file_uploader(
            "Upload CSV to update song data", type=['csv'],
            help="CSV should have columns: index, title, type",
        )
        if uploaded_file is not None:
            try:
                new_song_data = process_csv_upload(uploaded_file)
                if new_song_data:
                    st.success(f"Loaded {len(new_song_data)} songs from CSV")
                    if st.button("💾 Save Song Data"):
                        save_song_data(new_song_data)
                        st.success("Song data saved successfully!")
                        st.rerun()
                else:
                    st.error("No valid song data found in CSV")
            except Exception:
                st.error("Could not read the CSV. Check its index, title, and type columns.")
        st.info(f"Current song bank: {len(current_song_data)} songs")
        if st.button("🔄 Reset to Default Songs"):
            save_song_data(get_default_song_data())
            st.success("Reset to default song data!")
            st.rerun()

    st.subheader("Paste Your Set List")
    setlist_text = st.text_area("Enter the set list (one song or medley per line):", height=200)
    input_snapshot = (setlist_text, gig_name, gig_date.isoformat(), reasoning_effort,
                      json.dumps(current_song_data, sort_keys=True))
    if st.button("Generate PDF"):
        st.session_state.pop("setlist_result", None)
        if not api_key:
            st.error("Add your OpenAI API key to OPENAI_API_KEY in .env beside app.py, then try again.")
            st.stop()
        if not gig_name.strip() or not gig_date:
            st.error("Please provide both the gig name and gig date in the sidebar.")
            st.stop()
        if not setlist_text.strip():
            st.error("Please paste your set list first.")
            st.stop()
        try:
            with OpenAI(api_key=api_key) as client:
                with st.spinner("Selecting songs from the song bank …"):
                    indices = select_songs(client, setlist_text, current_song_data, reasoning_effort)
                result = {
                    "indices": indices, "snapshot": input_snapshot,
                    "file_checks": check_chart_files(indices, song_bank_dir, current_song_data),
                    "filename": f"{gig_name.strip().replace(' ', '_')}_{gig_date.isoformat()}.pdf",
                }
                try:
                    with st.spinner("Review agent: checking every song and medley …"):
                        result["review"] = review_selection(
                            client, setlist_text, indices, current_song_data, reasoning_effort,
                        )
                    # Also report missing PDFs for charts the first agent omitted.
                    result["file_checks"] = check_chart_files(
                        indices + result["review"]["expected_indices"], song_bank_dir, current_song_data,
                    )
                except (APIError, ValueError) as error:
                    result["review_error"] = agent_error_message(error)
        except (APIError, ValueError) as error:
            st.error(agent_error_message(error))
            st.stop()

        available_indices = [index for index in indices if index in current_song_data
                             and (song_bank_dir / f"{index}.pdf").is_file()]
        if available_indices:
            try:
                with st.spinner("Building merged PDF …"):
                    result["pdf"] = build_setlist_pdf(
                        available_indices, gig_name.strip(), gig_date,
                        song_bank_dir, current_song_data,
                    ).getvalue()
            except Exception:
                result["pdf_error"] = ("Could not build the PDF. Check that each selected chart "
                                       "opens correctly and is not encrypted.")
        st.session_state["setlist_result"] = result

    result = st.session_state.get("setlist_result")
    if result:
        if result["snapshot"] != input_snapshot:
            st.info("Showing the previous result. Click Generate PDF to apply your current changes.")
        render_result(result)


if __name__ == "__main__":
    main()
