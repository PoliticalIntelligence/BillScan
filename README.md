# BillScan

A simple public bill-to-Excel application.

**Workflow:** Upload ZIP → Generate Excel → Download Excel

## Supported files
- PDF (text-based or scanned)
- JPG / JPEG
- PNG

## Excel columns
- Bill No.
- Date
- Nature of Expense
- Paid To
- Amount

Expense categories are based on the supplied tracker categories.

## Run locally

Install Python 3.10 or newer. Install Tesseract OCR and ensure the `tesseract` command is available on PATH.

```bash
git clone https://github.com/YOUR-USERNAME/BillScan.git
cd BillScan
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free on Streamlit Community Cloud

1. Create a public GitHub repository named `BillScan`.
2. Upload all project files to the repository root.
3. Open https://share.streamlit.io/
4. Sign in with GitHub and choose the repository.
5. Set the main file path to `app.py`.
6. Deploy. Streamlit Community Cloud installs system packages listed in `packages.txt`.

## Important notes

- This project uses local OCR (Tesseract); no paid AI API is required.
- Bill extraction uses heuristic text parsing. Invoice layouts vary, so dates, invoice numbers, vendors and totals should be checked for accuracy before using the Excel output.
- The app processes ZIP contents in memory and does not intentionally save uploaded bills to permanent storage.
- Free hosting has resource, upload-size and availability limits. Large ZIP files may fail.
- Do not upload confidential financial documents unless you are comfortable with the hosting provider's processing and data handling.
- This is a starter implementation. Test it with representative bills before public use.
