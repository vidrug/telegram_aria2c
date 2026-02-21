from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    allowed_user_id: int
    aria2_rpc_url: str = "ws://aria2:6800/jsonrpc"
    aria2_rpc_secret: str = ""
    download_dir: str = "/downloads"
    usb_mount_path: str = "/mnt"
    progress_update_interval: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
