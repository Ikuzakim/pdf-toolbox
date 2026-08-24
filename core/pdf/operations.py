import pymupdf
from PIL import Image


def merge_pdfs(input_paths, output_path):
    """
    Merge multiple PDF files into a single PDF.

    Args:
        input_paths: List of PDF file paths.
        output_path: Path for the merged PDF.

    Returns:
        The output PDF path.
    """
    if not input_paths:
        raise ValueError("At least one PDF file is required.")

    merged_document = pymupdf.open()

    try:
        for input_path in input_paths:
            source_document = pymupdf.open(input_path)

            try:
                merged_document.insert_pdf(source_document)
            finally:
                source_document.close()

        merged_document.save(output_path)

    finally:
        merged_document.close()

    return output_path



def split_pdf(input_path, output_paths):
    """
    Split a PDF into separate PDF files.

    Args:
        input_path: Path to the source PDF.
        output_paths: List of output PDF paths.

    Returns:
        List of created output PDF paths.
    """
    source_document = pymupdf.open(input_path)

    try:
        page_count = len(source_document)

        if len(output_paths) != page_count:
            raise ValueError(
                "The number of output paths must match the number of PDF pages."
            )

        for page_number, output_path in enumerate(output_paths):
            output_document = pymupdf.open()

            try:
                output_document.insert_pdf(
                    source_document,
                    from_page=page_number,
                    to_page=page_number,
                )
                output_document.save(output_path)
            finally:
                output_document.close()

    finally:
        source_document.close()

    return output_paths



def compress_pdf(input_path, output_path):
    """
    Compress/optimize a PDF using PyMuPDF's built-in options.

    Args:
        input_path: Path to the source PDF.
        output_path: Path for the compressed PDF.

    Returns:
        The output PDF path.
    """
    document = pymupdf.open(input_path)

    try:
        document.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True,
        )
    finally:
        document.close()

    return output_path



def reorder_pages(input_path, output_path, page_order):
    """
    Reorder and/or delete pages from a PDF.

    Args:
        input_path: Path to the source PDF.
        output_path: Path for the resulting PDF.
        page_order: Zero-based page indexes in the desired order.

    Returns:
        The output PDF path.
    """
    source_document = pymupdf.open(input_path)
    output_document = pymupdf.open()

    try:
        page_count = len(source_document)

        for page_index in page_order:
            if page_index < 0 or page_index >= page_count:
                raise ValueError(
                    f"Invalid page index: {page_index}. "
                    f"PDF contains {page_count} pages."
                )

            output_document.insert_pdf(
                source_document,
                from_page=page_index,
                to_page=page_index,
            )

        output_document.save(output_path)

    finally:
        output_document.close()
        source_document.close()

    return output_path



def rotate_pdf(input_path, output_path, rotation=90):
    """
    Rotate all pages in a PDF.

    Args:
        input_path: Path to the source PDF.
        output_path: Path for the rotated PDF.
        rotation: Rotation in degrees. Must be 90, 180, or 270.

    Returns:
        The output PDF path.
    """
    if rotation not in (90, 180, 270):
        raise ValueError("Rotation must be 90, 180, or 270 degrees.")

    document = pymupdf.open(input_path)

    try:
        for page in document:
            page.set_rotation((page.rotation + rotation) % 360)

        document.save(output_path)
    finally:
        document.close()

    return output_path



def images_to_pdf(input_paths, output_path):
    """
    Convert one or more images into a PDF.

    Args:
        input_paths: List of image file paths.
        output_path: Path for the resulting PDF.

    Returns:
        The output PDF path.
    """
    if not input_paths:
        raise ValueError("At least one image is required.")

    images = []

    try:
        for input_path in input_paths:
            image = Image.open(input_path)

            if image.mode != "RGB":
                image = image.convert("RGB")

            images.append(image)

        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
        )

    finally:
        for image in images:
            image.close()

    return output_path