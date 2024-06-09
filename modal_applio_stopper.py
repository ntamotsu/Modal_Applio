"""
## スクリプトの概要:
  Applioでは学習が終了すると`added~~.index`ファイルが自動で生成されるので、定期的にチェックしてこのファイルを検知したらApplioを強制停止します。
  
## 実行手順:
1. 停止対象であるApplioのApp IDをModalダッシュボードで確認して`applio_app_id`に入力。 e.g. "ap-xxxxxxxx"
2. 学習開始時に指定したモデル名を`rvc_model_name`に入力。
3. `python modal_applio_stopper.py`を実行。
"""

import json
import re
import subprocess
import time


# TODO: ApplioのApp IDをModalダッシュボードで確認して入力。 e.g. "ap-xxxxxxxx"
applio_app_id = ""
# TODO: 学習開始時に指定したモデル名を入力。
rvc_model_name = ""

logs_volume_name = "applio-logs"
volume_check_interval = 60  # volumeチェックする間隔（秒）

# 学習終了時にApplioが生成するファイルのパス(xxx/added~~.index)
FILEPATH_TO_CHECK = r".*added.*\.index"


def check_volume_and_stop():
    """
    volume上に{FILEPATH_TO_CHECK}とマッチするファイルがあるか定期的に確認し、
    存在したらApplio自体を停止する。
    """
    while True:
        print("\n\nvolumeをチェックします...")
        dir_to_check = rvc_model_name
        result = subprocess.run(
            f"modal volume ls --json {logs_volume_name} {dir_to_check}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        stdout, stderr = result.stdout, result.stderr

        if stdout:
            ls_result_json = json.loads(stdout.decode("utf-8", errors="replace"))
            for item in ls_result_json:
                print(item["Filename"])
                if item["Type"] == "file" and re.match(
                    FILEPATH_TO_CHECK, item["Filename"]
                ):
                    print(f"{item['Filename']}を検知しました。終了します。")
                    subprocess.run(f"modal app stop {applio_app_id}", shell=True)
                    return
        elif stderr:
            print(stderr.decode("utf-8", errors="replace"))
            return

        print(f"{FILEPATH_TO_CHECK}は見つかりませんでした。")
        for i in range(volume_check_interval, 0, -1):
            print(
                f"次のvolumeチェックまであと{i}秒... (Ctrl+Cで停止)",
                end="\r",
                flush=True,
            )
            time.sleep(1)


def main():
    if not applio_app_id or not rvc_model_name:
        print("applio_app_idとrvc_model_nameを設定してください。")
        return

    check_volume_and_stop()


if __name__ == "__main__":
    main()
