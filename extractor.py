import re
from datetime import datetime

CATEGORIES = [
    "Food & Snacks", "Laundry", "Mobile", "Air Travel",
    "Ground Transport", "Hotel Accommodation",
    "Printing & Stationery", "Digital Media Payments",
    "Vendor Payments", "Others",
]

CATEGORY_KEYWORDS = {
    "Food & Snacks": [
        "restaurant service", "restaurant name", "food", "grocery",
        "blink commerce", "zomato hyperpure", "grofers", "domino",
        "chai", "bakers", "pizza", "cafe", "superwell comtrade",
    ],
    "Laundry": ["washeteria", "fabklean", "wash & iron", "laundry", "dry clean"],
    "Ground Transport": ["rapido", "cab_receipt", "auto_receipt", "ride id", "uber", "ola", "taxi"],
    "Mobile": ["mobile recharge", "telecom", "airtel", "jio", "vodafone"],
    "Air Travel": ["airline", "flight", "boarding pass", "air india", "indigo"],
    "Hotel Accommodation": ["hotel accommodation", "hotel booking", "lodging", "guest house"],
    "Printing & Stationery": ["printing", "photocopy", "stationery", "toner"],
    "Digital Media Payments": ["meta ads", "facebook ads", "google ads", "instagram ads"],
    "Vendor Payments": ["payment voucher", "vendor payment", "professional fee", "consultancy"],
}

def _clean_lines(text):
    return [re.sub(r"\s+", " ", x).strip(" \t:|") for x in text.splitlines() if x.strip()]

def _find_bill_number(text):
    # Zomato/restaurant tax invoices
    patterns = [
        r"\bInvoice\s*No\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})",
        r"\bInvoice\s*Number\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})",
        # Laundry invoices (e.g. INV-2997, sometimes split over lines)
        r"\bINV\s*[-:]?\s*(\d{2,})",
        # Rapido receipts: ride ID is the document's unique reference
        r"\b(RD\d{10,})\b",
        # Voucher numbers, if present
        r"\bVoucher\s*No\.?\s*[:\-]?\s*([A-Z0-9/\-]{2,})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = m.group(1).strip(" .,:;")
            if value.upper() not in {"ORIGINAL", "RECIPIENT"}:
                return ("INV-" + value if pattern == patterns[2] else value)
    return ""

def _find_date(text):
    # Prefer labelled invoice / bill / voucher dates.
    labelled = [
        r"(?:Invoice\s*Date|Bill\s*Date|Voucher\s*Date|Date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:Invoice\s*Date|Bill\s*Date|Voucher\s*Date|Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
        r"(?:Invoice\s*Date|Bill\s*Date|Voucher\s*Date|Date)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    ]
    for pat in labelled:
        m = re.search(pat, text, re.I)
        if m:
            raw = m.group(1).replace(",", "")
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                        "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    pass
            return raw

    # Rapido booking timestamp, e.g. Sep 12th 2026, 6:59 PM
    m = re.search(r"\b([A-Za-z]{3,9}\s+\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{4})", text)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%b %d %Y").date()
        except ValueError:
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %d %Y").date()
            except ValueError:
                pass
    return ""

def _find_paid_to(text):
    # Use the merchant-facing name, not "ORIGINAL FOR RECIPIENT" or the customer.
    patterns = [
        r"\bRestaurant\s*Name\s*:\s*(.+)",
        r"\bSold\s+By\s*/\s*Seller\s+(.+)",
        r"\bSold\s+By\s*/\s*Seller\s*:\s*(.+)",
        r"\bLegal\s+Entity\s+Name\s*:\s*(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            value = m.group(1).splitlines()[0].strip(" :|")
            if value and "ORIGINAL FOR RECIPIENT" not in value.upper():
                return value[:100]

    # Washeteria / laundry merchant
    if re.search(r"\bWASHETERIA\b", text, re.I):
        return "Washeteria"

    # Rapido receipts: the document is issued by Rapido; driver is not the payee.
    if re.search(r"\bRD\d{10,}\b", text) and re.search(r"Selected Price", text, re.I):
        return "Rapido"

    # Generic supplier / vendor label, avoiding customer name and document headers.
    m = re.search(r"\b(?:Vendor|Supplier|Merchant)\s*Name\s*:\s*(.+)", text, re.I)
    if m:
        return m.group(1).splitlines()[0].strip(" :|")[:100]

    # Fall back to first plausible non-generic line.
    excluded = (
        "tax invoice", "original for recipient", "invoice", "receipt",
        "customer name", "mantrana strategies", "delivery address",
        "gstin", "fssai", "payment voucher", "booking history",
    )
    for line in _clean_lines(text)[:12]:
        low = line.lower()
        if (len(line) >= 3 and not any(x in low for x in excluded)
                and not re.search(r"^\d[\d\s/-]*$", line)):
            return line[:100]
    return ""

def _find_amount(text):
    # Keep the original total-selection approach; this update is focused on
    # correcting Bill No. and Paid To.
    labels = [
        r"(?:grand\\s+total|total\\s+amount|amount\\s+payable|net\\s+payable|total\\s+payable|balance\\s+due|amount\\s+due|net\\s+amount|total)\\s*[:\\-]?\\s*(?:₹|Rs\\.?|INR)?\\s*([0-9][0-9,]*(?:\\.[0-9]{1,2})?)",
        r"(?:₹|Rs\\.?|INR)\\s*([0-9][0-9,]*(?:\\.[0-9]{1,2})?)",
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
        "Paid To": _find_paid_to(text),
        "Amount": _find_amount(text),
    }
