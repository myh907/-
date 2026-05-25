"""用 Claude API 生成公众号文章内容"""

import anthropic


SYSTEM_PROMPT = """你是一位专业的微信公众号内容创作者。
你的文章风格：标题吸引人、结构清晰（小标题+段落）、语言生动、适合移动端阅读。
输出格式要求：
- 第一行：文章标题（不加任何前缀）
- 第二行：空行
- 第三行开始：正文（支持 HTML，如 <h2>、<p>、<strong>、<br> 等）
- 最后：一句话摘要（以 DIGEST: 开头，单独一行）"""


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
        return self._parse(raw)

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
