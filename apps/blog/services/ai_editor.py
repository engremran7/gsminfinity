
from __future__ import annotations

from typing import Dict

from apps.core import ai_client, ai


def suggest_outline(text: str) -> str:
    prompt = f"Draft a concise outline for a blog post based on: {text}"
    return ai.safe_generate_text(prompt, context="blog_outline")


def rewrite_paragraph(text: str, tone: str = "concise") -> str:
    prompt = f"Rewrite the paragraph in a {tone} tone, preserve meaning:\n{text}"
    return ai.safe_generate_text(prompt, context="blog_rewrite")


def generate_summary(text: str) -> str:
    prompt = f"Summarize the content in 2 sentences:\n{text}"
    return ai.safe_generate_text(prompt, context="blog_summary")


def suggest_tags(text: str) -> Dict:
    return {"suggestions": ai_client.suggest_tags(text, None)}


