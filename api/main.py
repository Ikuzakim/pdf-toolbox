from pathlib import Path
import tempfile
import zipfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response

from core.pdf.operations import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    reorder_pages,
    rotate_pdf,
    images_to_pdf,
)


app = FastAPI(
    title="PDF Toolbox API",
    version="1.0.0",
    description="API for PDF Toolbox operations.",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "PDF Toolbox API",
        "version": "1.0.0",
    }


@app.post(
    "/merge",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                },
                            }
                        },
                        "required": ["files"],
                    }
                }
            }
        }
    },
)
async def merge_pdf_endpoint(
    files: list[UploadFile] = File(...),
):
    if len(files) < 2:
        return {
            "error": "At least 2 PDF files are required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_paths = []

        for index, uploaded_file in enumerate(files):
            input_path = temp_path / f"input_{index}.pdf"

            content = await uploaded_file.read()

            with open(input_path, "wb") as output_file:
                output_file.write(content)

            input_paths.append(input_path)

        output_path = temp_path / "merged_result.pdf"

        merge_pdfs(
            input_paths,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="merged_result.pdf"'
        },
    )


@app.post("/split")
async def split_pdf_endpoint(
    file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"

        content = await file.read()

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        import pymupdf

        document = pymupdf.open(input_path)
        page_count = len(document)
        document.close()

        output_dir = temp_path / "split_pages"
        output_dir.mkdir()

        output_paths = [
            output_dir / f"page_{page_number + 1}.pdf"
            for page_number in range(page_count)
        ]

        split_pdf(
            input_path,
            output_paths,
        )

        zip_path = temp_path / "split_result.zip"

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as zip_file:
            for pdf_file in output_paths:
                zip_file.write(
                    pdf_file,
                    arcname=pdf_file.name,
                )

        zip_bytes = zip_path.read_bytes()

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="split_result.zip"'
        },
    )


@app.post("/compress")
async def compress_pdf_endpoint(
    file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "compressed_result.pdf"

        content = await file.read()

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        compress_pdf(
            input_path,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="compressed_result.pdf"'
        },
    )


@app.post("/reorder-delete")
async def reorder_delete_pdf_endpoint(
    file: UploadFile = File(...),
    page_order: str = Form(...),
):
    try:
        page_indexes = [
            int(index.strip())
            for index in page_order.split(",")
            if index.strip()
        ]
    except ValueError:
        return {
            "error": "page_order must contain comma-separated page numbers."
        }

    if not page_indexes:
        return {
            "error": "At least one page index is required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "reordered_result.pdf"

        content = await file.read()

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        try:
            reorder_pages(
                input_path,
                output_path,
                page_indexes,
            )
        except ValueError as error:
            return {
                "error": str(error)
            }

        pdf_bytes = output_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="reordered_result.pdf"'
        },
    )


@app.post("/rotate")
async def rotate_pdf_endpoint(
    file: UploadFile = File(...),
    rotation: int = Form(90),
):
    if rotation not in (90, 180, 270):
        return {
            "error": "Rotation must be 90, 180, or 270 degrees."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "rotated_result.pdf"

        content = await file.read()

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        rotate_pdf(
            input_path,
            output_path,
            rotation,
        )

        pdf_bytes = output_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rotated_result.pdf"'
        },
    )


@app.post(
    "/images-to-pdf",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                },
                            }
                        },
                        "required": ["files"],
                    }
                }
            }
        }
    },
)
async def images_to_pdf_endpoint(
    files: list[UploadFile] = File(...),
):
    if not files:
        return {
            "error": "At least one image is required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_paths = []

        for index, uploaded_file in enumerate(files):
            suffix = Path(uploaded_file.filename or "").suffix or ".jpg"

            input_path = temp_path / f"image_{index}{suffix}"

            content = await uploaded_file.read()

            with open(input_path, "wb") as output_file:
                output_file.write(content)

            input_paths.append(input_path)

        output_path = temp_path / "images_to_pdf_result.pdf"

        images_to_pdf(
            input_paths,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="images_to_pdf_result.pdf"'
        },
    )