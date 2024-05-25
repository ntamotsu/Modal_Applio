"""
Tensorboard appをModal上で起動するスクリプト
"""

import modal


vol = modal.Volume.from_name("applio-logs", create_if_missing=True)

image: modal.Image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "tensorboard"
)

app = modal.App(name="tensorboard_app", image=image)


@app.function(
    concurrency_limit=1,
    volumes={"/root/watch_logs": vol},
)
@modal.wsgi_app()
def tensorboard_app():
    import tensorboard  # type: ignore

    board = tensorboard.program.TensorBoard()
    board.configure(logdir="/root/watch_logs")
    (data_provider, deprecated_multiplexer) = board._make_data_provider()
    wsgi_app = tensorboard.backend.application.TensorBoardWSGIApp(
        board.flags,
        board.plugin_loaders,
        data_provider,
        board.assets_zip_provider,
        deprecated_multiplexer,
    )
    return wsgi_app
