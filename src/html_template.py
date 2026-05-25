"""将纯文本/简单 HTML 转为微信公众号兼容的 inline-style HTML

微信会过滤外部 CSS，所有样式必须内联。
"""

import re


# 全局容器样式
_BODY_STYLE = (
    "font-family: -apple-system, 'PingFang SC', 'Helvetica Neue', sans-serif;"
    "font-size: 17px; color: #333; line-height: 1.8;"
    "padding: 0 16px; word-break: break-word;"
)

_H2_STYLE = (
    "font-size: 20px; font-weight: bold; color: #1a1a1a;"
    "margin: 28px 0 12px; padding-left: 10px;"
    "border-left: 4px solid #07C160;"
)

_H3_STYLE = (
    "font-size: 18px; font-weight: bold; color: #333;"
    "margin: 20px 0 8px;"
)

_P_STYLE = (
    "margin: 12px 0; text-indent: 2em;"
)

_STRONG_STYLE = "color: #07C160; font-weight: bold;"

_BLOCKQUOTE_STYLE = (
    "margin: 16px 0; padding: 12px 16px;"
    "background: #f5f5f5; border-left: 4px solid #07C160;"
    "color: #666; font-size: 15px;"
)

_HR_STYLE = (
    "border: none; border-top: 1px solid #e8e8e8; margin: 24px 0;"
)

_UL_STYLE = "margin: 12px 0; padding-left: 1.5em;"
_LI_STYLE = "margin: 6px 0;"


def render(content: str) -> str:
    """把 Claude 输出的 HTML 包装成微信兼容的 inline-style 版本。"""
    html = content.strip()

    # 替换标签，注入 inline style
    html = re.sub(r"<h2[^>]*>", f'<h2 style="{_H2_STYLE}">', html)
    html = re.sub(r"<h3[^>]*>", f'<h3 style="{_H3_STYLE}">', html)
    html = re.sub(r"<p[^>]*>", f'<p style="{_P_STYLE}">', html)
    html = re.sub(r"<strong[^>]*>", f'<strong style="{_STRONG_STYLE}">', html)
    html = re.sub(r"<blockquote[^>]*>", f'<blockquote style="{_BLOCKQUOTE_STYLE}">', html)
    html = re.sub(r"<hr\s*/?>", f'<hr style="{_HR_STYLE}"/>', html)
    html = re.sub(r"<ul[^>]*>", f'<ul style="{_UL_STYLE}">', html)
    html = re.sub(r"<li[^>]*>", f'<li style="{_LI_STYLE}">', html)

    # 未被 <p> 包裹的纯文本段落自动补 <p>
    # （Claude 有时输出裸文本行）
    lines = html.split("\n")
    wrapped = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^<(h[1-6]|p |ul|ol|li|blockquote|hr|section|div|br)", stripped, re.I):
            wrapped.append(stripped)
        else:
            wrapped.append(f'<p style="{_P_STYLE}">{stripped}</p>')
    html = "\n".join(wrapped)

    return f'<section style="{_BODY_STYLE}">\n{html}\n</section>'
