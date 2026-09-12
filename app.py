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
from dotenv import load_dotenv

load_dotenv()   # .env を読み込み、os.environ に反映

# ===========================
# 設定
# ===========================

# APIキーはハードコードせず環境変数から取得
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
HF_TOKEN = os.environ["HF_TOKEN"]

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
        token=HF_TOKEN,
    )
    if pipeline is None:
        raise RuntimeError(
            "パイプラインのロードに失敗しました。HF_TOKENが正しいか、"
            "モデルページの利用条件に同意済みかを確認してください。"
        )
    
    pipeline.to(torch.device("CPU"))
    return pipeline

def format_timestamp(seconds: float) -> str:
    """秒数をmm:ss.s形式に整形"""
    minutes = int(seconds // 60)
    remainder = seconds % 60
    return f"{minutes:02d}:{remainder:04.1f}"

def transcribe_segment(client: OpenAI, chunk: AudioSegment, language: str,
                       temp_path: str) -> str:
    """音声チャンク1件をWhisper APIで文字起こしする"""
    chunk.export(temp_path, format="wav")
    with open(temp_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="Whisper-1",
            file=audio_file,
            language=language,  #言語固定で制度を最大化
        )
    return transcript.text.strip()
    
def transcribe_to_csv(audio_path: str,
                      output_csv_path: str = "transcription_result.csv") -> None:
    """音声ファイル全体を処理し、結果をCSVに書き出す"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    temp_chunk_path = "temp_chunk.wav"
    
    print("1. 話者分離モデルをロード中...")
    diarization_pipeline = load_diarization_pipeline()
    
    print("2. 音声解析 （話者分離） を実行中...")
    diarization = diarization_pipeline(audio_path, num_speakers=NUM_SPEAKERS)
    
    print("3. 音声の切り出しと精密文字起こしを開始...")
    audio = AudioSegment.from_file(audio_path)
    
    with open(output_csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start_ms = int(turn.start * 1000)
            end_ms = int(turn.end * 1000)
            
            if end_ms - start_ms < MIN_SEGMENT_MS:
                continue
            
            language = SPEAKER_LANG_MAP.get(speaker, "pt")
            chunk = audio[start_ms:end_ms]
            text = transcribe_segment(client, chunk, language, temp_chunk_path)
            
            if not text:
                continue
            
            start_formatted = format_timestamp(turn.start)
            end_formatted = format_timestamp(turn.end)
            
            # translated_text は手動貼り付け用に空欄のまま出力
            writer.writerow(
                [start_formatted, end_formatted, speaker, language, text, ""]
            )
            print(f"[{start_formatted} - {end_formatted}] {speaker}({language}): {text}")
            
            if os.path.exists(temp_chunk_path):
                os.remove(temp_chunk_path)
                
            print("f\n完了: 結果を '{output_csv_path}' に保存しました。")
            
    if __name__ == "__main__":
        TARGET_AUIDO = "test.mp3"
        transcribe_to_csv(TARGET_AUIDO)