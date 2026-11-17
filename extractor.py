import re
from datetime import datetime

PLATFORM_CATEGORIES = {
    "Uber": "Ground Transport",
    "Rapido": "Ground Transport",
    "Blinkit": "Food & Snacks",
    "Zomato": "Food & Snacks",
    "Zepto": "Food & Snacks",
    "Swiggy": "Food & Snacks",
}

def _platform(text):
    t = text.lower()

    # Identify the specific platform using distinctive invoice/receipt wording.
    if "thanks for riding" in t and "uber" in t:
        return "Uber"
    if re.search(r"\bRD\d{10,}\b", text, re.I) or (
        "rapido" in t and ("selected price" in t or "ride id" in t)
    ):
        return "Rapido"
    if "swiggy limited" in t or re.search(r"\bswiggy\b", t):
        return "Swiggy"
    if "zepto marketplace" in t or re.search(r"\bzepto\b", t):
        return "Zepto"
    if "blink commerce" in t or re.search(r"\bblinkit\b", t):
        return "Blinkit"
    if "zomato" in t or "eternal limited" in t:
        return "Zomato"
    return ""

def _clean_amount(value):
    try:
        return round(float(value.replace(",", "").strip()), 2)
    except (ValueError, AttributeError):
        return ""

def _find_date(text):
    # Supports invoice dates, receipt dates and Rapido's ordinal date format.
    patterns = [
        r"(?:Date\s+of\s+Invoice|Invoice\s+Date|Date)\s*[:\-]?\s*(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"\b([A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{4})\b",
        r"\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s+\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        raw = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", match.group(1), flags=re.I)
        raw = raw.replace(",", "").strip()
        for fmt in (
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
            "%d-%b-%Y", "%d-%B-%Y",
            "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y",
        ):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
    return ""

def _find_bill_no(text, platform):
    if platform == "Rapido":
        match = re.search(r"\b(RD\d{10,})\b", text, re.I)
        return match.group(1).upper() if match else ""

    if platform == "Swiggy":
        patterns = [r"\bInvoice\s*No\s*:\s*([A-Z0-9/-]+)", r"\bOrder\s*ID\s*:\s*([A-Z0-9/-]+)"]
    elif platform in {"Blinkit", "Zepto"}:
        patterns = [
            r"\bInvoice\s*Number\s*:\s*([A-Z0-9/-]+)",
            r"\bInvoice\s*No\.?\s*:\s*([A-Z0-9/-]+)",
        ]
    elif platform == "Zomato":
        patterns = [r"\bInvoice\s*No\.?\s*:\s*([A-Z0-9/-]+)"]
    else:  # Uber receipt may not contain a visible trip reference.
        patterns = [
            r"\b(?:Trip|Receipt)\s*(?:ID|No\.?|Number)\s*[:#-]?\s*([A-Z0-9-]{5,})"
        ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip(" .,:;")
    return ""

def _amount_after_label(text, pattern):
    match = re.search(pattern, text, re.I | re.M)
    return _clean_amount(match.group(1)) if match else ""

def _find_amount(text, platform):
    if platform == "Uber":
        # Uber trip receipt: Total is the bill amount; do not use suggested fare.
        patterns = [
            r"(?m)^\s*Total\s*₹\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$",
            r"\bTotal\s*₹\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ]
        for pattern in patterns:
            value = _amount_after_label(text, pattern)
            if value != "":
                return value

    elif platform == "Rapido":
        # The sample labels the reimbursable ride charge as Selected Price.
        value = _amount_after_label(
            text,
            r"\bSelected\s+Price\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
        )
        if value != "":
            return value

    elif platform == "Zomato":
        # Zomato's receipt explicitly states the amount settled against the order.
        patterns = [
            r"\bAmount\s+of\s+INR\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s+settled",
            r"\bTotal\s+Value\b[\s\S]{0,180}?\b([0-9][0-9,]*\.\d{2})\s*(?:\r?\n|$)",
        ]
        for pattern in patterns:
            value = _amount_after_label(text, pattern)
            if value != "":
                return value

    elif platform in {"Blinkit", "Zepto"}:
        # Invoice Value is a distinct labelled total on Zepto invoices.
        if platform == "Zepto":
            value = _amount_after_label(
                text, r"\bInvoice\s+Value\s*[:\-]?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
            )
            if value != "":
                return value

        # Blinkit table's Total row contains several columns; take its final numeric
        # amount on the row, not the tax/handling values or individual item totals.
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        words_index = next(
            (i for i, line in enumerate(lines) if re.search(r"Amount\s+in|Amount$", line, re.I)),
            len(lines)
        )
        total_indices = [
            i for i, line in enumerate(lines[:words_index])
            if re.match(r"^Total\b", line, re.I)
        ]
        if total_indices:
            # The final Total row before Amount in Words is the invoice grand total.
            index = total_indices[-1]
            row_parts = lines[index:min(index + 8, words_index)]
            row_text = " ".join(row_parts)
            nums = re.findall(r"(?<![A-Z])\d[\d,]*\.\d{2}", row_text)
            if nums:
                return _clean_amount(nums[-1])

        # Some Blinkit/Zepto layouts print an explicit amount-in-words or invoice total.
        for pattern in (
            r"\bInvoice\s+Value\s*[:\-]?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
            r"\bGrand\s+Total\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ):
            value = _amount_after_label(text, pattern)
            if value != "":
                return value

    elif platform == "Swiggy":
        value = _amount_after_label(
            text, r"\bInvoice\s+Total\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
        )
        if value != "":
            return value

    return ""

def extract_bill_fields(text):
    platform = _platform(text)

    # Only the six approved platforms are supported. Every other document is
    # deliberately marked Unidentified instead of being guessed into a category.
    if not platform:
        return {
            "Bill No.": "Unidentified",
            "Date": "Unidentified",
            "Nature of Expense": "Unidentified",
            "Paid To": "Unidentified",
            "Amount": "Unidentified",
        }

    return {
        "Bill No.": _find_bill_no(text, platform) or "",
        "Date": _find_date(text) or "",
        "Nature of Expense": PLATFORM_CATEGORIES[platform],
        "Paid To": platform,
        "Amount": _find_amount(text, platform),
    }
