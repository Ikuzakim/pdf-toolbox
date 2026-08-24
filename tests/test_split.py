import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.pdf.operations import split_pdf


TEST_DIR = BASE_DIR / "tests"
OUTPUT_DIR = BASE_DIR / "outputs"


def test_split_pdf():
    input_pdf = TEST_DIR / "sample1.pdf"
    output_dir = OUTPUT_DIR / "split_test"

    output_dir.mkdir(exist_ok=True)

    import pymupdf

    document = pymupdf.open(input_pdf)
    page_count = len(document)
    document.close()

    output_paths = [
        output_dir / f"page_{page_number + 1}.pdf"
        for page_number in range(page_count)
    ]

    split_pdf(
        input_pdf,
        output_paths,
    )

    assert len(output_paths) == page_count

    for output_path in output_paths:
        assert output_path.exists()
        assert output_path.stat().st_size > 0