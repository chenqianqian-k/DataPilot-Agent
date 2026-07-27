import json
from functools import lru_cache
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.core.config import Settings, get_settings


class LLMServiceError(RuntimeError):
    """
    LLM调用失败时统一抛出的业务异常。
    """


class LLMClient:
    """
    DeepSeek/OpenAI兼容模型客户端。

    负责：
    1. 普通文本对话
    2. JSON结构化结果生成
    3. API异常统一处理
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        self.client = OpenAI(
            api_key=settings.deepseek_api_key.get_secret_value(),
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )

    def chat(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        调用模型并返回文本结果。
        """

        if not user_prompt.strip():
            raise ValueError("user_prompt不能为空")

        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt.strip(),
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_prompt.strip(),
            }
        )

        request_temperature = (
            self.settings.llm_temperature
            if temperature is None
            else temperature
        )

        request_max_tokens = (
            self.settings.llm_max_tokens
            if max_tokens is None
            else max_tokens
        )

        try:
            response = self.client.chat.completions.create(
                model=self.settings.deepseek_model,
                messages=messages,
                temperature=request_temperature,
                max_tokens=request_max_tokens,
                stream=False,
            )
        except APITimeoutError as exc:
            raise LLMServiceError("模型请求超时，请稍后重试") from exc
        except RateLimitError as exc:
            raise LLMServiceError("模型请求频率过高或额度不足") from exc
        except APIConnectionError as exc:
            raise LLMServiceError("无法连接到模型服务，请检查网络和Base URL") from exc
        except APIStatusError as exc:
            raise LLMServiceError(
                f"模型服务返回错误，状态码：{exc.status_code}"
            ) from exc
        except Exception as exc:
            raise LLMServiceError(
                f"模型调用出现未知错误：{type(exc).__name__}"
            ) from exc

        if not response.choices:
            raise LLMServiceError("模型未返回任何候选结果")

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise LLMServiceError("模型返回内容为空")

        return content.strip()

    def chat_json(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | list[Any]:
        """
        要求模型返回JSON，并将结果解析为Python对象。

        该方法不依赖特定服务商的response_format参数，
        因此兼容DeepSeek及多数OpenAI兼容接口。
        """

        json_instruction = """
请严格以合法JSON格式输出，不要输出Markdown代码块，
不要在JSON之前或之后添加解释文字。
""".strip()

        enhanced_system_prompt = (
            f"{system_prompt.strip()}\n\n{json_instruction}"
            if system_prompt
            else json_instruction
        )

        content = self.chat(
            user_prompt=user_prompt,
            system_prompt=enhanced_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        cleaned_content = self._remove_markdown_code_fence(content)

        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            extracted_json = self._extract_json_fragment(cleaned_content)

            if extracted_json is None:
                raise LLMServiceError(
                    "模型未返回可以识别的JSON结构"
                )

            try:
                return json.loads(extracted_json)
            except json.JSONDecodeError as exc:
                raise LLMServiceError(
                    f"模型返回的JSON解析失败：{exc.msg}"
                ) from exc

    @staticmethod
    def _remove_markdown_code_fence(content: str) -> str:
        """
        移除模型偶尔返回的Markdown代码块标记。
        """

        cleaned = content.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        return cleaned

    @staticmethod
    def _extract_json_fragment(content: str) -> str | None:
        """
        从包含额外说明的文本中提取最外层JSON对象或数组。
        """

        object_start = content.find("{")
        object_end = content.rfind("}")

        array_start = content.find("[")
        array_end = content.rfind("]")

        object_fragment = None
        array_fragment = None

        if object_start != -1 and object_end > object_start:
            object_fragment = content[object_start : object_end + 1]

        if array_start != -1 and array_end > array_start:
            array_fragment = content[array_start : array_end + 1]

        if object_fragment is None:
            return array_fragment

        if array_fragment is None:
            return object_fragment

        if object_start < array_start:
            return object_fragment

        return array_fragment


@lru_cache
def get_llm_client() -> LLMClient:
    """
    返回全局缓存的LLM客户端。
    """

    return LLMClient(settings=get_settings())


llm_client = get_llm_client()