"""
音声文字起こしパイプライン
-------------------------
モノラル音声（日本語話者・ポルトガル語話者の2人）を対象に、
1. pyannote.audio で話者分離
2. 話者ごとに言語を固定してWhisperAPIで文字起こし
3. 結果をCSVに時系列順で出力（翻訳を行う）
までを行う。

翻訳（pt -> ja）はWeb版DeepL Proへ手動で貼り付けて行う運用を想定し、
本スクリプトの責務は「認識とデータ整形」のみに限定している。
"""

import csv
import os

import torch
from openai import OpenAI
from pyannote.audio import Pipeline
from pydub import AudioSegment

# ===========================
# 設定
# ===========================

# APIキーはハードコードせず環境変数から取得
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
HF_TOKEN = os.environ["HF_TOKEN"]

# 話者 -> 言語 のマッピング （テスト結果に応じて調整）
SPEAKER_LANG_MAP = {
    "SPEAKER_00": "ja", #   日本語話者
    "SPEAKER_01": "pt", #   ポルトガル語話者
}

# 話者数 (固定で2名)
NUM_SPEAKERS = 2

# 短すぎる会話（相槌・咳払い・ノイズ）を除去する間隔[ms]
MIN_SEGMENT_MS = 500

# CPU実行時のスレッド数 (Core i7-10510Uを想定)
CPU_THREADS = 4

CSV_HEADER = [
    "start_time",
    "end_time",
    "speaker",
    "language",
    "original_text",
    "translated_text",
]

# ===========================
# 関数化して処理
# ===========================

def load_diarization_pipeline() -> Pipeline:
    """話者分離モデルをロードしCPUに割り当てる"""
    torch.set_num_threads(CPU_THREADS)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HF_TOKEN,
    )
    pipeline.to(torch.device("CPU"))
    return pipeline


