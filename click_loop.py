"""
長い実行時間を要する処理を`@modal.web_server`で立ち上げたwebアプリから行う場合(モデル学習など)、
`@app.cls`や`@app.function`で`timeout`を長く設定しても現状1時間きっかりで強制中断されてしまう。
しかし実は、2ウィンドウでwebアプリを開いて両方から定期的になんらかのリクエストを送り続ければ1時間以上の処理も維持できる。
このスクリプトでは2ウィンドウそれぞれの適当なボタンを交互にクリックし続け、条件を満たしたら中断してwebアプリも停止する。

Usage:
    1. `modal serve applio.py`でApplioを立ち上げ、"Start Training"ボタンを押す直前まで進める。
    2. もう1つのウィンドウでApplioを開く。
    3. 本スクリプトの`applio_app_id`と`rvc_model_name`に値を入力後`python click_loop.py`で起動し、
       開いている2ウィンドウそれぞれで定期クリックしたい箇所を1地点ずつ指定してスペースキーを押す。
    4. 指定した2地点が交互に自動でクリックされ続ける。
    5. 学習が終了したら指定したvolume上の{rvc_model_name}ディレクトリに{FILENAME_TO_CHECK}ファイルが生成されるので、
       それを検知して終了する。
"""

import asyncio
import json
import pyautogui
from pynput.keyboard import Key, Listener
import re


applio_app_id = (
    ""  # TODO: ApplioのApp IDをModalダッシュボードで確認して入力。 e.g. "ap-xxxxxxxx"
)
rvc_model_name = ""  # TODO: 学習開始時に指定したモデル名を入力。

logs_volume_name = "applio-logs"
click_interval = 25  # 定期クリックの間隔（秒） container_idle_timeoutの1/2以下に設定
volume_check_interval = 60  # volumeチェックする間隔（秒）

# 学習終了時にApplioが生成するファイル(added~~.index)
FILENAME_TO_CHECK = r".*added.*\.index"


def get_coordinates_on_space():
    """スペースキーが押されたときのマウス座標を取得"""
    coords: list[tuple[float, float]] = []

    def on_press(key):
        if key == Key.space:
            x, y = pyautogui.position()
            coords.append((x, y))
            print(f"記録された座標: ({x}, {y})")
            if len(coords) == 2:  # 2点が記録されたらリスナーを停止
                listener.stop()
                return

    with Listener(on_press=on_press) as listener:
        listener.join()
    return coords


async def check_volume(stop_event: asyncio.Event):
    """
    volume上の{rvc_model_name}ディレクトリに{FILENAME_TO_CHECK}ファイルがあるか定期的に確認し、
    存在したら終了シグナルを送ってApplio自体も停止する。
    """
    while True:
        await asyncio.sleep(volume_check_interval)
        print("volumeをチェックします...")
        dir_to_check = rvc_model_name
        result = asyncio.subprocess.create_subprocess_shell(
            f"modal volume ls --json {logs_volume_name} {dir_to_check}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        process = await result
        stdout, stderr = await process.communicate()

        if stdout:
            ls_result_json = json.loads(stdout.decode("utf-8", errors="replace"))
            for item in ls_result_json:
                if item["Type"] == "file" and re.match(
                    FILENAME_TO_CHECK, item["Filename"]
                ):
                    print(f"{item['Filename']}を検知しました。終了します。")
                    stop_event.set()  # 終了シグナルを送る

                    import subprocess

                    subprocess.run(f"modal app stop {applio_app_id}", shell=True)
                    return
        elif stderr:
            print(stderr.decode("utf-8", errors="replace"))
            return


async def click_loop(points, stop_event: asyncio.Event):
    """指定された座標リストを無限ループでクリックし続ける。終了シグナルが来たらループを抜ける。"""
    while True:
        for point in points:
            pyautogui.click(point)  # 記録された座標でクリック
            print(f"クリック位置: {point}")
            for i in range(click_interval, 0, -1):
                print(
                    f"次のクリックまであと{i}秒... (Ctrl+Cで停止)", end="\r", flush=True
                )
                await asyncio.sleep(1)
                if stop_event.is_set():  # 終了シグナルが来たらループを抜ける
                    return


async def main():
    if not applio_app_id or not rvc_model_name:
        print("applio_app_idとrvc_model_nameを設定してください。")
        return

    print(
        "定期クリックする2地点を指定します。指定したい位置にマウスを移動してスペースキーを押してください。"
    )
    points = get_coordinates_on_space()  # 2点の座標を取得

    if len(points) < 2:
        print("2点の座標を正しく取得できませんでした。")
        return

    stop_event = asyncio.Event()
    click_task = asyncio.create_task(click_loop(points, stop_event))
    check_task = asyncio.create_task(check_volume(stop_event))

    await asyncio.gather(click_task, check_task)


if __name__ == "__main__":
    asyncio.run(main())
