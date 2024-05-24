"""
Applioで時間のかかる処理を行う際に、定期的にRefreshボタンなどをクリックさせてセッションを維持するためのツール。
"""

import pyautogui
import time
import signal
import sys

# クリック間隔(秒)を設定
interval = 40


# Ctrl+Cが押されたときのハンドラを定義
def signal_handler(sig, frame):
    print("\nプログラムが中断されました。")
    sys.exit(0)


# SIGINT (Ctrl+C) シグナルを捕捉
signal.signal(signal.SIGINT, signal_handler)

while True:
    # 次のクリックまでの時間を表示
    for i in range(interval, 0, -1):
        print(f"次のクリックまであと{i}秒 (Ctrl+Cで停止)", end="\r", flush=True)
        time.sleep(1)
    pyautogui.click()
