"""用 Claude API 生成公众号文章内容"""

import anthropic
from src.html_template import render as render_html


SYSTEM_PROMPT = """你是一位专业的微信公众号内容创作者。
你的文章风格：标题吸引人、结构清晰（小标题+段落）、语言生动、适合移动端阅读。
输出格式要求：
- 第一行：文章标题（不加任何前缀）
- 第二行：空行
- 第三行开始：正文（使用 HTML 标签：<h2> 小标题、<p> 段落、<strong> 加粗、<blockquote> 引用、<ul><li> 列表）
- 最后：一句话摘要（以 DIGEST: 开头，单独一行）

注意：正文只输出 HTML 片段，不要包含 <html>/<body>/<style> 等外层标签。"""


class ContentGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(
            api_key=api_key,
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )

    def generate(self, topic: str, extra_instructions: str = "") -> dict:
        """
        生成一篇公众号文章。
        返回 {"title": str, "content": str, "digest": str}
        """
        user_prompt = f"请写一篇关于「{topic}」的公众号文章。"
        if extra_instructions:
            user_prompt += f"\n额外要求：{extra_instructions}"

        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text
        result = self._parse(raw)
        result["content"] = render_html(result["content"])
        return result

    def generate_batch(self, topics: list[str]) -> list[dict]:
        """批量生成多篇文章"""
        return [self.generate(topic) for topic in topics]

    @staticmethod
    def _parse(raw: str) -> dict:
        lines = raw.strip().splitlines()
        title = lines[0].strip()

        digest = ""
        content_lines = []
        for line in lines[1:]:
            if line.startswith("DIGEST:"):
                digest = line[len("DIGEST:"):].strip()
            else:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()
        return {"title": title, "content": content, "digest": digest}
