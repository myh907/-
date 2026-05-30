"""AI 圈日报：把每天的 AI 热点交给 Claude，产出结构化、有态度的日报。

核心产物是一个结构化 dict（见 generate 的返回），再由 digest_card.py
渲染成可截图转发的海报，或微信公众号兼容的 inline HTML。

无 ANTHROPIC_API_KEY 时可用 demo_digest() 跑出示例效果。
"""

import datetime
import json
import re

import anthropic


SYSTEM_PROMPT = """你是「AI 圈日报」的主编，风格犀利、有观点、不堆砌术语。
我会给你今天 AI 圈的若干条原始热点，你要把它们整理成一份精炼的日报。

只输出一个 JSON 对象（不要任何额外说明、不要 markdown 代码块），结构如下：
{
  "intro": "一句卷首语，点出今天 AI 圈最值得关注的主线，20-40 字，有态度",
  "items": [
    {
      "tag": "分类，2-4字，如：模型/产品/开源/资本/争议/研究",
      "title": "精炼后的标题，15 字以内，吸引人",
      "take": "一句话锐评，30 字以内，带主编个人观点，可以毒舌可以兴奋",
      "why": "为什么重要，40 字以内，说清楚对从业者/行业的实际影响"
    }
  ],
  "closing": "一句收尾，可以是趋势判断或明日看点，20-30 字"
}

要求：
- items 数量与我给的热点条数一致（最多 6 条），按重要性从高到低排序
- 语言中文，口语化、有网感，但不浮夸、不编造事实
- 严格输出合法 JSON，所有字符串用双引号"""


class DailyDigest:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(
            api_key=api_key,
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        self.model = model

    def generate(self, items: list[str], date: datetime.date | None = None) -> dict:
        """把原始热点列表整理成结构化日报。

        items: 每条是一句话原始热点/新闻。
        返回 {date, intro, items:[{tag,title,take,why}], closing}
        """
        if not items:
            raise ValueError("热点列表为空，请在 daily_sources.txt 中填写，或用 --demo 体验")

        date = date or datetime.date.today()
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(items, 1))
        user_prompt = f"今天是 {date:%Y年%m月%d日}，以下是今天的 AI 圈热点：\n{numbered}"

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        data = self._parse(message.content[0].text)
        data["date"] = date.isoformat()
        return data

    @staticmethod
    def _parse(raw: str) -> dict:
        """从模型输出中提取 JSON，容忍 ```json 代码块包裹。"""
        text = raw.strip()
        # 去掉可能的 markdown 代码块围栏
        fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, re.S)
        if fence:
            text = fence.group(1)
        # 退一步：截取第一个 { 到最后一个 }
        if not text.startswith("{"):
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"模型未返回合法 JSON：{e}\n原始输出：\n{raw[:500]}")

        data.setdefault("intro", "")
        data.setdefault("items", [])
        data.setdefault("closing", "")
        return data


def load_sources(path: str) -> list[str]:
    """从文本文件读取原始热点，每行一条，# 开头为注释。"""
    import os

    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        ]


def demo_digest(date: datetime.date | None = None) -> dict:
    """离线示例日报，无需 API key，用于快速预览效果。"""
    date = date or datetime.date.today()
    return {
        "date": date.isoformat(),
        "intro": "模型卷参数、Agent 卷落地，今天 AI 圈最大的变量是「便宜」。",
        "items": [
            {
                "tag": "模型",
                "title": "新一代旗舰模型把价格打下来了",
                "take": "性能不输上一代，价格腰斩——这才是真·普惠。",
                "why": "推理成本直接决定 AI 产品的毛利，降价会逼着一批套壳产品重做账。",
            },
            {
                "tag": "Agent",
                "title": "编码 Agent 拿下真实开源 issue",
                "take": "从「能写代码」到「能交活」，门槛越过了一道坎。",
                "why": "意味着初级重复性工程任务开始可被自动化，团队配置要重新算。",
            },
            {
                "tag": "开源",
                "title": "又一个高质量开源模型上线",
                "take": "闭源还在挤牙膏，开源已经追到了身后半个身位。",
                "why": "对中小团队是利好：本地部署 + 可控成本，数据也不用出门。",
            },
            {
                "tag": "资本",
                "title": "AI 基础设施赛道又一笔大额融资",
                "take": "卖铲子的永远先赚钱，这轮淘金热依旧。",
                "why": "算力与数据管线仍是瓶颈，资金流向能看出下一个卡脖子环节。",
            },
            {
                "tag": "争议",
                "title": "AI 生成内容版权再起争论",
                "take": "技术跑得太快，规则还在系鞋带。",
                "why": "合规边界没定清楚之前，商业化的每一步都带着不确定性。",
            },
        ],
        "closing": "便宜 + 可用 + 可控，三条线交汇处，就是明年的产品机会。",
    }
