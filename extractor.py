import re
from datetime import datetime

CATEGORIES = [
    "Food & Snacks",
    "Laundry",
    "Mobile",
    "Air Travel",
    "Ground Transport",
    "Hotel Accommodation",
    "Printing & Stationery",
    "Digital Media Payments",
    "Vendor Payments",
    "Others",
]

CATEGORY_KEYWORDS = {
    "Food & Snacks": ["restaurant", "food", "cafe", "catering", "snack", "meal", "hotel bill", "dhaba"],
    "Laundry": ["laundry", "dry clean", "washing", "pressing"],
    "Mobile": ["mobile", "recharge", "prepaid", "postpaid", "telecom", "airtel", "jio", "vi "],
    "Air Travel": ["airline", "flight", "air ticket", "indigo", "air india", "spicejet", "boarding pass"],
    "Ground Transport": ["taxi", "cab", "uber", "ola", "auto", "bus", "railway", "train", "fuel", "petrol", "diesel"],
    "Hotel Accommodation": ["hotel", "lodging", "accommodation", "room rent", "guest house", "resort"],
    "Printing & Stationery": ["printing", "photocopy", "stationery", "paper", "printer", "toner", "flex", "banner"],
    "Digital Media Payments": ["meta", "facebook ads", "google ads", "instagram ads", "digital marketing"],
    "Vendor Payments": ["vendor", "service provider", "professional fee", "consultancy"],
}

DATE_PATTERNS = [
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,]?\s+\d{2,4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}[,]?\s+\d{2,4})\b",
]

def _find_date(text):
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            raw = match.group(1).replace(",", "")
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                        "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    pass
            return raw
    return ""

def _find_bill_number(text):
    patterns = [
        r"(?:invoice|bill|receipt)\s*(?:no|number|#|:)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/\-]{2,})",
        r"(?:inv|in)\s*\.?\s*(?:no|#)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/\-]{2,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip(" .,:;")
    return ""

def _find_amount(text):
    # Prefer explicitly labelled payable/total fields; avoid picking GST rates or dates.
    labels = [
        r"(?:grand\s+total|total\s+amount|amount\s+payable|net\s+payable|total\s+payable|balance\s+due|amount\s+due|net\s+amount|total)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    ]
    found = []
    for pattern in labels:
        for match in re.finditer(pattern, text, re.I):
            try:
                value = float(match.group(1).replace(",", ""))
                if value > 0:
                    found.append(value)
            except ValueError:
                continue
        if found:
            return max(found)
    return ""

def _find_vendor(text):
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) >= 3]
    exclusions = ("invoice", "tax invoice", "receipt", "bill no", "gstin", "date", "customer", "buyer")
    for line in lines[:8]:
        low = line.lower()
        if not any(word in low for word in exclusions) and not re.search(r"\d{5,}", line):
            return line[:100]
    return ""

def _categorise(text):
    low = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in low for keyword in keywords):
            return category
    return "Others"

def extract_bill_fields(text):
    return {
        "Bill No.": _find_bill_number(text),
        "Date": _find_date(text),
        "Nature of Expense": _categorise(text),
        "Paid To": _find_vendor(text),
        "Amount": _find_amount(text),
    }
