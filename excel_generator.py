from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

HEADERS = ["Bill No.", "Date", "Nature of Expense", "Paid To", "Amount"]

def build_excel(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Expense Entries"
    sheet.append(HEADERS)

    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in rows:
        sheet.append([row.get(header, "") for header in HEADERS])

    widths = [22, 16, 28, 34, 18]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    for row in sheet.iter_rows(min_row=2):
        row[1].number_format = "DD-MM-YYYY" if hasattr(row[1].value, "strftime") else "General"
        row[4].number_format = '₹#,##0.00'
        for cell in row:
            cell.alignment = Alignment(vertical="top")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
