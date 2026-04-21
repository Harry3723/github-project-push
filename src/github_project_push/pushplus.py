from __future__ import annotations

import requests


def chunk_markdown_by_bytes(content: str, max_bytes: int) -> list[str]:
    if len(content.encode("utf-8")) <= max_bytes:
        return [content]

    paragraphs = content.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        candidate = "\n\n".join(current + [paragraph]) if current else paragraph
        if len(candidate.encode("utf-8")) <= max_bytes:
            current.append(paragraph)
            continue
        if current:
            chunks.append("\n\n".join(current))
            current = []
        if len(paragraph.encode("utf-8")) <= max_bytes:
            current = [paragraph]
            continue
        text = paragraph
        start = 0
        while start < len(text):
            end = len(text)
            while len(text[start:end].encode("utf-8")) > max_bytes and end > start:
                end -= 200
            if end <= start:
                end = min(len(text), start + 500)
            chunks.append(text[start:end])
            start = end

    if current:
        chunks.append("\n\n".join(current))
    return chunks


class PushplusSender:
    def __init__(self, token: str | None, topic: str | None, api_url: str, max_bytes: int) -> None:
        self.token = token
        self.topic = topic
        self.api_url = api_url
        self.max_bytes = max_bytes

    def is_available(self) -> bool:
        return bool(self.token)

    def send(self, content: str, title: str) -> bool:
        if not self.token:
            return False
        chunks = chunk_markdown_by_bytes(content, max(1000, self.max_bytes - 1500))
        total = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            chunk_title = f"{title} ({index}/{total})" if total > 1 else title
            payload = {
                "token": self.token,
                "title": chunk_title,
                "content": chunk,
                "template": "markdown",
            }
            if self.topic:
                payload["topic"] = self.topic
            response = requests.post(self.api_url, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            if result.get("code") != 200:
                raise RuntimeError(f"PushPlus returned error: {result}")
        return True
