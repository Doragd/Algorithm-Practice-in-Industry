import os
import requests
import time
import json
from abc import ABC, abstractmethod

class ModelClient(ABC):
    @abstractmethod
    def translate(self, source, system_prompt, temperature):
        pass

    @abstractmethod
    def call(self, source, system_prompt, temperature):
        pass

    def retry_call(self, source, system_prompt, temperature, attempts=3, base_delay=60):
        for attempt in range(attempts):
            try:
                return self.call(source, system_prompt, temperature)
            except requests.exceptions.RequestException as e:
                print(f"请求失败（尝试 {attempt + 1}/{attempts}）：", e)
            except requests.exceptions.HTTPError as e:
                print(f"HTTP错误（尝试 {attempt + 1}/{attempts}）：", e)
            except requests.exceptions.ConnectionError as e:
                print(f"连接错误（尝试 {attempt + 1}/{attempts}）：", e)
            except requests.exceptions.Timeout as e:
                print(f"请求超时（尝试 {attempt + 1}/{attempts}）：", e)
            except Exception as e:
                print(f"未知错误（尝试 {attempt + 1}/{attempts}）：", e)
            if attempt < attempts - 1:
                time.sleep(base_delay * (attempt + 1))
        return None

class DeepSeekClient(ModelClient):
    def __init__(self, api_key, base_url):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def call(self, source, system_prompt=None, temperature=1.3):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                system_prompt,
                {"role": "user", "content": source}
            ],
            temperature=temperature,
            stream=False
        )
        ret = response.choices[0].message.content.strip()
        return ret

    def translate(self, source, system_prompt=None, temperature=1.3):
        translations = []
        for s in source:
            response = self.retry_call(s, system_prompt, temperature)
            translations.append(response if response is not None else '')
        return translations

class CaiyunClient(ModelClient):
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
    
    def call(self, source, system_prompt=None, temperature=1.3):

        payload = {
            "source": source,
            "trans_type": "en2zh",
            "request_id": "demo",
            "detect": True,
        }

        headers = {
            "content-type": "application/json",
            "x-authorization": "token " + self.api_key,
        }

        response = requests.post(self.base_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return json.loads(response.text)["target"]

    def translate(self, source, system_prompt=None, temperature=1.3):
        ret = self.retry_call(source, system_prompt, temperature)
        if ret is None:
            return ['' for _ in source]
        return ret

def init_model_client():
    model_type = os.environ.get("MODEL_TYPE", "DeepSeek")
    if model_type == "DeepSeek":
        api_key = os.environ.get("DEEPSEEK_API_KEY", None)
        base_url = "https://api.deepseek.com"
        return DeepSeekClient(api_key=api_key, base_url=base_url)
    elif model_type == "Caiyun":
        api_key = os.environ.get("CAIYUN_TOKEN", None)
        base_url = "http://api.interpreter.caiyunai.com/v1/translator"
        return CaiyunClient(api_key=api_key, base_url=base_url)
    else:
        raise ValueError(f"未定义的模型类型: {model_type}")

model_client = init_model_client()

def translate(source):
    system_prompt = {
        "role": "system",
        "content": "你是一位专业的翻译人员，擅长在人工智能领域内进行高质量的英文到中文翻译。你将会接收到一篇涉及自然语言处理（NLP）、信息检索（IR）、计算机视觉（CV）等方向的英文论文摘要。请准确翻译摘要内容，确保所有专业术语和技术细节得到正确的表达。"
    }

    return model_client.translate(source, system_prompt=system_prompt, temperature=1.3)
