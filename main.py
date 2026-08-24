import streamlit as st
import pymupdf

from core.pdf.operations import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    reorder_pages,
    rotate_pdf,
    images_to_pdf,
)

from core.file_manager import (
    create_workspace,
    cleanup_workspace,
)

from core.usage_tracker import (
    can_use,
    record_operation,
    get_usage,
    FREE_OPERATION_LIMIT,
)


st.set_page_config(
    page_title="PDF Toolbox",
    page_icon="📄",
    layout="centered",
)


st.title("📄 PDF Toolbox")

st.write(
    "Simple PDF tools for everyday document tasks."
)

st.caption(
    "Merge • Split • Compress • Reorder • Rotate • Images → PDF"
)


usage = get_usage()

st.caption(
    f"Free usage: "
    f"{usage['operations']}/{FREE_OPERATION_LIMIT} "
    f"operations used this month"
)
st.caption(
    "Free plan • 10 operations/month"
)

st.info(
    "PDF Toolbox Pro — more usage and expanded capabilities. "
    "Coming soon."
)


tool = st.selectbox(
    "What do you want to do?",
    [
        "Merge PDF",
        "Split PDF",
        "Compress PDF",
        "Reorder / Delete Pages",
        "Rotate PDF",
        "Images → PDF",
    ],
)
tool_descriptions = {
    "Merge PDF": "Combine multiple PDF files into one.",
    "Split PDF": "Separate a PDF into individual pages.",
    "Compress PDF": "Reduce PDF file size where possible.",
    "Reorder / Delete Pages": "Rearrange pages or remove unwanted pages.",
    "Rotate PDF": "Rotate all pages by 90°, 180°, or 270°.",
    "Images → PDF": "Turn one or more images into a PDF.",
}

st.caption(tool_descriptions[tool])
st.divider()

# --------------------------------------------------
# MERGE PDF
# --------------------------------------------------

if tool == "Merge PDF":

    st.header("Merge PDF")

    uploaded_files = st.file_uploader(
        "Choose PDF files to merge",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:

        st.write(
            f"{len(uploaded_files)} PDF file(s) selected."
        )

        if st.button("Merge PDFs"):

            if len(uploaded_files) < 2:

                st.warning(
                    "Please select at least 2 PDF files to merge."
                )

            elif not can_use():

                st.warning(
                    "You've reached your 10 free operations "
                    "for this month."
                )

                st.info(
                    "Upgrade to PDF Toolbox Pro for more usage."
                )

            else:

                workspace = create_workspace()

                try:

                    input_paths = []

                    for index, uploaded_file in enumerate(
                        uploaded_files
                    ):

                        input_path = (
                            workspace / f"input_{index}.pdf"
                        )

                        with open(input_path, "wb") as file:
                            file.write(
                                uploaded_file.getbuffer()
                            )

                        input_paths.append(input_path)

                    output_path = (
                        workspace / "merged_result.pdf"
                    )

                    merge_pdfs(
                        input_paths,
                        output_path,
                    )

                    record_operation()

                    st.success(
                        "PDFs merged successfully."
                    )

                    with open(output_path, "rb") as file:

                        st.download_button(
                            label="Download merged PDF",
                            data=file,
                            file_name="merged_result.pdf",
                            mime="application/pdf",
                        )

                except Exception:

                    st.error(
                        "We couldn't merge those PDFs. "
                        "Please make sure the files are valid "
                        "PDF documents and try again."
                    )

                finally:

                    cleanup_workspace(workspace)


# --------------------------------------------------
# SPLIT PDF
# --------------------------------------------------

elif tool == "Split PDF":

    st.header("Split PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF to split",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "split_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            try:

                document = pymupdf.open(input_path)

                page_count = len(document)

                document.close()

            except Exception:

                st.error(
                    "We couldn't read this PDF. "
                    "Please upload a valid PDF document."
                )

                page_count = 0

            if page_count > 0:

                st.write(
                    f"This PDF contains **{page_count} page(s)**."
                )

                if st.button("Split PDF"):

                    if not can_use():

                        st.warning(
                            "You've reached your 10 free operations "
                            "for this month."
                        )

                        st.info(
                            "Upgrade to PDF Toolbox Pro for more usage."
                        )

                    else:

                        try:

                            output_paths = [
                                workspace / f"split_page_{i + 1}.pdf"
                                for i in range(page_count)
                            ]

                            split_pdf(
                                input_path,
                                output_paths,
                            )

                            record_operation()

                            st.success(
                                "PDF split successfully."
                            )

                            for index, output_path in enumerate(
                                output_paths
                            ):

                                with open(
                                    output_path,
                                    "rb"
                                ) as file:

                                    st.download_button(
                                        label=(
                                            f"Download page "
                                            f"{index + 1}"
                                        ),
                                        data=file,
                                        file_name=(
                                            f"page_{index + 1}.pdf"
                                        ),
                                        mime="application/pdf",
                                        key=(
                                            f"split_download_{index}"
                                        ),
                                    )

                        except Exception:

                            st.error(
                                "We couldn't split this PDF. "
                                "Please try another valid PDF."
                            )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# COMPRESS PDF
# --------------------------------------------------

elif tool == "Compress PDF":

    st.header("Compress PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF to compress",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "compress_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            original_size = input_path.stat().st_size

            if original_size > 0:

                st.write(
                    f"Original file size: "
                    f"**{original_size / 1024:.1f} KB**"
                )

                if st.button("Compress PDF"):

                    if not can_use():

                        st.warning(
                            "You've reached your 10 free operations "
                            "for this month."
                        )

                        st.info(
                            "Upgrade to PDF Toolbox Pro for more usage."
                        )

                    else:

                        try:

                            output_path = (
                                workspace
                                / "compressed_result.pdf"
                            )

                            compress_pdf(
                                input_path,
                                output_path,
                            )

                            compressed_size = (
                                output_path.stat().st_size
                            )

                            record_operation()

                            st.success(
                                "PDF compression complete."
                            )

                            st.write(
                                f"Compressed file size: "
                                f"**{compressed_size / 1024:.1f} KB**"
                            )

                            if compressed_size < original_size:

                                reduction = (
                                    (
                                        original_size
                                        - compressed_size
                                    )
                                    / original_size
                                ) * 100

                                st.write(
                                    f"Size reduction: "
                                    f"**{reduction:.1f}%**"
                                )

                            else:

                                st.info(
                                    "This PDF could not be reduced "
                                    "further with the current "
                                    "compression method."
                                )

                            with open(
                                output_path,
                                "rb"
                            ) as file:

                                st.download_button(
                                    label=(
                                        "Download compressed PDF"
                                    ),
                                    data=file,
                                    file_name=(
                                        "compressed_result.pdf"
                                    ),
                                    mime="application/pdf",
                                )

                        except Exception:

                            st.error(
                                "We couldn't compress this PDF. "
                                "Please try another valid PDF."
                            )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# REORDER / DELETE PAGES
# --------------------------------------------------

elif tool == "Reorder / Delete Pages":

    st.header("Reorder / Delete Pages")

    uploaded_file = st.file_uploader(
        "Choose a PDF",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "reorder_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            try:

                document = pymupdf.open(input_path)

                page_count = len(document)

                document.close()

            except Exception:

                st.error(
                    "We couldn't read this PDF. "
                    "Please upload a valid PDF document."
                )

                page_count = 0

            if page_count > 0:

                st.write(
                    f"This PDF contains **{page_count} page(s)**."
                )

                st.caption(
                    "Enter the page numbers in the order "
                    "you want them. Leave out a page number "
                    "to delete that page."
                )

                page_order_text = st.text_input(
                    "New page order",
                    placeholder="Example: 3,1,4",
                )

                if st.button("Apply Changes"):

                    if not can_use():

                        st.warning(
                            "You've reached your 10 free operations "
                            "for this month."
                        )

                        st.info(
                            "Upgrade to PDF Toolbox Pro for more usage."
                        )

                    else:

                        try:

                            page_numbers = [
                                int(number.strip())
                                for number in (
                                    page_order_text.split(",")
                                )
                                if number.strip()
                            ]

                            if not page_numbers:

                                raise ValueError(
                                    "Enter at least one page number."
                                )

                            if any(
                                number < 1
                                or number > page_count
                                for number in page_numbers
                            ):

                                raise ValueError(
                                    f"Page numbers must be between "
                                    f"1 and {page_count}."
                                )

                            page_order = [
                                number - 1
                                for number in page_numbers
                            ]

                            output_path = (
                                workspace
                                / "reordered_result.pdf"
                            )

                            reorder_pages(
                                input_path,
                                output_path,
                                page_order,
                            )

                            record_operation()

                            st.success(
                                "PDF pages updated successfully."
                            )

                            with open(
                                output_path,
                                "rb"
                            ) as file:

                                st.download_button(
                                    label=(
                                        "Download updated PDF"
                                    ),
                                    data=file,
                                    file_name=(
                                        "reordered_result.pdf"
                                    ),
                                    mime="application/pdf",
                                )

                        except ValueError as error:

                            st.warning(str(error))

                        except Exception:

                            st.error(
                                "We couldn't update the PDF pages. "
                                "Please check the page order "
                                "and try again."
                            )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# ROTATE PDF
# --------------------------------------------------

elif tool == "Rotate PDF":

    st.header("Rotate PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF to rotate",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "rotate_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            rotation = st.selectbox(
                "Rotation",
                [90, 180, 270],
                format_func=lambda value:
                    f"{value}° clockwise",
            )

            if st.button("Rotate PDF"):

                if not can_use():

                    st.warning(
                        "You've reached your 10 free operations "
                        "for this month."
                    )

                    st.info(
                        "Upgrade to PDF Toolbox Pro for more usage."
                    )

                else:

                    try:

                        output_path = (
                            workspace
                            / "rotated_result.pdf"
                        )

                        rotate_pdf(
                            input_path,
                            output_path,
                            rotation=rotation,
                        )

                        record_operation()

                        st.success(
                            f"PDF rotated "
                            f"{rotation}° clockwise."
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as file:

                            st.download_button(
                                label="Download rotated PDF",
                                data=file,
                                file_name="rotated_result.pdf",
                                mime="application/pdf",
                            )

                    except Exception:

                        st.error(
                            "We couldn't rotate this PDF. "
                            "Please try another valid PDF."
                        )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# IMAGES → PDF
# --------------------------------------------------

elif tool == "Images → PDF":

    st.header("Images → PDF")

    uploaded_files = st.file_uploader(
        "Choose images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_files:

        st.write(
            f"{len(uploaded_files)} image(s) selected."
        )

        if st.button("Convert to PDF"):

            if not can_use():

                st.warning(
                    "You've reached your 10 free operations "
                    "for this month."
                )

                st.info(
                    "Upgrade to PDF Toolbox Pro for more usage."
                )

            else:

                workspace = create_workspace()

                try:

                    input_paths = []

                    for index, uploaded_file in enumerate(
                        uploaded_files
                    ):

                        input_path = (
                            workspace
                            / (
                                f"image_{index}_"
                                f"{uploaded_file.name}"
                            )
                        )

                        with open(
                            input_path,
                            "wb"
                        ) as file:

                            file.write(
                                uploaded_file.getbuffer()
                            )

                        input_paths.append(input_path)

                    output_path = (
                        workspace / "images_result.pdf"
                    )

                    try:

                        images_to_pdf(
                            input_paths,
                            output_path,
                        )

                        record_operation()

                        st.success(
                            "Images converted to PDF successfully."
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as file:

                            st.download_button(
                                label="Download PDF",
                                data=file,
                                file_name="images_result.pdf",
                                mime="application/pdf",
                            )

                    except Exception:

                        st.error(
                            "We couldn't convert these images "
                            "to PDF. Please check the image files "
                            "and try again."
                        )

                finally:

                    cleanup_workspace(workspace)

st.divider()

st.caption(
    "PDF Toolbox • Simple document tools for everyday PDF tasks."
)