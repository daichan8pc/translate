"""
音声文字起こしパイプライン（修正版）
---------------------------------
モノラル音声（日本語話者・ポルトガル語話者の2人）を対象に、
1. pyannote.audio で話者分離
2. 話者ごとに言語を固定して Whisper API で文字起こし
3. 結果を CSV に時系列順で出力
までを行う。

"""

import csv
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import torch
from dotenv import load_dotenv
from openai import OpenAI
from pyannote.audio import Pipeline
from pydub import AudioSegment

load_dotenv()  # .env を読み込み、os.environ に反映


# ===========================
# 設定
# ===========================


def require_env(name: str) -> str:
    """環境変数が未設定なら明確な例外を投げる"""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"環境変数 '{name}' が設定されていません。'.env' を確認してください。")
    return value


OPENAI_API_KEY = require_env("OPENAI_API_KEY")
HF_TOKEN = require_env("HF_TOKEN")

BASE_DIR = Path(__file__).resolve().parent
SOUND_DIR = BASE_DIR / "sound"

# 話者 -> 言語 のマッピング
SPEAKER_LANG_MAP = {
    "SPEAKER_00": "ja",
    "SPEAKER_01": "pt",
}
DEFAULT_LANGUAGE = "pt"

# 話者数（固定で2名）
NUM_SPEAKERS = 2

# 短すぎる発話（相槌・咳払い・ノイズ）を除去する閾値[ms]
MIN_SEGMENT_MS = 500

# CPU実行時のスレッド数
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
# 関数
# ===========================


def find_wav_files(sound_dir: Path) -> list[Path]:
    """sound_dir 直下にある .wav ファイルを名前順で取得する (サブフォルダ除外)"""
    if not sound_dir.exists():
        raise FileNotFoundError(f"音声フォルダ '{sound_dir}' が見つかりません。")
    return sorted(sound_dir.glob("*.wav"))


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

    pipeline.to(torch.device("cpu"))
    return pipeline


def format_timestamp(seconds: float) -> str:
    """秒数を mm:ss.s 形式に整形する"""
    total_ms = int(round(seconds * 1000))
    minutes, remainder_ms = divmod(total_ms, 60 * 1000)
    seconds_part = remainder_ms / 1000.0
    return f"{minutes:02d}:{seconds_part:05.1f}"


def resolve_language(speaker: str) -> str:
    """話者ラベルから言語を決定する。未知の話者はデフォルトで pt とする"""
    return SPEAKER_LANG_MAP.get(speaker, DEFAULT_LANGUAGE)


def transcribe_segment(client: OpenAI, chunk: AudioSegment, language: str) -> str:
    """音声チャンク1件をWhisper APIで文字起こしする"""
    with NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        chunk.export(temp_path, format="wav")
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
            )
        return transcript.text.strip()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def transcribe_to_csv(audio_path: str | Path, output_csv_path: str | Path = "transcription_result.csv") -> None:
    """音声ファイル全体を処理し、結果をCSVに書き出す"""
    audio_path = Path(audio_path)
    output_csv_path = Path(output_csv_path)

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("1. 話者分離モデルをロード中...")
        diarization_pipeline = load_diarization_pipeline()

        print("2. 音声解析（話者分離）を実行中...")
        diarization = diarization_pipeline(str(audio_path), num_speakers=NUM_SPEAKERS)

        print("3. 音声の切り出しと精密文字起こしを開始...")
        audio = AudioSegment.from_file(str(audio_path))

        output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)

            for turn, _, speaker in diarization.speaker_diarization.itertracks(yield_label=True):
                start_ms = max(0, int(turn.start * 1000))
                end_ms = min(len(audio), int(turn.end * 1000))

                if end_ms - start_ms < MIN_SEGMENT_MS:
                    continue

                language = resolve_language(speaker)
                chunk = audio[start_ms:end_ms]

                try:
                    text = transcribe_segment(client, chunk, language)
                except Exception as exc:
                    print(
                        f"[警告] 文字起こし失敗: {audio_path.name} / {speaker} / "
                        f"{start_ms}ms-{end_ms}ms / {exc}",
                        file=sys.stderr,
                    )
                    continue

                if not text:
                    continue

                start_formatted = format_timestamp(turn.start)
                end_formatted = format_timestamp(turn.end)

                # translated_text は手動貼り付け用に空欄のまま出力
                writer.writerow(
                    [start_formatted, end_formatted, speaker, language, text, ""]
                )
                print(f"[{start_formatted} - {end_formatted}] {speaker}({language}): {text}")

        print(f"\n完了: 結果を '{output_csv_path}' に保存しました。")

    except Exception as exc:
        print(f"\nエラー: {audio_path} の処理中に失敗しました。", file=sys.stderr)
        print(f"詳細: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        wav_files = find_wav_files(SOUND_DIR)
    except FileNotFoundError as exc:
        print(f"'{SOUND_DIR}' フォルダの直下に .wav ファイルを配置してください。")
        raise SystemExit(1) from exc

    if not wav_files:
        print(f"'{SOUND_DIR}' フォルダの直下に .wav ファイルが見つかりませんでした。")
        raise SystemExit(1)

    print(f"{len(wav_files)} 件の音声ファイルを処理します: {', '.join(p.name for p in wav_files)}")

    for audio_path in wav_files:
        output_path = BASE_DIR / f"{audio_path.stem}_result.csv"
        print(f"\n=== {audio_path.name} の処理を開始します。 ===")
        transcribe_to_csv(audio_path, output_csv_path=output_path)
