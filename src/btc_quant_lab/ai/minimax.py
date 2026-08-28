import httpx

from btc_quant_lab.config import settings


class MiniMaxClient:
    def __init__(self):
        if not settings.minimax_api_key:
            raise RuntimeError("MINIMAX_API_KEY no está configurada")

    async def complete(self, system: str, user: str) -> str:
        payload = {
            "model": settings.minimax_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(settings.minimax_base_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        if "reply" in data:
            return data["reply"]
        return str(data)
