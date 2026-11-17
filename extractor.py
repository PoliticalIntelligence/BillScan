import re
from datetime import datetime

CATEGORIES = {
    "Uber": "Ground Transport",
    "Rapido": "Ground Transport",
    "Blinkit": "Food & Snacks",
    "Zomato": "Food & Snacks",
    "Zepto": "Food & Snacks",
    "Swiggy": "Food & Snacks",
}

def _platform(text):
    t = text.lower()
    # Prefer explicit platform markers over incidental mentions.
    if "thanks for riding" in t and ("uber go" in t or "uber" in t):
        return "Uber"
    if re.search(r"\bRD\d{10,}\b", text, re.I) or ("rapido" in t and ("selected price" in t or "ride id" in t)):
        return "Rapido"
    if "zepto" in t or "zepto marketplace" in t:
        return "Zepto"
    if "swiggy limited" in t or "swiggy" in t:
        return "Swiggy"
    if "blink commerce" in t or "blinkit" in t:
        return "Blinkit"
    if "zomato" in t:
        return "Zomato"
    return ""

def _date_value(raw):
    raw = raw.strip().replace(",", "")
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
                "%Y-%m-%d", "%b %d %Y", "%B %d %Y",
                "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return ""

def _find_date(text, platform):
    patterns = [
        r"(?:Date\s+of\s+Invoice|Invoice\s+Date|Date)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b",
        r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            value = _date_value(m.group(1))
            if value:
                return value
    return ""

def _find_bill_no(text, platform):
    # Platform-specific stable identifiers.
    if platform == "Rapido":
        m = re.search(r"\b(RD\d{10,})\b", text, re.I)
        if m:
            return m.group(1).upper()
    if platform == "Swiggy":
        m = re.search(r"\bInvoice\s*No\s*:\s*([A-Z0-9/-]+)", text, re.I)
        if m:
            return m.group(1)
    if platform == "Zepto":
        m = re.search(r"\bInvoice\s*No\.?\s*:\s*([A-Z0-9/-]+)", text, re.I)
        if m:
            return m.group(1)
    if platform in {"Blinkit", "Zomato"}:
        m = re.search(r"\bInvoice\s*(?:No\.?|Number)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/-]{4,})", text, re.I)
        if m:
            return m.group(1).strip(" .,:;")
    # Uber sample receipt does not display a trip/receipt ID; do not invent one.
    if platform == "Uber":
        m = re.search(r"\b(?:Trip|Receipt)\s*(?:ID|No\.?|Number)\s*[:#\-]?\s*([A-Z0-9-]{5,})", text, re.I)
        if m:
            return m.group(1)
    # Generic fallback for supported platforms only.
    m = re.search(r"\b(?:Invoice|Order)\s*(?:No\.?|Number|ID)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/-]{5,})", text, re.I)
    return m.group(1).strip(" .,:;") if m else ""

def _amount(text, platform):
    patterns = {
        "Uber": [
            r"^\s*Total\s+₹\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
            r"\bTotal\s+₹\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        "Rapido": [
            r"Selected\s+Price\s*(?:[:\-]\s*)?(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        "Blinkit": [
            r"\bInvoice\s+Value\b\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
            r"\bGrand\s+Total\b\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        "Zepto": [
            r"\bInvoice\s+Value\b\s*[:\-]?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        "Swiggy": [
            r"\bInvoice\s+Total\b\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        "Zomato": [
            r"Amount\s+of\s+INR\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s+settled",
            r"\bInvoice\s+Value\b\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
            r"\bGrand\s+Total\b\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
    }
    for pat in patterns.get(platform, []):
        m = re.search(pat, text, re.I | re.M)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return ""

def extract_bill_fields(text):
    platform = _platform(text)
    if not platform:
        return {
            "Bill No.": "Unidentified",
            "Date": "Unidentified",
            "Nature of Expense": "Unidentified",
            "Paid To": "Unidentified",
            "Amount": "Unidentified",
        }
    return {
        "Bill No.": _find_bill_no(text, platform),
        "Date": _find_date(text, platform),
        "Nature of Expense": CATEGORIES[platform],
        "Paid To": platform,
        "Amount": _amount(text, platform),
    }
