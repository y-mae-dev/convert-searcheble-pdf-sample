import os
import sys
from pathlib import Path
from typing import List

import fitz
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_toolbox import document
from ocrmypdf import exceptions, hocrtransform, ocr

# サービスアカウントキーのパスを環境変数に設定
# NOTE 事前にスクリプトを実行するファイルと同じ階層に配置
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "XXXXXXX.json"

# プロジェクトID・ロケーション・プロセッサIDを設定
project_id = "your-project-id"
location = "us"  # またはeu（プロセッサを作成したリージョン）
processor_id = "your-processor-id"  # （作成したプロセッサID）


def process_pdf_by_ocrmypdf(input_pdf: str, output_pdf: str) -> None:
    """
    OCRmyPDFを使ってPDFにOCRテキストレイヤーを付与する

    Args:
        input_pdf (str): 入力PDFファイルパス
        output_pdf (str): 出力PDFファイルパス
    """
    try:
        ocr(
            input_file=input_pdf,
            output_file=output_pdf,
            language="jpn",
            deskew=True,
            clean=True,
            progress_bar=True,
        )
        print(f"[INFO] OCRが正常に完了: {output_pdf}")
    except exceptions.ExitStatusException as e:
        print(f"[ERROR] OCRmyPDFエラー: {e}")


def split_pdf_page_by_page(input_path: str) -> List[str]:
    """
    PDFファイルを1ページずつ分割し、個別ファイルとして保存する

    Args:
        input_path (str): 入力PDFファイルパス

    Returns:
        List[str]: 分割後の各ページPDFファイルパスリスト
    """
    pdf = fitz.open(input_path)
    chunk_files = []

    base_name = os.path.splitext(input_path)[0]

    for i in range(len(pdf)):
        chunk_path = f"{base_name}_page{i + 1}.pdf"
        chunk_pdf = fitz.open()
        chunk_pdf.insert_pdf(pdf, from_page=i, to_page=i)
        chunk_pdf.save(chunk_path)
        chunk_pdf.close()
        chunk_files.append(chunk_path)

    pdf.close()
    return chunk_files


def convert_hocr_to_pdf(
    hocr_path: str, background_pdf_path: str, output_pdf_path: str, dpi: int = 300
) -> None:
    """
    hOCRファイルから透明テキストレイヤーを作成し、背景PDFと合成する

    Args:
        hocr_path (str): hOCRファイルパス
        background_pdf_path (str): 背景PDFファイルパス
        output_pdf_path (str): 出力PDFファイルパス
        dpi (int, optional): 解像度（デフォルト300）
    """
    ocr_only_pdf_path = str(Path(output_pdf_path).with_suffix(".ocr_only.pdf"))

    transformer = hocrtransform.HocrTransform(hocr_filename=Path(hocr_path), dpi=dpi)
    transformer.to_pdf(out_filename=Path(ocr_only_pdf_path))
    print(f"[INFO] 透明テキストPDF生成完了: {ocr_only_pdf_path}")

    merge_background_and_ocr(background_pdf_path, ocr_only_pdf_path, output_pdf_path)
    print(f"[INFO] 背景と透明テキストを合成完了: {output_pdf_path}")

    Path(ocr_only_pdf_path).unlink(missing_ok=True)


def merge_background_and_ocr(
    background_pdf_path: str, ocr_text_pdf_path: str, output_pdf_path: str
) -> None:
    """
    背景PDFと透明テキストレイヤーPDFを合成する

    Args:
        background_pdf_path (str): 背景PDFパス
        ocr_text_pdf_path (str): 透明テキストPDFパス
        output_pdf_path (str): 出力PDFパス
    """
    bg_doc = fitz.open(background_pdf_path)
    ocr_doc = fitz.open(ocr_text_pdf_path)

    for page_num in range(len(bg_doc)):
        bg_page = bg_doc[page_num]
        bg_page.show_pdf_page(bg_page.rect, ocr_doc, page_num)

    bg_doc.save(output_pdf_path, garbage=4, deflate=True)
    bg_doc.close()
    ocr_doc.close()


def process_document_with_docai(file_path: str) -> documentai.Document:
    """
    Document AIでPDFをOCR処理する

    Args:
        file_path (str): 入力PDFパス

    Returns:
        documentai.Document: OCR処理結果
    """
    client = documentai.DocumentProcessorServiceClient()
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    with open(file_path, "rb") as f:
        content = f.read()

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(
            content=content, mime_type="application/pdf"
        ),
    )
    result = client.process_document(request=request)
    return result.document


def save_docai_response_to_json(
    document_obj: documentai.Document, output_path: str
) -> None:
    """
    Document AIレスポンスをJSONファイルとして保存する

    Args:
        document_obj (Document): Documentオブジェクト
        output_path (str): 出力JSONファイルパス
    """
    json_obj = documentai.Document.to_json(document_obj)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_obj)


def convert_docai_response_to_hocr(
    docai_document: documentai.Document, title: str, document_path: str
) -> str:
    """
    Document AI JSONからhOCR形式に変換する

    Args:
        docai_document (Document): OCRドキュメント
        title (str): hOCRファイルタイトル
        document_path (str): Document AI JSONパス

    Returns:
        str: hOCRテキスト
    """
    wrapped_doc = document.Document.from_document_path(document_path=document_path)
    return wrapped_doc.export_hocr_str(title=title)


def merge_pdfs_with_pymupdf(pdf_files: List[str], output_path: str) -> None:
    """
    複数PDFファイルを結合する

    Args:
        pdf_files (List[str]): PDFファイルリスト
        output_path (str): 出力ファイルパス
    """
    merger = fitz.open()
    for pdf_file in pdf_files:
        merger.insert_pdf(fitz.open(pdf_file))
    merger.save(output_path)
    merger.close()


def make_searchable_pdf(
    input_path: str, output_path: str, use_docai: bool = True
) -> None:
    """
    PDFをOCR処理して検索可能なPDFに変換する

    Args:
        input_path (str): 入力PDFパス
        output_path (str): 出力PDFパス
        use_docai (bool, optional): Document AIを使用するか（デフォルトTrue）
    """
    print(f"[INFO] 分割処理中: {input_path}")
    chunk_files = split_pdf_page_by_page(input_path)
    processed_chunks = []
    temp_files = []

    for i, chunk_file in enumerate(chunk_files):
        print(f"[INFO] ページ {i + 1}/{len(chunk_files)} 処理中...")

        base = os.path.splitext(chunk_file)[0]
        hocr_path = f"{base}.hocr.xml"
        json_path = f"{base}.json"
        output_chunk = f"{base}_processed.pdf"

        try:
            if use_docai:
                docai_document = process_document_with_docai(chunk_file)
                save_docai_response_to_json(docai_document, json_path)
                hocr_content = convert_docai_response_to_hocr(
                    docai_document, f"Chunk {i + 1}", json_path
                )

                with open(hocr_path, "w", encoding="utf-8") as f:
                    f.write(hocr_content)

                convert_hocr_to_pdf(hocr_path, chunk_file, output_chunk)

            else:
                process_pdf_by_ocrmypdf(chunk_file, output_chunk)

            processed_chunks.append(output_chunk)
            temp_files += [chunk_file]
            if use_docai:
                temp_files += [hocr_path, json_path]

        except Exception as e:
            print(f"[ERROR] ページ {i + 1} 処理失敗: {e}")

    print("[INFO] 各ページを結合中...")
    merge_pdfs_with_pymupdf(processed_chunks, output_path)

    for path in temp_files + processed_chunks:
        try:
            os.remove(path)
        except Exception as e:
            print(f"[WARN] 一時ファイル削除失敗: {path} -> {e}")

    print(f"[DONE] 完了: {output_path}")


# 実行部分
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python script.py 入力PDF 出力PDF [use_docai]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    use_docai = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else True

    if use_docai:
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            print("[WARN] 認証情報が設定されていません。")

    make_searchable_pdf(input_pdf, output_pdf, use_docai)
