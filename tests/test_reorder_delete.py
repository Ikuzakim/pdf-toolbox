import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.pdf.operations import reorder_pages


TEST_DIR = BASE_DIR / "tests"
OUTPUT_DIR = BASE_DIR / "outputs"


def test_reorder_delete():
    input_pdf = TEST_DIR / "sample1.pdf"
    output_pdf = OUTPUT_DIR / "reordered_test.pdf"

    OUTPUT_DIR.mkdir(exist_ok=True)

    import pymupdf

    document = pymupdf.open(input_pdf)
    page_count = len(document)
    document.close()

    assert page_count >= 1

    page_order = list(range(page_count))

    reorder_pages(
        input_pdf,
        output_pdf,
        page_order,
    )

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0