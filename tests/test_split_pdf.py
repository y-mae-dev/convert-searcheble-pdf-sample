import os
from pathlib import Path

import fitz

from convert_to_searchable_pdf_sapmle import split_pdf_page_by_page


def test_split_pdf_creates_two_pages(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    output_files = split_pdf_page_by_page(str(pdf_path))

    assert len(output_files) == 2
    for f in output_files:
        assert Path(f).exists()

    for f in output_files:
        Path(f).unlink(missing_ok=True)
    pdf_path.unlink(missing_ok=True)
