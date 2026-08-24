import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.pdf.operations import merge_pdfs


TEST_DIR = BASE_DIR / "tests"
OUTPUT_DIR = BASE_DIR / "outputs"


def test_merge_pdfs():
    pdf_1 = TEST_DIR / "sample1.pdf"
    pdf_2 = TEST_DIR / "sample2.pdf"
    output_pdf = OUTPUT_DIR / "merged_test.pdf"

    OUTPUT_DIR.mkdir(exist_ok=True)

    merge_pdfs(
        [pdf_1, pdf_2],
        output_pdf,
    )

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0