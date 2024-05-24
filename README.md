# セットアップ
```
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python -m modal setup
```
ブラウザでModalのページが開くので画面の指示に従ってトークンを発行する。

# 実行
applio.pyの`local_datasets_dir`にローカルの音声データセットが格納されているディレクトリのパスを入力してから以下を実行する。
```
modal serve applio.py
(もしくは modal deploy applio.py)
```
コンソールとModalダッシュボードでURLが表示されるのでどちらかからアクセス。

# Tensorboard起動
```
modal serve logs_tensorboard.py
(もしくは modal deploy logs_tensorboard.py)
```
コンソールとModalダッシュボードでURLが表示されるのでどちらかからアクセス。

# 自動定期クリックツール起動
Applioで時間のかかる処理(Dataset Processing、Feature Extraction、Start training)を行う際に、定期的にRefreshボタンなどをクリックさせてセッションを維持するためのツール。
```
python click_loop.py
```
