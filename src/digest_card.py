"""把结构化日报渲染成两种产物：

1. render_poster(digest) -> 独立 HTML 海报，深色渐变、卡片式，
   浏览器打开后可直接截长图转发（小红书 / 朋友圈 / X）。
2. render_wechat(digest) -> 微信公众号兼容的 inline-style HTML 片段，
   可直接走现有发布流程发到公众号。
"""

import datetime
import html


def _fmt_date(iso: str) -> tuple[str, str]:
    """返回 (主日期, 星期) 两段展示文本。"""
    try:
        d = datetime.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso, ""
    weeks = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{d:%Y.%m.%d}", weeks[d.weekday()]


def _esc(s: str) -> str:
    return html.escape(str(s or ""))


# ── 1. 独立海报（可截图转发） ────────────────────────────────────────────────

_POSTER_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #0b0d12;
  font-family: -apple-system, 'PingFang SC', 'Helvetica Neue', 'Microsoft YaHei', sans-serif;
  display: flex; justify-content: center; padding: 40px 16px;
}
.card {
  width: 100%; max-width: 720px;
  background: radial-gradient(1200px 400px at 0% 0%, #1b2a4a 0%, transparent 60%),
              linear-gradient(160deg, #111726 0%, #0c0f18 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 28px; overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,0.55);
}
.hd { padding: 40px 40px 28px; position: relative; }
.hd::after {
  content: ''; position: absolute; left: 40px; right: 40px; bottom: 0; height: 1px;
  background: linear-gradient(90deg, rgba(94,234,212,0.6), rgba(94,234,212,0) 70%);
}
.brand { display: flex; align-items: center; gap: 12px; }
.logo {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg, #5eead4, #3b82f6);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; color: #0b0d12;
}
.brand-txt .t1 { color: #fff; font-size: 22px; font-weight: 800; letter-spacing: 1px; }
.brand-txt .t2 { color: #5eead4; font-size: 12px; letter-spacing: 3px; margin-top: 2px; }
.date-row { display: flex; align-items: baseline; gap: 12px; margin-top: 22px; }
.date-row .d { color: #fff; font-size: 30px; font-weight: 800; }
.date-row .w { color: #8a93a6; font-size: 15px; }
.date-row .ed {
  margin-left: auto; color: #5eead4; font-size: 12px;
  border: 1px solid rgba(94,234,212,0.4); border-radius: 999px; padding: 4px 12px;
}
.intro {
  margin: 26px 40px 6px; padding: 18px 20px;
  background: rgba(94,234,212,0.06); border-left: 3px solid #5eead4; border-radius: 0 12px 12px 0;
  color: #e6edf6; font-size: 16px; line-height: 1.7;
}
.list { padding: 18px 40px 8px; }
.item { display: flex; gap: 18px; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.06); }
.item:first-child { border-top: none; }
.num {
  flex: none; width: 30px; color: #3b82f6; font-size: 22px; font-weight: 800;
  font-variant-numeric: tabular-nums; line-height: 1.3;
}
.body { flex: 1; min-width: 0; }
.tag {
  display: inline-block; font-size: 11px; color: #5eead4;
  background: rgba(59,130,246,0.14); border-radius: 6px; padding: 2px 8px; margin-bottom: 8px;
}
.title { color: #fff; font-size: 19px; font-weight: 700; line-height: 1.4; }
.take { color: #aeb6c4; font-size: 14px; margin-top: 8px; line-height: 1.6; }
.why { color: #6f7889; font-size: 13px; margin-top: 8px; line-height: 1.6; }
.why b { color: #8a93a6; font-weight: 600; }
.ft {
  margin: 14px 40px 36px; padding-top: 22px; border-top: 1px solid rgba(255,255,255,0.06);
  display: flex; align-items: center; justify-content: space-between;
}
.closing { color: #cdd5e1; font-size: 14px; line-height: 1.6; max-width: 78%; }
.by { color: #4a5366; font-size: 12px; text-align: right; }
.by b { color: #5eead4; }
"""


def render_poster(digest: dict, title: str = "AI 圈日报") -> str:
    """生成自包含的 HTML 海报字符串。"""
    d, w = _fmt_date(digest.get("date", ""))

    items_html = []
    for i, it in enumerate(digest.get("items", []), 1):
        items_html.append(
            f'''      <div class="item">
        <div class="num">{i:02d}</div>
        <div class="body">
          <span class="tag">{_esc(it.get("tag", ""))}</span>
          <div class="title">{_esc(it.get("title", ""))}</div>
          <div class="take">{_esc(it.get("take", ""))}</div>
          <div class="why"><b>为什么重要 · </b>{_esc(it.get("why", ""))}</div>
        </div>
      </div>'''
        )
    items_block = "\n".join(items_html)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} · {d}</title>
<style>{_POSTER_CSS}</style>
</head>
<body>
  <div class="card">
    <div class="hd">
      <div class="brand">
        <div class="logo">AI</div>
        <div class="brand-txt">
          <div class="t1">{_esc(title)}</div>
          <div class="t2">DAILY AI BRIEFING</div>
        </div>
      </div>
      <div class="date-row">
        <span class="d">{d}</span>
        <span class="w">{w}</span>
        <span class="ed">每日精选 · {len(digest.get("items", []))} 条</span>
      </div>
    </div>
    <div class="intro">{_esc(digest.get("intro", ""))}</div>
    <div class="list">
{items_block}
    </div>
    <div class="ft">
      <div class="closing">{_esc(digest.get("closing", ""))}</div>
      <div class="by">由 <b>Claude</b> 生成<br>AI 圈日报机器人</div>
    </div>
  </div>
</body>
</html>'''


# ── 2. 微信公众号 inline-style 版（可直接发布） ──────────────────────────────

_WX_SECTION = "font-family:-apple-system,'PingFang SC',sans-serif;font-size:16px;color:#333;line-height:1.8;padding:0 4px;"


def render_wechat(digest: dict) -> str:
    """生成微信兼容的 inline-style HTML 片段（公众号会过滤外部 CSS）。"""
    d, w = _fmt_date(digest.get("date", ""))
    parts = [f'<section style="{_WX_SECTION}">']

    parts.append(
        f'<p style="text-align:center;color:#888;font-size:13px;margin:0 0 6px;">'
        f'AI 圈日报 · {d} {w}</p>'
    )
    if digest.get("intro"):
        parts.append(
            f'<blockquote style="margin:16px 0;padding:12px 16px;background:#f5f7fa;'
            f'border-left:4px solid #3b82f6;color:#444;font-size:15px;">'
            f'{_esc(digest["intro"])}</blockquote>'
        )

    for i, it in enumerate(digest.get("items", []), 1):
        parts.append(
            f'<h2 style="font-size:19px;font-weight:bold;color:#1a1a1a;margin:26px 0 8px;">'
            f'<span style="color:#3b82f6;">{i:02d}</span>&nbsp;&nbsp;'
            f'<span style="font-size:12px;color:#fff;background:#3b82f6;border-radius:5px;'
            f'padding:2px 8px;vertical-align:middle;">{_esc(it.get("tag", ""))}</span>&nbsp;'
            f'{_esc(it.get("title", ""))}</h2>'
        )
        parts.append(
            f'<p style="margin:8px 0;color:#333;">{_esc(it.get("take", ""))}</p>'
        )
        parts.append(
            f'<p style="margin:6px 0 0;color:#888;font-size:14px;">'
            f'<strong style="color:#3b82f6;">为什么重要 · </strong>{_esc(it.get("why", ""))}</p>'
        )

    if digest.get("closing"):
        parts.append(
            f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0;"/>'
            f'<p style="color:#555;font-size:15px;">{_esc(digest["closing"])}</p>'
        )
    parts.append(
        '<p style="text-align:center;color:#bbb;font-size:12px;margin-top:24px;">'
        '本文由 Claude 自动生成 · AI 圈日报机器人</p>'
    )
    parts.append("</section>")
    return "\n".join(parts)


def digest_to_article(digest: dict, title: str | None = None) -> dict:
    """组装成可投递给 WeChatClient.add_draft 的文章 dict 所需字段。"""
    d, _ = _fmt_date(digest.get("date", ""))
    return {
        "title": title or f"AI 圈日报 | {d}",
        "digest": digest.get("intro", "")[:120],
        "content": render_wechat(digest),
    }
