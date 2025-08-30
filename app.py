import os
import re
import json
import csv
from io import BytesIO, StringIO
from datetime import datetime

import streamlit as st
from openai import OpenAI
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
        "040": {"title": "Besame Mucho", "type": "single"},
        "041": {"title": "Always on My Mind", "type": "single"},
        "042": {"title": "Two of Us", "type": "single"}
    }

def load_song_data():
    """Load song data from file or return defaults."""
    song_data_file = "song_data.json"
    if os.path.exists(song_data_file):
        try:
            with open(song_data_file, "r") as f:
                return json.load(f)
        except:
            pass
    return get_default_song_data()

def save_song_data(song_data):
    """Save song data to file."""
    with open("song_data.json", "w") as f:
        json.dump(song_data, f, indent=2)

def process_csv_upload(uploaded_file):
    """Process uploaded CSV and return song data dictionary."""
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    csv_reader = csv.DictReader(stringio)
    
    song_data = {}
    for row in csv_reader:
        index = row.get("index", "").strip()
        title = row.get("title", "").strip()
        song_type = row.get("type", "single").strip()
        
        if index and title:
            song_data[index] = {"title": title, "type": song_type}
    
    return song_data

def build_system_prompt(song_data):
    """Build system prompt with current song data."""
    song_bank_json = json.dumps({"song_bank": song_data}, indent=4)
    
    return (
        "You are an AI set list assistant.\n"
        "You will be given a set list of songs to review. For each song in the set list,"
        " respond with a simple, comma-separated list of index numbers (e.g., 004, 008, 025, …)"
        " that correspond to each song's entry in the song_bank JSON object provided below.\n\n"
        "Instructions:\n\n"
        "• The order of the returned index numbers should match the order in which the songs are provided in the set list.\n"
        "• Some set list entries may be medleys (multiple songs combined, such as 'I Think We're Alone Now/Pretty Woman/MissQueen').\n"
        "  – If the song_bank contains that exact medley as a single entry, return that single index.\n"
        "  – Otherwise, return the indices of each individual song in order.\n"
        "• Handle spelling or abbreviation differences intelligently.\n\n"
        "Return **only** the ordered, comma-separated index numbers. Do **not** include explanation or extra text.\n\n"
        f"{song_bank_json}"
    )

def extract_indices(response_text: str):
    """Return a list of 3‑digit index strings (001‑999) from the model response."""
    return re.findall(r"\b\d{3}\b", response_text)


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
    """Generate a table‑of‑contents page and return it as BytesIO."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 72, "Table of Contents")

    c.setFont("Helvetica", 12)
    y = height - 110
    line_height = 18
    for entry in toc_entries:
        title = entry["title"]
        page_num = entry["page"]
        dest = entry["dest"]

        c.drawString(72, y, title)
        page_str = str(page_num)
        c.drawRightString(width - 72, y, page_str)

        # Note: Do not create ReportLab links here. Destinations are added later
        # when pages are merged with PyPDF2, so ReportLab cannot resolve them now.
        # Leaving the TOC text-only avoids "undefined destination" errors.

        y -= line_height

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def build_setlist_pdf(indices, gig_name: str, gig_date: datetime, song_bank_dir: str, song_data):
    """Create the final merged PDF with title, TOC, and charts."""
    writer = PdfWriter()

    # Precompute TOC entries and load song PDFs
    toc_entries = []
    song_pdfs = []
    current_page = 3  # title page (1) + TOC (2) -> songs start at page 3

    for idx in indices:
        song_path = os.path.join(song_bank_dir, f"{idx}.pdf")
        if not os.path.exists(song_path):
            st.warning(f"⚠️  {idx}.pdf not found in '{song_bank_dir}'. Skipping …")
            continue

        reader = PdfReader(song_path)
        song_pdfs.append((idx, reader))

        title = song_data.get(idx, {}).get("title", idx)
        toc_entries.append({"title": title, "page": current_page, "dest": f"song_{idx}"})
        current_page += len(reader.pages)

    # Title and TOC pages
    title_buffer = create_title_page(gig_name, gig_date)
    title_reader = PdfReader(title_buffer)

    toc_buffer = create_table_of_contents(toc_entries)
    toc_reader = PdfReader(toc_buffer)

    writer.add_page(title_reader.pages[0])
    writer.add_page(toc_reader.pages[0])

    # Append songs and destinations
    for idx, reader in song_pdfs:
        start_page = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)

        dest_name = f"song_{idx}"
        writer.add_named_destination(dest_name, page_number=start_page)
        title = song_data.get(idx, {}).get("title", idx)
        writer.add_outline_item(title, page_number=start_page)

    # Add clickable links on the TOC page
    if toc_entries:
        try:
            toc_page_index = 1  # 0-based: 0=title, 1=TOC
            toc_page = writer.pages[toc_page_index]
            page_width = float(toc_page.mediabox.width)
            page_height = float(toc_page.mediabox.height)

            y = page_height - 110
            line_height = 18

            # Ensure the Annots array exists
            if "/Annots" not in toc_page:
                toc_page[NameObject("/Annots")] = ArrayObject()

            for i, entry in enumerate(toc_entries):
                target_page = entry["page"] - 1  # Convert to 0-based page index

                # Clickable area spans from left margin to right margin on the line
                x1 = 72.0
                x2 = page_width - 72.0
                y1 = y - 2.0
                y2 = y + 10.0

                # Create a link annotation with page destination
                # Get the target page height to position at top
                target_page_obj = writer.pages[target_page]
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
                        writer.pages[target_page].indirect_reference,
                        NameObject("/XYZ"),
                        NumberObject(0),  # X position (0 = left edge)
                        NumberObject(target_height),  # Y position (page height = top)
                        NumberObject(0)   # Zoom (0 = keep current zoom)
                    ])
                })

                # Add the link as an indirect object
                writer._add_object(link)
                toc_page["/Annots"].append(link.indirect_reference)
                
                y -= line_height
        except Exception as e:
            # If link annotation fails for any reason, continue with a text-only TOC
            st.warning(f"Could not add TOC links: {str(e)}")
            pass

    # Output to in‑memory buffer
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Set‑List PDF Builder", layout="centered")
st.title("🎵 Set‑List PDF Builder")

# Load current song data
current_song_data = load_song_data()

# Sidebar configuration inputs
with st.sidebar:
    st.header("🔑 Configuration")
    api_key = st.text_input("OpenAI API Key", type="password")
    gig_name = st.text_input("Gig Name", placeholder="e.g. The Midnight Showcase")
    gig_date = st.date_input("Gig Date", format="MM/DD/YYYY")
    song_bank_dir = "song-bank"  # relative path
    st.markdown(
        f"Song charts must reside in `./{song_bank_dir}/` named **001.pdf – 999.pdf**.")
    
    st.header("🎵 Song Data Management")
    
    # CSV upload for song data
    uploaded_file = st.file_uploader(
        "Upload CSV to update song data",
        type=['csv'],
        help="CSV should have columns: index, title, type"
    )
    
    if uploaded_file is not None:
        try:
            new_song_data = process_csv_upload(uploaded_file)
            if new_song_data:
                st.success(f"Loaded {len(new_song_data)} songs from CSV")
                if st.button("💾 Save Song Data"):
                    save_song_data(new_song_data)
                    current_song_data = new_song_data
                    st.success("Song data saved successfully!")
                    st.rerun()
            else:
                st.error("No valid song data found in CSV")
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")
    
    # Display current song count
    st.info(f"Current song bank: {len(current_song_data)} songs")
    
    # Reset to defaults option
    if st.button("🔄 Reset to Default Songs"):
        save_song_data(get_default_song_data())
        st.success("Reset to default song data!")
        st.rerun()

st.subheader("Paste or Upload Your Set List")

setlist_text = st.text_area(
    "Enter the set list (one song or medley per line):",
    height=200,
)

# Submit button
if st.button("Generate PDF"):
    # --- Validation ----------------------------------------------------------------
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        st.stop()

    if not gig_name or not gig_date:
        st.error("Please provide both the gig name and gig date in the sidebar.")
        st.stop()

    if not setlist_text.strip():
        st.error("Please paste or upload your set list first.")
        st.stop()

    # --- Call OpenAI ----------------------------------------------------------------
    st.info("Contacting OpenAI …")
    client = OpenAI(api_key=api_key)

    SYSTEM_PROMPT = build_system_prompt(current_song_data)

    completion = client.chat.completions.create(
        model="gpt-4.1",  # or whichever model is preferred
        temperature=0.45,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": setlist_text},
        ],
    )

    model_reply = completion.choices[0].message.content.strip()
    st.write("**Model output:**", model_reply)

    indices = extract_indices(model_reply)
    if not indices:
        st.error("No valid indices found in the model response.")
        st.stop()

    # --- Build & deliver PDF --------------------------------------------------------
    st.info("Building merged PDF …")
    pdf_bytes = build_setlist_pdf(indices, gig_name, gig_date, song_bank_dir, current_song_data)

    filename = f"{gig_name.replace(' ', '_')}_{gig_date.isoformat()}.pdf"
    st.success("Done! Click below to download your set list.")
    st.download_button(
        label="📥 Download Set List PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )