from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# DataPilot项目根目录：
# /root/autodl-tmp/DataPilot
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    DataPilot统一配置。

    配置优先从系统环境变量读取，其次从项目根目录下的.env读取。
    """

    # =========================
    # Application
    # =========================
    app_name: str = Field(default="DataPilot", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")

    # =========================
    # FastAPI
    # =========================
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=6016, alias="APP_PORT")

    # =========================
    # Streamlit
    # =========================
    streamlit_host: str = Field(
        default="0.0.0.0",
        alias="STREAMLIT_HOST",
    )
    streamlit_port: int = Field(
        default=6018,
        alias="STREAMLIT_PORT",
    )

    # =========================
    # Data directories
    # =========================
    upload_dir: str = Field(
        default="data/uploads",
        alias="UPLOAD_DIR",
    )
    output_dir: str = Field(
        default="data/outputs",
        alias="OUTPUT_DIR",
    )
    max_upload_size_mb: int = Field(
        default=50,
        alias="MAX_UPLOAD_SIZE_MB",
    )

    # =========================
    # DeepSeek / OpenAI-compatible API
    # =========================
    deepseek_api_key: SecretStr = Field(alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(alias="DEEPSEEK_MODEL")

    # =========================
    # LLM request settings
    # =========================
    llm_timeout: float = Field(default=120.0, alias="LLM_TIMEOUT")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    llm_temperature: float = Field(
        default=0.0,
        alias="LLM_TEMPERATURE",
    )
    llm_max_tokens: int = Field(
        default=4096,
        alias="LLM_MAX_TOKENS",
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def upload_path(self) -> Path:
        """
        返回上传目录的绝对路径。
        """
        path = Path(self.upload_dir)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        return path.resolve()

    @property
    def output_path(self) -> Path:
        """
        返回分析结果目录的绝对路径。
        """
        path = Path(self.output_dir)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        return path.resolve()

    def create_runtime_directories(self) -> None:
        """
        创建项目运行过程中需要使用的数据目录。
        """
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    获取全局配置对象。

    使用缓存避免每次调用时重复读取.env文件。
    """
    return Settings()


settings = get_settings()
settings.create_runtime_directories()