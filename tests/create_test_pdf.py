import pymupdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
output_path = BASE_DIR / "tests" / "three_page_test.pdf"

document = pymupdf.open()

for page_number in range(1, 4):
    page = document.new_page()
    page.insert_text((72, 72), f"TEST PAGE {page_number}")

document.save(output_path)
document.close()

print(f"Created: {output_path}")