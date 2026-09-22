#!/usr/bin/env bash
# ============================================================
# セットアップ & 実行スクリプト
# author:Daiki Suzuki
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
WORK_DIR="$HOME/translate_work"

copy_project_to_work_dir() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        echo "'$PROJECT_DIR/.env' が見つかりません。配布フォルダに .env を配置してください。"
        exit 1
    fi

    rm -rf "$WORK_DIR"
    mkdir -p "$WORK_DIR/sound"

    cp "$PROJECT_DIR/app.py" "$WORK_DIR/app.py"
    cp "$PROJECT_DIR/requirements.txt" "$WORK_DIR/requirements.txt"

    shopt -s nullglob
    audio_files=("$PROJECT_DIR/sound"/*.wav)
    shopt -u nullglob
    if [ "${#audio_files[@]}" -eq 0 ]; then
        echo "'$PROJECT_DIR/sound' フォルダの直下に .wav ファイルがありません。"
        exit 1
    fi
    cp "${audio_files[@]}" "$WORK_DIR/sound/"

    cp "$PROJECT_DIR/.env" "$WORK_DIR/.env"
}

move_results_to_results_dir() {
    local result_files=()
    mapfile -t result_files < <(find "$WORK_DIR" -maxdepth 1 -type f -name '*_result.csv' -print)

    if [ "${#result_files[@]}" -eq 0 ]; then
        echo "処理結果のCSVが見つかりませんでした。"
        return 1
    fi

    RESULTS_DIR="$PROJECT_DIR/results"
    mkdir -p "$RESULTS_DIR"
    mv "${result_files[@]}" "$RESULTS_DIR/"
    echo "CSVを配布フォルダの results へ移動しました: $RESULTS_DIR"
}

echo "============================================"
echo " 1. OSパッケージのインストール "
echo "============================================"

sudo apt update
sudo apt install -y ffmpeg python3 python3-venv python3-pip

echo ""
echo "============================================"
echo " 2. Python仮想環境の作成"
echo "============================================"

copy_project_to_work_dir
cd "$WORK_DIR"

if [ ! -d "$WORK_DIR/venv" ]; then
    python3 -m venv "$WORK_DIR/venv"
    echo "venv を新規作成しました。"
else
    echo "venv は既に存在するため作成をスキップします。"
fi

# 以降、仮想環境内のpip/pythonを使う
source "$WORK_DIR/venv/bin/activate"

echo ""
echo "============================================"
echo " 3. 必要なPythonパッケージのインストール"
echo "============================================"

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "============================================"
echo " 4. 配布済み .env の確認"
echo "============================================"

if [ ! -f ".env" ]; then
    echo "'$PROJECT_DIR/.env' のコピーに失敗しました。"
    exit 1
fi

echo "配布フォルダの .env を使用します。処理を続行します。"

echo ""
echo "============================================"
echo " 5. 文字起こしパイプラインの実行"
echo "============================================"

python3 app.py

echo ""
move_results_to_results_dir
rm -rf "$WORK_DIR"
echo "完了しました。results フォルダ内の *_result.csv を確認してください。"