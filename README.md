# 概要
ModalのサーバーレスGPUを使ってApplioを動かすだけ。
- [Modal](https://modal.com/)
- [Applio](https://docs.applio.org/)

# セットアップ
1. 事前にModalのアカウントを作成しておく。
2. 以下のコマンドを順次実行する。
```
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m modal setup
```
3. ブラウザでModalのページが開くので画面の指示に従ってトークンを発行する。

# Applio起動
1. 学習を行う場合は`applio_asgiapp.py`の`local_datasets_dir`に「音声データセットが格納されているローカルのディレクトリのパス」を入力する。  
(例: "/Users/username/wav_datasets")  
2. 使いたい事前学習モデルがある場合は`custom_pretrained_urls`を編集する。  
3. 以下のコマンドを実行する。  
```
modal serve applio_asgiapp.py
```
もしくは
```
modal deploy applio_asgiapp.py
```
4. しばらく待つとコンソールとModalダッシュボードにURL (https://~~~.modal.run) が表示されるのでどちらかからアクセスする。(この時点ではまだApplioは開けない)
5. さらに待つとコンソールとModalダッシュボードLogsにgradio public URLが表示されるのでどちらかからアクセスする。  
![pic1](doc/gradio_public_url_in_console.png)  
↑コンソール  
![pic2](doc/gradio_public_url_in_modal_logs.png)  
↑ModalダッシュボードのLogs  

# Tensorboard起動(学習状況の可視化)
```
modal serve logs_tensorboard.py
```
もしくは
```
modal deploy logs_tensorboard.py
```
コンソールとModalダッシュボードでURLが表示されるのでどちらかからアクセス。  

# 学習結果の保存
- Trainタブでの各工程(Prepocess Dataset、Feature Extraction、Start Training、Train Feature Index)の結果はModalのVolume機能によって逐一保存される。
- これにより、特に意識しなくても学習の中断と再開が可能。
- Volumeの中身はダッシュボードから確認できる。
![pic3](doc/modal_storage_dashboard.png)  
- なお現在、ダッシュボードでは閲覧のみ可能でありファイルのダウンロードなどはCLIから行う必要がある。

# その他のファイルについて
`applio_webserver.py`と`click_loop.py`は、`@modal.web_server`を用いたApplioの起動と学習に必要なファイル。  
ただの遠回りしてあれこれやった残骸なので無視していいです... 一応使い方は`click_loop.py`のトップコメントに書いてあります。  
