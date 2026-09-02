import json
import urllib.request
from typing import List, Dict, Optional


class LLMClient:
    """
    Cliente mínimo para llama.cpp server.
    No sabe nada de PDFs, IBANs ni abogados. Solo habla HTTP.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            req = urllib.request.Request(
                f"{self.base_url}/health",
                method="GET",
                headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._available = resp.status == 200
        except Exception:
            self._available = False
        return self._available

    def chat(self, messages: List[Dict], temperature: float = 0.2,
             max_tokens: int = 512) -> Optional[str]:
        """
        Envía mensajes al endpoint /v1/chat/completions.
        Devuelve el texto de la respuesta o None si falla cualquier cosa.
        """
        if not self.is_available():
            return None

        payload = json.dumps({
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "stop": ["<|im_end|>", "Usuario:", "Human:", "Assistant:"]
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None