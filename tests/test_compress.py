import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.pdf.operations import compress_pdf


TEST_DIR = BASE_DIR / "tests"
OUTPUT_DIR = BASE_DIR / "outputs"


def test_compress_pdf():
    input_pdf = TEST_DIR / "sample1.pdf"
    output_pdf = OUTPUT_DIR / "compressed_test.pdf"

    OUTPUT_DIR.mkdir(exist_ok=True)

    compress_pdf(
        input_pdf,
        output_pdf,
    )

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0