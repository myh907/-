"""把结构化日报直接渲染成 PNG 分享图（无需浏览器）。

用 Pillow 手绘，配色与 digest_card.render_poster 的网页海报保持一致，
方便在不方便截图的场景下直接产出可转发的图片。
"""

import datetime
import os

from PIL import Image, ImageDraw, ImageFont


# ── 字体 ────────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def _font_path() -> str:
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("未找到可用的中文字体，请安装 wqy-zenhei 或 Noto Sans CJK")


# ── 配色（与网页海报一致） ────────────────────────────────────────────────────
BG_TOP = (27, 42, 74)       # 左上角微光
BG_BASE = (12, 15, 24)      # 主背景
CARD_BORDER = (40, 48, 66)
TEAL = (94, 234, 212)
BLUE = (59, 130, 246)
WHITE = (255, 255, 255)
GREY = (174, 182, 196)
DGREY = (111, 120, 137)
MUTE = (138, 147, 166)

W = 760
PAD = 48
WEEKS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _fmt_date(iso: str):
    try:
        d = datetime.date.fromisoformat(iso)
        return f"{d:%Y.%m.%d}", WEEKS[d.weekday()]
    except (ValueError, TypeError):
        return iso, ""


def _wrap(draw, text, font, max_w):
    """按像素宽度对中英文混排做换行。"""
    lines, cur = [], ""
    for ch in str(text):
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if draw.textlength(cur + ch, font=font) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines or [""]


def render_png(digest: dict, path: str, title: str = "AI 圈日报") -> str:
    fp = _font_path()
    f_logo = ImageFont.truetype(fp, 26)
    f_brand = ImageFont.truetype(fp, 24)
    f_eyebrow = ImageFont.truetype(fp, 13)
    f_date = ImageFont.truetype(fp, 34)
    f_week = ImageFont.truetype(fp, 16)
    f_badge = ImageFont.truetype(fp, 14)
    f_intro = ImageFont.truetype(fp, 18)
    f_num = ImageFont.truetype(fp, 26)
    f_tag = ImageFont.truetype(fp, 13)
    f_title = ImageFont.truetype(fp, 21)
    f_take = ImageFont.truetype(fp, 16)
    f_why = ImageFont.truetype(fp, 14)
    f_foot = ImageFont.truetype(fp, 13)

    inner_w = W - 2 * PAD
    items = digest.get("items", [])

    # ── 先量算总高度 ──
    d, w = _fmt_date(digest.get("date", ""))
    y = PAD + 56  # header brand block
    y += 60       # date row
    y += 24
    intro_lines = _wrap(_measure_draw(), digest.get("intro", ""), f_intro, inner_w - 40)
    y += len(intro_lines) * 28 + 36 + 24

    item_blocks = []
    for it in items:
        body_w = inner_w - 54
        t_lines = _wrap(_measure_draw(), it.get("title", ""), f_title, body_w)
        k_lines = _wrap(_measure_draw(), it.get("take", ""), f_take, body_w)
        why_text = "为什么重要 · " + it.get("why", "")
        y_lines = _wrap(_measure_draw(), why_text, f_why, body_w)
        h = 26 + len(t_lines) * 30 + 6 + len(k_lines) * 24 + 8 + len(y_lines) * 22 + 22
        item_blocks.append((it, t_lines, k_lines, y_lines, h))
        y += h

    closing_lines = _wrap(_measure_draw(), digest.get("closing", ""), f_take, inner_w - 160)
    y += 24 + max(len(closing_lines) * 24, 40) + 40

    H = y + PAD

    # ── 背景 ──
    img = Image.new("RGB", (W, H), BG_BASE)
    # 左上角径向微光（简单线性近似）
    glow = Image.new("RGB", (W, H), BG_BASE)
    gd = ImageDraw.Draw(glow)
    for i in range(260):
        t = i / 260
        col = tuple(int(BG_TOP[j] * (1 - t) + BG_BASE[j] * t) for j in range(3))
        gd.line([(0, i), (W, i)], fill=col)
    img = Image.blend(img, glow, 0.5)
    draw = ImageDraw.Draw(img)

    # 卡片边框
    draw.rounded_rectangle([6, 6, W - 6, H - 6], radius=26, outline=CARD_BORDER, width=1)

    x = PAD
    y = PAD

    # ── Header：logo + 品牌 ──
    draw.rounded_rectangle([x, y, x + 46, y + 46], radius=12, fill=BLUE)
    draw.text((x + 8, y + 8), "AI", font=f_logo, fill=BG_BASE)
    draw.text((x + 60, y + 2), title, font=f_brand, fill=WHITE)
    draw.text((x + 60, y + 32), "DAILY AI BRIEFING", font=f_eyebrow, fill=TEAL)
    y += 70

    # 分隔线
    draw.line([(x, y), (W - PAD, y)], fill=(40, 60, 70), width=1)
    y += 22

    # ── 日期行 ──
    draw.text((x, y), d, font=f_date, fill=WHITE)
    dw = draw.textlength(d, font=f_date)
    draw.text((x + dw + 14, y + 14), w, font=f_week, fill=MUTE)
    badge = f"每日精选 · {len(items)} 条"
    bw = draw.textlength(badge, font=f_badge)
    draw.rounded_rectangle([W - PAD - bw - 24, y + 6, W - PAD, y + 34], radius=14,
                           outline=TEAL, width=1)
    draw.text((W - PAD - bw - 12, y + 12), badge, font=f_badge, fill=TEAL)
    y += 60

    # ── 卷首语 ──
    box_top = y
    intro_h = len(intro_lines) * 28 + 24
    draw.rounded_rectangle([x, box_top, W - PAD, box_top + intro_h], radius=10,
                           fill=(18, 32, 38))
    draw.rectangle([x, box_top, x + 3, box_top + intro_h], fill=TEAL)
    ty = box_top + 12
    for ln in intro_lines:
        draw.text((x + 18, ty), ln, font=f_intro, fill=(230, 237, 246))
        ty += 28
    y = box_top + intro_h + 24

    # ── 条目 ──
    for idx, (it, t_lines, k_lines, y_lines, h) in enumerate(item_blocks, 1):
        if idx > 1:
            draw.line([(x, y), (W - PAD, y)], fill=(28, 34, 48), width=1)
        iy = y + 18
        draw.text((x, iy), f"{idx:02d}", font=f_num, fill=BLUE)
        bx = x + 54
        # tag chip
        tag = it.get("tag", "")
        tw = draw.textlength(tag, font=f_tag)
        draw.rounded_rectangle([bx, iy, bx + tw + 16, iy + 22], radius=6, fill=(24, 40, 70))
        draw.text((bx + 8, iy + 3), tag, font=f_tag, fill=TEAL)
        ty = iy + 30
        for ln in t_lines:
            draw.text((bx, ty), ln, font=f_title, fill=WHITE)
            ty += 30
        ty += 4
        for ln in k_lines:
            draw.text((bx, ty), ln, font=f_take, fill=GREY)
            ty += 24
        ty += 6
        for j, ln in enumerate(y_lines):
            draw.text((bx, ty), ln, font=f_why, fill=DGREY)
            ty += 22
        y += h

    # ── 页脚 ──
    draw.line([(x, y), (W - PAD, y)], fill=(28, 34, 48), width=1)
    y += 20
    cy = y
    for ln in closing_lines:
        draw.text((x, cy), ln, font=f_take, fill=(205, 213, 225))
        cy += 24
    foot = "由 Claude 生成 · AI 圈日报机器人"
    fw = draw.textlength(foot, font=f_foot)
    draw.text((W - PAD - fw, y + 2), foot, font=f_foot, fill=(74, 83, 102))

    img.save(path)
    return path


_DRAW_SINGLETON = None


def _measure_draw():
    """提供一个用于文本测量的 Draw 对象。"""
    global _DRAW_SINGLETON
    if _DRAW_SINGLETON is None:
        _DRAW_SINGLETON = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    return _DRAW_SINGLETON
