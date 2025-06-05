## convert-searcheble-pdf-sample
画像PDFを検索可能なPDFに変換する

### 前提
- uvをインストール済み
- Google Cloud SDKが使える状態であること
- Document AIにて、OCRプロセッサを作成済み
- ocrmypdfを導入済み

### 使用方法
変換させたい入力PDFファイルの名前、出力結果のPDFの名前を指定。
use_docaiオプションを`true`にすることで、Document AIによるOCRが行われる。
`False`にする場合は、OCRmyPDFによるOCRが行われ、PDF変換される。

```zsh
$ uv run convert_to_searchable_pdf_v2.py [input.pdf] [output.pdf] [use_docai]
```

```mermaid
flowchart TD
    A[画像PDF（入力）] --> B{ページごとに分割}

    B --> C1[ページ1]
    B --> C2[ページ2]

    C1 --> D1{Document AIを使うか？}
    C2 --> D2{Document AIを使うか？}

    D1 -- Yes --> E1[Document AIでOCR実行、<br>レスポンスをJSONファイルに保存]
    D1 -- No --> F1[OCRmyPDFでOCR]

    D2 -- Yes --> E2[Document AIでOCR実行、<br>レスポンスをJSONファイルに保存]
    D2 -- No --> F2[OCRmyPDFでOCR]

    E1 --> G1[JSONからhOCRを生成 → <br>透明テキストPDF作成]
    E2 --> G2[JSONからhOCRを生成 → <br>透明テキストPDF作成]

    G1 --> H1[背景PDFと<br>透明テキスト合成]
    G2 --> H2[背景PDFと<br>透明テキスト合成]

    F1 --> I1[テキストが埋め込まれたPDF]
    F2 --> I2[テキストが埋め込まれたPDF]

    H1 --> M[各ページの結果を統合]
    H2 --> M
    I1 --> M
    I2 --> M

    M --> Z[検索可能なPDF（出力）]
```

### テストの実行
依存関係をインストール後、以下のコマンドでテストを実行できます。

```bash
$ pytest
```

