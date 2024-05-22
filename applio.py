import modal
import modal.gpu
from pathlib import Path
import subprocess


local_datasets_dir = ""  # TODO

COMMIT_SHA = "5f9f65b6a05aae3d5a386630133f9ffe431b6af1"
REMOTE_LOGS_DIR = "/root/logs"
LOCAL_MUTE_DIR = Path(__file__).parent / "mute"


vol = modal.Volume.from_name("applio-logs", create_if_missing=True)
try:
    with vol.batch_upload(force=True) as batch:
        batch.put_directory(LOCAL_MUTE_DIR, "/mute")
except AssertionError:
    # リモート側でもアップロード処理が走ってしまうため、local_mute_dirが見つからずにエラーが発生するが無視する。
    pass

image: modal.Image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg")
    .run_commands(
        "cd /root && git init .",
        "cd /root && git remote add --fetch origin https://github.com/IAHispano/Applio.git",
        f"cd /root && git checkout {COMMIT_SHA}",
        f"cd /root && rm -rf {REMOTE_LOGS_DIR}/mute",  # Volumeは空のディレクトリにしかマウントできないため、既存のmuteディレクトリは削除
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

app = modal.App(name="applio", image=image)


@app.cls(
    gpu=modal.gpu.T4(),
    # Allows 100 concurrent requests per container.
    allow_concurrent_inputs=100,
    # An optional maximum number of concurrent containers running the function (use keep_warm for minimum).
    # Restrict to 1 container because we want our ComfyUI session state
    # to be on a single container.
    concurrency_limit=1,
    # An optional minimum number of containers to always keep warm (use concurrency_limit for maximum).
    # keep_warm=1,
    timeout=86400,  # 1 days
    volumes={REMOTE_LOGS_DIR: vol},
    _allow_background_volume_commits=True,
    mounts=(
        [
            modal.Mount.from_local_dir(
                local_datasets_dir, remote_path="/root/assets/datasets"
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
        import threading

        run_prerequisites_script(
            "False", "True", "True", "True"
        )  # pretrained_v2ダウンロード

        custom_pretrained_urls = [
            "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/D_KLMv7s_Batch3E_48k.pth",
            "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/G_KLMv7s_Batch3E_48k.pth",
            "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/D_KLMv7s_Batch3E_ContVec_48k.pth",
            "https://huggingface.co/SeoulStreamingStation/KLMv7s_Batch3/resolve/main/G_KLMv7s_Batch3E_ContVec_48k.pth",
        ]
        pretraineds_custom_path = os.path.join(
            "rvc", "pretraineds", "pretraineds_custom"
        )
        os.makedirs(pretraineds_custom_path, exist_ok=True)
        for url in custom_pretrained_urls:
            threading.Thread(
                target=wget.download, args=(url, pretraineds_custom_path)
            ).start()
            print(f"Downloading {url} to {pretraineds_custom_path}")

    @modal.web_server(port=6969, startup_timeout=120)
    def web(self):
        cmd = "python app.py --port 6969"
        subprocess.Popen(cmd, shell=True)
