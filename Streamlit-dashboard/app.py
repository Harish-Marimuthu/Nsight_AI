import streamlit as st
import fitz  # PyMuPDF
from azure.storage.blob import BlobServiceClient
from io import BytesIO
import os
from dotenv import load_dotenv
import re
import datetime
import pandas as pd
import altair as alt




def check_documents_v2(fields):
    matches = [field for field in fields if isinstance(field, str) and "purchase" in field.lower()]
    if matches:
        return "PurchaseOrder"

    matches = [field for field in fields if isinstance(field, str) and "sales" in field.lower()]
    if matches:
        return "SalesOrder"

    matches = [field for field in fields if isinstance(field, str) and "bill" in field.lower()]
    if matches:
        return "Bills"

    matches = [field for field in fields if isinstance(field, str) and "invoice" in field.lower()]
    if matches:
        return "Invoice"

    return "Others"



load_dotenv()

# Azure setup
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_ACCOUNT_KEY = os.getenv("STORAGE_ACCOUNT_KEY")
container_name = os.getenv("CONTAINER_NAME")
container_path = os.getenv("CONTAINER_PATH")

connect_str = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT_NAME};AccountKey={STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_client = blob_service_client.get_container_client(container_name)



# Page controller
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# App title
st.markdown("<h1 style='text-align: center;'> Document Processing web</h1>", unsafe_allow_html=True)

# Centered button layout
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("Dashboard", use_container_width=True):
        st.session_state.page = "Dashboard"
    if btn_col2.button("Process Data", use_container_width=True):
        st.session_state.page = "Process Data"

st.markdown("---")


folders = ['PurchaseOrder', 'Invoice', 'SalesOrder', 'Bills']

# -------------------- PAGE HANDLING ----------------------

if st.session_state.page == "Process Data":

    # Streamlit App
    st.title("📑 Invoice Review ")

    # -------- FILTERS --------

    # Filter 1: Folder
    folders = ['PurchaseOrder', 'Invoice', 'SalesOrder', 'Bills']
    selected_folder = st.selectbox("Select Document Folder", folders, index=1)

    # Based on selected folder
    base_folder_path = f"{container_path}/{selected_folder}"
    processed_path = f"{base_folder_path}/processed"

    # Helper function: List all pdfs under a folder
    def list_processed_pdfs(folder_path):
        return [blob.name for blob in container_client.list_blobs(name_starts_with=folder_path) if blob.name.endswith('.pdf')]

    def list_pdfs(folder_path):
        return [blob.name for blob in container_client.list_blobs(name_starts_with=folder_path) if blob.name.endswith('.pdf')]

    # Get all PDFs
    all_pdfs = list_pdfs(base_folder_path)
    processed_pdfs = list_processed_pdfs(processed_path)

    # Extract unique dates from blob names
    def extract_dates(pdfs):
        dates = set()
        pattern = r"(\d{4}-\d{2}-\d{2})"  # Looking for YYYY-MM-DD
        for pdf in pdfs:
            match = re.search(pattern, pdf)
            if match:
                dates.add(match.group(1))
        return sorted(list(dates), reverse=True)

    available_dates = extract_dates(all_pdfs)
    print(available_dates)

    # Filter 2: Date
    if available_dates:
        selected_date = st.selectbox("Select Date", available_dates)
    else:
        selected_date = None

    # Final filtered PDFs
    def filter_pdfs_by_date(pdfs, date):
        if date:
            return [pdf for pdf in pdfs if date in pdf and '/processed/' not in pdf]
        else:
            return []

    pdf_list = filter_pdfs_by_date(all_pdfs, selected_date)

    # Helper functions: get_blob, move_blob, render_pdf
    def get_blob(blob_name):
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def move_blob(blob_name, new_name):
        sanitized_name = re.sub(r"[^\w\-.]", "", new_name)
        source_url = f"{blob_service_client.primary_endpoint}/{container_name}/{blob_name}".replace('//', '/').replace('https:/', 'https://')
        copied_blob = container_client.get_blob_client(f"{processed_path}/{sanitized_name}")
        copied_blob.start_copy_from_url(source_url)
        container_client.delete_blob(blob_name)

    def render_pdf(data, page_num):
        pdf = fitz.open(stream=data, filetype="pdf")
        if page_num >= len(pdf):
            page_num = len(pdf) - 1
        page = pdf.load_page(page_num)
        pix = page.get_pixmap()
        return pix.tobytes("png")

    # --------- UI Rendering ---------

    if "pdf_index" not in st.session_state:
        st.session_state.pdf_index = 0
    if "page_index" not in st.session_state:
        st.session_state.page_index = 0

    if not pdf_list:
        st.warning("No PDFs available for selected Folder and Date.")
    else:
        current_pdf = pdf_list[st.session_state.pdf_index]
        pdf_data = get_blob(current_pdf)

        col1, col2 = st.columns([3, 1])

        # Center - PDF Preview
        with col1:
            st.subheader(f"Preview: {os.path.basename(current_pdf)}")
            img = render_pdf(pdf_data, st.session_state.page_index)
            st.image(img, use_container_width=True)

        # Right - Actions
        with col2:
            st.subheader("Actions")
            new_name = st.text_input("Rename PDF", value=os.path.basename(current_pdf))
            st.write(f"Number of pending PDFs: {len(pdf_list)}")
            st.write(f"Number of processed PDFs: {len(processed_pdfs)}")
            if st.button("✅ Process this PDF"):
                move_blob(current_pdf, new_name)
                st.success("File Moved Successfully")
                st.rerun()

        # Bottom - Navigation
        st.markdown("---")
        nav1, nav2, nav3 = st.columns([1, 3, 1])

        with nav1:
            if st.button("⬅️ Previous PDF"):
                st.session_state.pdf_index = (st.session_state.pdf_index - 1) % len(pdf_list)
                st.session_state.page_index = 0
                st.rerun()
            if st.button("⬅️ Prev Page"):
                st.session_state.page_index = max(0, st.session_state.page_index - 1)
                st.rerun()

        with nav3:
            if st.button("➡️ Next PDF"):
                st.session_state.pdf_index = (st.session_state.pdf_index + 1) % len(pdf_list)
                st.session_state.page_index = 0
                st.rerun()
            if st.button("➡️ Next Page"):
                st.session_state.page_index += 1
                st.rerun()

elif st.session_state.page == "Dashboard":

    # Streamlit App
    st.markdown("## Document Summary")

    # -------------------- SUMMARY CARD ----------------------

    # Dropdown 1 - For summary counts
    summary_type = st.selectbox("Select Document Type for Summary", folders , index=0)

    # Get folder paths
    summary_base = f"{container_path}/{summary_type}"
    summary_proc = f"{summary_base}/processed"

    # Count logic
    summary_pending = len([b for b in container_client.list_blobs(name_starts_with=summary_base) 
                           if b.name.endswith(".pdf") and '/processed/' not in b.name])
    summary_processed = len([b for b in container_client.list_blobs(name_starts_with=summary_proc) 
                             if b.name.endswith(".pdf")])

    # Display counts
    col_summary1, col_summary2 = st.columns(2)
    with col_summary1:
        st.metric(label="Pending Documents", value=summary_pending)
    with col_summary2:
        st.metric(label="Processed Documents", value=summary_processed)

        # -------------------- VISUALIZATION SECTION ----------------------


    
    

# Assuming container_client and container_path are already initialized

    st.markdown("## Document Classification - Last 7 Days")

# Get today's date and last 7 days
today = datetime.date.today()
last_7_dates = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]

# Initialize document counts
doc_counts = {
    date: {"Invoice": 0, "PurchaseOrder": 0, "SalesOrder": 0, "Bills": 0, "Others": 0}
    for date in last_7_dates
}

# Process each blob
for blob in container_client.list_blobs(name_starts_with=container_path):
    if blob.name.endswith('.pdf') and '/processed/' not in blob.name:
        upload_date = blob.last_modified.date()
        if upload_date in doc_counts:
            try:
                # Read blob PDF content
                blob_data = container_client.get_blob_client(blob.name).download_blob(timeout=30).readall()
                pdf_doc = fitz.open(stream=blob_data, filetype="pdf")
                extracted_text = ""
                for page in pdf_doc:
                    extracted_text += page.get_text()
                pdf_doc.close()

                # Classify document type
                words = extracted_text.split()
                doc_type = check_documents_v2(words)
                doc_counts[upload_date][doc_type] += 1

            except Exception as e:
                st.warning(f"Failed to read: {blob.name} — {e}")

# Convert to DataFrame
chart_data = []
for date, types in doc_counts.items():
    for doc_type, count in types.items():
        chart_data.append({
            "Date": date.strftime("%Y-%m-%d"),
            "Document Type": doc_type,
            "Count": count
        })

df_chart = pd.DataFrame(chart_data)

# Dropdown to select document type
doc_type_list = ["Invoice", "PurchaseOrder", "SalesOrder", "Bills", "Others"]
selected_doc_type = st.selectbox("Select Document Type to View", doc_type_list)

# Filter chart data
filtered_df = df_chart[df_chart["Document Type"] == selected_doc_type]

# Bar chart for selected document type
chart = alt.Chart(filtered_df).mark_bar().encode(
    x=alt.X("Date:N", title="Date", axis=alt.Axis(labelAngle=-45)),
    y=alt.Y("Count:Q", title="Document Count"),
    color=alt.value("#1f77b4"),
    tooltip=["Date", "Count"]
).properties(
    width=700,
    height=400,
    title=f"{selected_doc_type} Count Over Last 7 Days"
)

st.altair_chart(chart, use_container_width=True)