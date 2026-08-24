import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.pdf.operations import images_to_pdf


TEST_DIR = BASE_DIR / "tests"
OUTPUT_DIR = BASE_DIR / "outputs"


def test_images_to_pdf():
    image_files = [
        TEST_DIR / "image1.jpg",
        TEST_DIR / "image2.jpg",
    ]

    output_pdf = OUTPUT_DIR / "images_to_pdf_test.pdf"

    OUTPUT_DIR.mkdir(exist_ok=True)

    existing_images = [
        image for image in image_files
        if image.exists()
    ]

    assert existing_images, "No test images found."

    images_to_pdf(
        existing_images,
        output_pdf,
    )

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0