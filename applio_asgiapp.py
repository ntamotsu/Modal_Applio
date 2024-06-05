"""
ApplioをModal上で起動するスクリプト(@asgi_app使用)
"""

import modal
import modal.gpu
from pathlib import Path


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

    @modal.asgi_app()
    def launch_gradio(self):
        """Applioのapp.pyの内容ほぼそのまま"""
        import gradio as gr  # type: ignore
        import sys
        import os
        import logging

        now_dir = os.getcwd()
        sys.path.append(now_dir)

        # Tabs
        from tabs.inference.inference import inference_tab  # type: ignore
        from tabs.train.train import train_tab  # type: ignore
        from tabs.extra.extra import extra_tab  # type: ignore
        from tabs.report.report import report_tab  # type: ignore
        from tabs.download.download import download_tab  # type: ignore
        from tabs.tts.tts import tts_tab  # type: ignore
        from tabs.voice_blender.voice_blender import voice_blender_tab  # type: ignore
        from tabs.settings.presence import presence_tab, load_config_presence  # type: ignore
        from tabs.settings.flask_server import flask_server_tab  # type: ignore
        from tabs.settings.fake_gpu import fake_gpu_tab, gpu_available, load_fake_gpu  # type: ignore
        from tabs.settings.themes import theme_tab  # type: ignore
        from tabs.plugins.plugins import plugins_tab  # type: ignore
        from tabs.settings.version import version_tab  # type: ignore
        from tabs.settings.lang import lang_tab  # type: ignore
        from tabs.settings.restart import restart_tab  # type: ignore

        # Assets
        import assets.themes.loadThemes as loadThemes  # type: ignore
        from assets.i18n.i18n import I18nAuto  # type: ignore
        import assets.installation_checker as installation_checker  # type: ignore
        from assets.discord_presence import RPCManager  # type: ignore
        from assets.flask.server import start_flask, load_config_flask  # type: ignore

        i18n = I18nAuto()
        if load_config_presence() == True:
            RPCManager.start_presence()
        installation_checker.check_installation()
        logging.getLogger("uvicorn").disabled = True
        logging.getLogger("fairseq").disabled = True
        if load_config_flask() == True:
            print("Starting Flask server")
            start_flask()

        my_applio = loadThemes.load_json()
        if my_applio:
            pass
        else:
            my_applio = "ParityError/Interstellar"

        with gr.Blocks(theme=my_applio, title="Applio") as Applio:
            gr.Markdown("# Applio")
            gr.Markdown(
                i18n(
                    "Ultimate voice cloning tool, meticulously optimized for unrivaled power, modularity, and user-friendly experience."
                )
            )
            gr.Markdown(
                i18n(
                    "[Support](https://discord.gg/IAHispano) — [Discord Bot](https://discord.com/oauth2/authorize?client_id=1144714449563955302&permissions=1376674695271&scope=bot%20applications.commands) — [Find Voices](https://applio.org/models) — [GitHub](https://github.com/IAHispano/Applio)"
                )
            )
            with gr.Tab(i18n("Inference")):
                inference_tab()

            with gr.Tab(i18n("Train")):
                if gpu_available() or load_fake_gpu():
                    train_tab()
                else:
                    gr.Markdown(
                        i18n(
                            "Training is currently unsupported due to the absence of a GPU. To activate the training tab, navigate to the settings tab and enable the 'Fake GPU' option."
                        )
                    )

            with gr.Tab(i18n("TTS")):
                tts_tab()

            with gr.Tab(i18n("Voice Blender")):
                voice_blender_tab()

            with gr.Tab(i18n("Plugins")):
                plugins_tab()

            with gr.Tab(i18n("Download")):
                download_tab()

            with gr.Tab(i18n("Report a Bug")):
                report_tab()

            with gr.Tab(i18n("Extra")):
                extra_tab()

            with gr.Tab(i18n("Settings")):
                presence_tab()
                flask_server_tab()
                if not gpu_available():
                    fake_gpu_tab()
                theme_tab()
                version_tab()
                lang_tab()
                restart_tab()

        fast_api_app, _, _ = Applio.launch(
            favicon_path="assets/ICON.ico",
            share=True,
        )
        return fast_api_app
