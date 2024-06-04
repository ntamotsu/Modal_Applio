"""
ApplioをModal上で起動するスクリプト
"""

import modal
import modal.gpu
from pathlib import Path
import subprocess


# TODO: ローカルにある音声データセットのディレクトリを指定してください。 e.g. "/Users/username/wav_datasets"
local_datasets_dir = ""
custom_pretrained_urls = [
    "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/D_KLMv7s_Batch3F_48k.pth",
    "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/G_KLMv7s_Batch3F_48k.pth",
    # 適宜追加・削除してください
]

logs_volume_name = "applio-logs"
app_name = "applio"

TAG_NAME = "3.2.0"
REMOTE_LOGS_DIR = "/root/logs"
REMOTE_DATASETS_DIR = "/root/assets/datasets"
LOCAL_MUTE_DIR = Path(__file__).parent / "mute"


vol = modal.Volume.from_name(logs_volume_name, create_if_missing=True)
try:
    # ローカルからVolumeにmuteディレクトリをアップロード
    with vol.batch_upload(force=True) as batch:
        batch.put_directory(LOCAL_MUTE_DIR, "/mute")
    print("Batch upload completed.")
except AssertionError as e:
    # リモート側でもアップロード処理が走ってしまうため、LOCAL_MUTE_DIRが見つからずにエラーが発生するが無視する。
    print(f"Ignoring batch upload error: {e}")

image: modal.Image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg")
    .run_commands(
        "cd /root && git init .",
        "cd /root && git remote add --fetch origin https://github.com/IAHispano/Applio.git",
        f"cd /root && git checkout {TAG_NAME}",
        f"rm -rf {REMOTE_LOGS_DIR}/mute",  # Volumeは空のディレクトリにしかマウントできないため、既存のmuteディレクトリは一旦削除
        "cd /root && pip install -r requirements.txt",
        "cd /root && pip uninstall torch torchvision torchaudio -y",
        "cd /root && pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1",
    )
    .env(
        {
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
            "PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.0",
            "GRADIO_SERVER_NAME": "0.0.0.0",
        }
    )
)

app = modal.App(name=app_name, image=image)


@app.cls(
    gpu=modal.gpu.T4(),
    allow_concurrent_inputs=100,
    concurrency_limit=1,
    timeout=60 * 60 * 24,  # 1 day (設定可能最大値)
    container_idle_timeout=60,  # 1 minute (デフォルト値)
    volumes={REMOTE_LOGS_DIR: vol},
    _allow_background_volume_commits=True,
    mounts=(
        [
            modal.Mount.from_local_dir(
                local_datasets_dir, remote_path=REMOTE_DATASETS_DIR
            )
        ]
        if local_datasets_dir
        else ()
    ),
)
class Model:
    @modal.build()
    def model_preload(self):
        from core import run_prerequisites_script  # type: ignore
        import wget  # type: ignore
        import os

        # pretrained_v2ダウンロード
        run_prerequisites_script("False", "True", "True", "True")

        # custom pretrainedダウンロード
        pretraineds_custom_path = os.path.join(
            "rvc", "pretraineds", "pretraineds_custom"
        )
        os.makedirs(pretraineds_custom_path, exist_ok=True)
        for url in custom_pretrained_urls:
            print(f"Downloading {url} to {pretraineds_custom_path}")
            wget.download(url, pretraineds_custom_path)

    @modal.web_server(port=6969, startup_timeout=120)
    def web(self):
        cmd = "python app.py --port 6969"
        subprocess.Popen(cmd, shell=True)
