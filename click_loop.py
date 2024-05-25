"""
Modal上でのモデル学習時、定期的にRefreshボタンなどをクリックさせてExecutionを維持するためのツール。
@app.clsでtimeoutを長く設定しても現状1時間きっかりで強制中断されるのでその対策として作成。

Usage:
    1. 監視するスクリーン領域を選択するために、左上の点と右下の点をマウスクリックで指定します。
       ※ "Stop Training & Restart Applio" ボタンの部分を指定する意図で作られています。
    2. 指定した領域のスクリーンショットを定期的に取得し、変化がなければクリックします。
    3. キャプチャ領域の内容が変化した場合、プログラムは終了します。
"""

import time
import cv2
import pyautogui
import numpy as np
from pynput.mouse import Listener, Button

interval = 10  # 定期クリックの間隔（秒）


def get_click_coordinates():
    """マウスクリックの座標を取得"""
    coords: list[tuple[int, int]] = []

    def on_click(x, y, button: Button, pressed: bool):
        if pressed and button == Button.left:
            coords.append((int(x), int(y)))
            return False  # リスナーを停止

    with Listener(on_click=on_click) as listener:
        listener.join()
    return coords[0]


def screen_capture(region: tuple[int, int, int, int]):
    """スクリーンショットを取得し、NumPy配列に変換"""
    image = pyautogui.screenshot(region=region)
    return np.array(image)


def compare_images(img1, img2) -> bool:
    """二つの画像配列が一致するかどうかを比較"""
    return (
        cv2.matchTemplate(np.array(img1), np.array(img2), cv2.TM_CCOEFF_NORMED)[0][0]
        > 0.9
    )


def main():
    print("スクリーンの領域の左上の点でマウスをクリックしてください...")
    x1, y1 = get_click_coordinates()

    print("スクリーンの領域の右下の点でマウスをクリックしてください...")
    x2, y2 = get_click_coordinates()

    region = (
        min(x1, x2),
        min(y1, y2),
        abs(x2 - x1),
        abs(y2 - y1),
    )
    print(f"選択された領域: {region}")

    original_image = screen_capture(region)

    while True:
        for i in range(interval, 0, -1):
            print(f"次のクリックまであと{i}秒 (Ctrl+Cで停止)", end="\r", flush=True)
            time.sleep(1)
        new_image = screen_capture(region)
        if not compare_images(original_image, new_image):
            print("\nキャプチャ領域の内容が変化しました。")
            break
        pyautogui.click()


if __name__ == "__main__":
    main()
