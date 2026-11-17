import re

def safe_filename(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value or "BillScan"
