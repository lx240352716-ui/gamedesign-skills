# -*- coding: utf-8 -*-
"""
LLM 抽象层 — OpenAI 兼容模式，一套代码支持多家模型。

支持的模型提供商（只需改 .env 配置）：
- 通义千问: base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
- DeepSeek:  base_url=https://api.deepseek.com
- OpenAI:    base_url=https://api.openai.com/v1
- 本地 Ollama: base_url=http://localhost:11434/v1

Usage:
    from llm_client import llm
    response = llm.chat("你是数值策划", "帮我分析这个需求")
"""

import os
import json
import sys

# 加载 .env
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCES_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..'))
BASE_DIR = os.path.normpath(os.path.join(REFERENCES_DIR, '..'))

_env_loaded = False

def _load_env():
    """从 .env 加载配置到 os.environ"""
    global _env_loaded
    if _env_loaded:
        return
    # 优先项目根目录，兜底 references/
    for candidate in [os.path.join(BASE_DIR, '.env'), os.path.join(REFERENCES_DIR, '.env')]:
        if os.path.exists(candidate):
            with open(candidate, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k, v = k.strip(), v.strip()
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            break
    _env_loaded = True


class LLMClient:
    """OpenAI 兼容的 LLM 客户端。"""

    # [DISABLED] 外部 API 调用已禁用，设 LLM_ENABLED=true 可恢复
    DISABLED_MSG = "[i] LLM API disabled (LLM_ENABLED=false in .env)"

    def __init__(self):
        _load_env()
        self._client = None
        self.enabled = os.environ.get('LLM_ENABLED', 'false').lower() == 'true'
        self.model = os.environ.get('LLM_MODEL', 'qwen-plus')
        self.base_url = os.environ.get(
            'LLM_BASE_URL',
            'https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
        self.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        self.temperature = float(os.environ.get('LLM_TEMPERATURE', '0.7'))
        self.max_tokens = int(os.environ.get('LLM_MAX_TOKENS', '4096'))
        if not self.enabled:
            print(self.DISABLED_MSG)

    @property
    def client(self):
        """懒加载 OpenAI 客户端。"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                print("[ERR] openai not installed: pip install openai>=1.0")
                sys.exit(1)
            if not self.api_key:
                print("[ERR] DASHSCOPE_API_KEY not set in .env")
                sys.exit(1)

            # GLM (智谱) API 需要 JWT 认证
            actual_key = self.api_key
            if 'bigmodel.cn' in self.base_url:
                actual_key = self._generate_glm_jwt(self.api_key)

            self._client = OpenAI(
                api_key=actual_key,
                base_url=self.base_url,
            )
        return self._client

    @staticmethod
    def _generate_glm_jwt(api_key: str) -> str:
        """将智谱 API Key ({id}.{secret}) 转为 JWT token。"""
        try:
            import jwt
            import time
            parts = api_key.split('.')
            if len(parts) != 2:
                return api_key  # 不是 GLM 格式，原样返回
            key_id, secret = parts
            payload = {
                "api_key": key_id,
                "exp": int(time.time()) + 3600,  # 1 小时有效
                "timestamp": int(time.time()),
            }
            token = jwt.encode(payload, secret, algorithm="HS256",
                               headers={"alg": "HS256", "sign_type": "SIGN"})
            return token
        except ImportError:
            print("[WARN] GLM requires PyJWT: pip install pyjwt")
            return api_key

    def chat(self, system_prompt: str, user_message: str,
             temperature: float = None, max_tokens: int = None,
             json_mode: bool = False) -> str:
        """发送对话请求，返回 LLM 回复文本。"""
        if not self.enabled:
            return self.DISABLED_MSG

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    def chat_with_history(self, system_prompt: str,
                          messages: list,
                          temperature: float = None) -> str:
        """带历史记录的多轮对话。"""
        if not self.enabled:
            return self.DISABLED_MSG

        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content

    def chat_json(self, system_prompt: str, user_message: str) -> dict:
        """对话并解析 JSON 返回值。"""
        if not self.enabled:
            return {"disabled": True, "message": self.DISABLED_MSG}

        text = self.chat(system_prompt, user_message, json_mode=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # 尝试从 markdown 代码块中提取 JSON
            import re
            m = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
            return {"raw": text, "error": str(e)}


# ── 全局单例 ──
llm = LLMClient()
