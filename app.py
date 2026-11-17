import streamlit as st
from bill_reader import extract_text_from_file
from extractor import extract_bill_fields
from excel_generator import build_excel
from utils import safe_filename

st.set_page_config(page_title="BillScan", page_icon="🧾", layout="centered")

st.title("🧾 BillScan")
st.caption("Automated Bill-to-Excel Generator")

st.write("Upload a ZIP containing PDF, JPG, JPEG or PNG bills. BillScan will extract the details and generate an Excel file.")

uploaded_zip = st.file_uploader("Upload ZIP file", type=["zip"])

if uploaded_zip:
    if st.button("Generate Excel", type="primary", use_container_width=True):
        import zipfile, io
        from pathlib import PurePosixPath

        rows = []
        errors = []
        allowed = {".pdf", ".jpg", ".jpeg", ".png"}

        with st.spinner("Reading bills and extracting details..."):
            try:
                with zipfile.ZipFile(io.BytesIO(uploaded_zip.getvalue())) as archive:
                    candidates = [
                        name for name in archive.namelist()
                        if not name.endswith("/")
                        and PurePosixPath(name).suffix.lower() in allowed
                        and not PurePosixPath(name).name.startswith(".")
                    ]
                    if not candidates:
                        st.error("No supported bills found. Please upload a ZIP containing PDF, JPG or PNG files.")
                        st.stop()

                    progress = st.progress(0)
                    status = st.empty()
                    for index, name in enumerate(candidates, start=1):
                        status.write(f"Processing {PurePosixPath(name).name} ({index}/{len(candidates)})")
                        try:
                            content = archive.read(name)
                            text = extract_text_from_file(PurePosixPath(name).suffix.lower(), content)
                            if not text.strip():
                                raise ValueError("No readable text found. The bill may be blank, blurry or unsupported.")
                            rows.append(extract_bill_fields(text))
                        except Exception as exc:
                            errors.append(f"{PurePosixPath(name).name}: {exc}")
                        progress.progress(index / len(candidates))

                if rows:
                    excel_bytes = build_excel(rows)
                    st.success(f"Excel generated. Successfully processed {len(rows)} of {len(candidates)} bills.")
                    st.download_button(
                        "⬇️ Download Excel",
                        data=excel_bytes,
                        file_name=safe_filename(uploaded_zip.name.rsplit(".", 1)[0]) + "_expenses.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                if errors:
                    st.warning(f"{len(errors)} bill(s) could not be read and were not included in the Excel file.")
                    with st.expander("See processing issues"):
                        for error in errors:
                            st.write("• " + error)
            except zipfile.BadZipFile:
                st.error("This ZIP file is invalid or damaged. Please upload a valid ZIP.")
