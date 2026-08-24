import streamlit as st
from pathlib import Path

from core.pdf.operations import merge_pdfs


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


st.set_page_config(
    page_title="PDF Toolbox",
    page_icon="📄",
    layout="centered",
)


st.title("📄 PDF Toolbox")
st.write("Simple PDF tools. Get it done.")


st.header("Merge PDF")

uploaded_files = st.file_uploader(
    "Choose PDF files to merge",
    type=["pdf"],
    accept_multiple_files=True,
)


if uploaded_files:
    st.write(f"{len(uploaded_files)} PDF file(s) selected.")

    if st.button("Merge PDFs"):
        if len(uploaded_files) < 2:
            st.error("Please select at least 2 PDF files.")
        else:
            input_paths = []

            for index, uploaded_file in enumerate(uploaded_files):
                input_path = OUTPUT_DIR / f"merge_input_{index}.pdf"

                with open(input_path, "wb") as file:
                    file.write(uploaded_file.getbuffer())

                input_paths.append(input_path)

            output_path = OUTPUT_DIR / "merged_result.pdf"

            try:
                merge_pdfs(
                    input_paths,
                    output_path,
                )

                st.success("PDFs merged successfully.")

                with open(output_path, "rb") as file:
                    st.download_button(
                        label="Download merged PDF",
                        data=file,
                        file_name="merged_result.pdf",
                        mime="application/pdf",
                    )

            except Exception as error:
                st.error(f"Something went wrong: {error}")