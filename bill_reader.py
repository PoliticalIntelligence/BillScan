import io
import fitz
from PIL import Image
import pytesseract

def _ocr_image(image):
    # Improve readability for common scanned bills.
    image = image.convert("L")
    return pytesseract.image_to_string(image, config="--psm 6")

def extract_text_from_file(extension, content):
    if extension == ".pdf":
        document = fitz.open(stream=content, filetype="pdf")
        page_text = []
        for page in document:
            text = page.get_text("text").strip()
            if len(text) < 25:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text = _ocr_image(image)
            page_text.append(text)
        return "\n".join(page_text)

    if extension in {".jpg", ".jpeg", ".png"}:
        image = Image.open(io.BytesIO(content))
        return _ocr_image(image)

    raise ValueError("Unsupported file type")
