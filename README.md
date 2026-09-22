<style>
    /* フォント・行間・余白の調整 */
    body{
        font-family: "Segoe UI", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
        line-height: 1.7;
        color: #333333;
        max-width: 980px;
        margin: 0 auto;
        padding: 20px;
    }

    /* 見出しデザイン */
    h1 {
        color: #1a365d;
        border-bottom: 3px solid #2b6cb0;
        padding-bottom: 8px;
    }
    h2 {
        color: #2c5282;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
        margin-top: 2em;
    }

    /* 警告・注意ボックス */
    .alert-warning {
        background-color: #fffaf0;
        border-left: 5px solid #dd6b20;
        color: #9c4221;
        padding: 12px 16px;
        margin: 15px 0;
        border-radius: 4px;
        font-weight: 500;
    }

    /* コマンド確認コメント */
    .cmd-comment {
        color: #2f855a;
        font-weight: bold;
    }

    /* 赤字強調 */
    .text-danger {
        color: #e53e3e;
        font-weight: bold;
    }

    /* 処理結果・手順 */
    .text-info {
        color: #2b6cb0;
        font-weight: bold;
    }

    /* リストや箇条書きの装飾 */
    ul, ol {
        padding-left: 24px;
    }
    li {
        margin-bottom: 6px;
    }

    /* インラインコードの背景 */
    code {
        background-color: #edf2f7;
        color: #805ad5;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: Consolas, Monaco, 'Courier New', monospace;
    }

</style>

# 音声文字起こしツール

## はじめに

このツールは、指定された音声フォルダ内の音声ファイル（`.wav`形式のみ）を自動で文字起こしし、Excelで開けるCSVファイルを出力します。

---

## 1. 音声ファイルの配置

ICレコーダーから取り出した音声を、`app.py` と同じフォルダにある `sound` フォルダに入れます。

- 例: `1.wav`, `2.wav`, `3.wav`
- ファイル名は `1.wav`, `2.wav`, `3.wav` を基本にしてください
- 新規録音があれば `3.wav` へ名前を変更してから実行してください

---

## 2. `.env` ファイルの配置

プロジェクト直下に `.env` ファイルがあることを確認してください。

内容は次のような形式です。

```env
OPENAI_API_KEY=ここにOpenAIのAPIキーを貼り付け
HF_TOKEN=ここにHuggingFaceのトークンを貼り付け
```

<div class="alert-box">
    Hugging Face 側の `pyannote` モデル利用条件に同意していない場合、話者分離のロードに失敗します。
</div>

---

## 3. 実行手順

1. zip化されたフォルダをデスクトップ上に展開してください。
2. フォルダ内の `run.bat` をダブルクリックしてください。

`run.bat` は必要なファイルを WSL のホームディレクトリ直下に一時コピーして処理し、処理後に生成された `*_result.csv` を配布フォルダ内の `results` フォルダへ移動します。

---

## 4. 実行時間と注意

- 処理にはかなり時間がかかります
- PCの負荷が高くなるため、そのまま放置して問題ありませんが、PCの自動スリープ設定をオフにしてください
- 1時間前後かかる場合があります

---

## 5. 出力結果

処理が終わると、生成されたCSVが `translate/results` フォルダへ移動します。
以下のようなファイルをExcelで開いてください。

- `1_result.csv`
- `2_result.csv`
- `3_result.csv`

CSVを右クリック→ `プログラムから開く` → `Excel` で開き、ポルトガル語の行を選んでDeepLへ貼り付けて翻訳してください。
