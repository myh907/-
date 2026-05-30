"""公众号自动化主入口

用法：
    # 检查 API 凭证是否正确
    python main.py test

    # 上传封面图并获取 media_id
    python main.py upload --image cover.jpg

    # 立即发布一篇文章
    python main.py publish --topic "2025年AI发展趋势"

    # 仅生成内容，不发布（用于预览）
    python main.py generate --topic "健康饮食的5个习惯"

    # 从文件批量发布
    python main.py batch --file topics.txt

    # 查看最近发布记录
    python main.py log

    # 生成今日「AI 圈日报」海报（读取 daily_sources.txt）
    python main.py daily

    # 不配 API key，直接看日报海报示例效果
    python main.py daily --demo

    # 生成日报并发布到公众号
    python main.py daily --publish

    # 启动定时任务（每天 PUBLISH_SCHEDULE 时间自动发布）
    python main.py schedule --topic "每日科技资讯"
"""

import argparse
import os
import sys
import time

import schedule
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from src.content_generator import ContentGenerator
from src.daily_digest import DailyDigest, demo_digest, load_sources
from src.digest_card import render_poster, digest_to_article
from src.poster_png import render_png
from src.publish_log import write as log_write, read_recent as log_recent
from src.topic_manager import pick_today_topic
from src.wechat_api import WeChatClient, WeChatAPIError

load_dotenv()

# ── 配置校验 ──────────────────────────────────────────────────────────────────

def _require_env(*keys: str) -> dict:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        print(f"缺少环境变量：{', '.join(missing)}\n请参考 .env.example 配置 .env 文件")
        sys.exit(1)
    return {k: os.environ[k] for k in keys}

# ── 核心流程 ──────────────────────────────────────────────────────────────────

def test_connections() -> None:
    """验证微信 API 和 Anthropic API 凭证是否有效。"""
    cfg = _require_env("WECHAT_APP_ID", "WECHAT_APP_SECRET", "ANTHROPIC_API_KEY")
    ok = True

    print("[ 1/2 ] 检查微信公众号 API…")
    try:
        wechat = WeChatClient(cfg["WECHAT_APP_ID"], cfg["WECHAT_APP_SECRET"])
        token = wechat.get_access_token()
        print(f"        access_token 获取成功（{token[:8]}…）")
    except WeChatAPIError as e:
        print(f"        失败：{e}")
        ok = False
    except Exception as e:
        print(f"        网络错误：{e}")
        ok = False

    print("[ 2/2 ] 检查 Anthropic API…")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=cfg["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
        print(f"        连接正常（model: {msg.model}）")
    except Exception as e:
        print(f"        失败：{e}")
        ok = False

    print()
    print("全部通过，可以开始使用！" if ok else "有配置项异常，请检查 .env 文件。")
    sys.exit(0 if ok else 1)


def publish_article(topic: str, thumb_media_id: str | None = None) -> None:
    cfg = _require_env("WECHAT_APP_ID", "WECHAT_APP_SECRET", "ANTHROPIC_API_KEY")

    generator = ContentGenerator(cfg["ANTHROPIC_API_KEY"])
    wechat = WeChatClient(cfg["WECHAT_APP_ID"], cfg["WECHAT_APP_SECRET"])

    print(f"正在生成文章：{topic}")
    article = generator.generate(topic)
    print(f"标题：{article['title']}")
    print(f"摘要：{article['digest']}")

    # 公众号 API 要求必须有 thumb_media_id（封面图素材 ID）
    # 如果未传入，使用占位值（测试用）或在此上传默认封面
    cover = thumb_media_id or os.getenv("DEFAULT_THUMB_MEDIA_ID", "")
    if not cover:
        print("警告：未配置封面图 media_id（DEFAULT_THUMB_MEDIA_ID），发布可能失败")

    draft_payload = {
        "title": article["title"],
        "author": os.getenv("AUTHOR_NAME", ""),
        "digest": article["digest"],
        "content": article["content"],
        "content_source_url": "",
        "thumb_media_id": cover,
        "need_open_comment": 1,
    }

    print("正在创建草稿…")
    media_id = wechat.add_draft([draft_payload])
    print(f"草稿已创建，media_id：{media_id}")

    print("正在提交发布…")
    publish_id = wechat.publish(media_id)
    print(f"已提交发布，publish_id：{publish_id}")

    # 轮询发布状态（最多等 30 秒）
    final_status = "timeout"
    for _ in range(6):
        time.sleep(5)
        status = wechat.get_publish_status(publish_id)
        publish_status = status.get("publish_info", {}).get("status", -1)
        if publish_status == 0:
            print("发布成功！")
            final_status = "success"
            break
        if publish_status in (2, 3):
            print(f"发布失败，状态：{status}")
            final_status = "failed"
            break
        print("发布中，稍候…")
    else:
        print("发布超时，请在公众号后台查看状态")

    log_write(topic, article["title"], media_id, publish_id, final_status)


def generate_preview(topic: str) -> None:
    cfg = _require_env("ANTHROPIC_API_KEY")
    generator = ContentGenerator(cfg["ANTHROPIC_API_KEY"])

    print(f"正在生成文章：{topic}\n")
    article = generator.generate(topic)
    print(f"标题：{article['title']}\n")
    print(f"摘要：{article['digest']}\n")
    print("正文：\n" + "─" * 40)
    print(article["content"])


def upload_thumb(image_path: str) -> None:
    cfg = _require_env("WECHAT_APP_ID", "WECHAT_APP_SECRET")
    wechat = WeChatClient(cfg["WECHAT_APP_ID"], cfg["WECHAT_APP_SECRET"])

    if not os.path.exists(image_path):
        print(f"文件不存在：{image_path}")
        sys.exit(1)

    print(f"正在上传封面图：{image_path}")
    media_id = wechat.upload_thumb(image_path)
    print(f"上传成功！media_id：{media_id}")
    print(f"请将此 media_id 填入 .env 的 DEFAULT_THUMB_MEDIA_ID，或 GitHub Secrets 中")


def show_log(n: int = 10) -> None:
    entries = log_recent(n)
    if not entries:
        print("暂无发布记录")
        return
    print(f"最近 {len(entries)} 条发布记录：\n")
    for e in entries:
        status_icon = {"success": "✓", "failed": "✗", "timeout": "?"}.get(e["status"], "-")
        print(f"  {status_icon} {e['time'][:16]}  {e['title']}")
        print(f"      主题：{e['topic']}  状态：{e['status']}")
        print()


def batch_publish(topics_file: str) -> None:
    with open(topics_file, encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip()]
    print(f"共 {len(topics)} 个主题，开始批量发布…")
    for i, topic in enumerate(topics, 1):
        print(f"\n[{i}/{len(topics)}] {topic}")
        try:
            publish_article(topic)
        except WeChatAPIError as e:
            print(f"发布失败：{e}")
        time.sleep(2)  # 避免请求过快


def daily_report(
    sources_file: str = "daily_sources.txt",
    demo: bool = False,
    publish: bool = False,
    out_dir: str = "output",
) -> None:
    """生成今日「AI 圈日报」海报，可选发布到公众号。"""
    if demo:
        print("使用示例数据生成日报（demo 模式，无需 API key）…")
        digest = demo_digest()
    else:
        cfg = _require_env("ANTHROPIC_API_KEY")
        items = load_sources(sources_file)
        if not items:
            print(
                f"{sources_file} 没有热点内容。\n"
                f"请在该文件每行写一条今天的 AI 热点，或先用 --demo 体验效果。"
            )
            sys.exit(1)
        print(f"读取到 {len(items)} 条热点，正在请 Claude 主编整理日报…")
        digest = DailyDigest(cfg["ANTHROPIC_API_KEY"]).generate(items)

    # 渲染并保存海报（HTML + PNG）
    os.makedirs(out_dir, exist_ok=True)
    poster_path = os.path.join(out_dir, f"ai-daily-{digest['date']}.html")
    with open(poster_path, "w", encoding="utf-8") as f:
        f.write(render_poster(digest))

    png_path = os.path.join(out_dir, f"ai-daily-{digest['date']}.png")
    try:
        render_png(digest, png_path)
    except Exception as e:
        png_path = None
        print(f"（PNG 导出跳过：{e}）")

    print(f"\n卷首语：{digest.get('intro', '')}")
    for i, it in enumerate(digest.get("items", []), 1):
        print(f"  {i:02d}. [{it.get('tag', '')}] {it.get('title', '')}")
    print(f"\n海报 HTML：{poster_path}（浏览器打开可截图）")
    if png_path:
        print(f"分享图 PNG：{png_path}（可直接转发）")

    if not publish:
        return

    cfg = _require_env("WECHAT_APP_ID", "WECHAT_APP_SECRET")
    wechat = WeChatClient(cfg["WECHAT_APP_ID"], cfg["WECHAT_APP_SECRET"])
    article = digest_to_article(digest)
    cover = os.getenv("DEFAULT_THUMB_MEDIA_ID", "")
    if not cover:
        print("警告：未配置封面图 media_id（DEFAULT_THUMB_MEDIA_ID），发布可能失败")

    draft = {
        "title": article["title"],
        "author": os.getenv("AUTHOR_NAME", ""),
        "digest": article["digest"],
        "content": article["content"],
        "content_source_url": "",
        "thumb_media_id": cover,
        "need_open_comment": 1,
    }
    print("\n正在创建草稿并发布…")
    media_id = wechat.add_draft([draft])
    publish_id = wechat.publish(media_id)
    print(f"已提交发布，publish_id：{publish_id}")
    log_write("AI 圈日报", article["title"], media_id, publish_id, "submitted")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="微信公众号自动化工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("test", help="验证微信 API 和 Anthropic API 凭证")

    p_upl = sub.add_parser("upload", help="上传封面图，获取 media_id")
    p_upl.add_argument("--image", required=True, help="本地图片路径（JPG/PNG，≤1MB）")

    p_pub = sub.add_parser("publish", help="生成并发布文章")
    p_pub.add_argument("--topic", default=None, help="文章主题，留空则从 topics.txt 自动选取")
    p_pub.add_argument("--thumb", default=None, help="封面图 media_id")

    p_gen = sub.add_parser("generate", help="仅生成预览，不发布")
    p_gen.add_argument("--topic", required=True)

    p_bat = sub.add_parser("batch", help="从文件批量发布")
    p_bat.add_argument("--file", required=True)

    p_log = sub.add_parser("log", help="查看最近发布记录")
    p_log.add_argument("--n", type=int, default=10, help="显示条数（默认 10）")

    p_day = sub.add_parser("daily", help="生成「AI 圈日报」海报，可选发布")
    p_day.add_argument("--sources", default="daily_sources.txt", help="热点输入文件")
    p_day.add_argument("--demo", action="store_true", help="用示例数据，无需 API key")
    p_day.add_argument("--publish", action="store_true", help="生成后发布到公众号")

    p_sch = sub.add_parser("schedule", help="定时发布")
    p_sch.add_argument("--topic", required=True)
    p_sch.add_argument("--time", default=None, help="HH:MM，默认读取 PUBLISH_SCHEDULE 环境变量")

    args = parser.parse_args()

    if args.cmd == "test":
        test_connections()
    elif args.cmd == "upload":
        upload_thumb(args.image)
    elif args.cmd == "publish":
        topic = args.topic or pick_today_topic("topics.txt")
        publish_article(topic, args.thumb)
    elif args.cmd == "generate":
        generate_preview(args.topic)
    elif args.cmd == "batch":
        batch_publish(args.file)
    elif args.cmd == "log":
        show_log(args.n)
    elif args.cmd == "daily":
        daily_report(sources_file=args.sources, demo=args.demo, publish=args.publish)
    elif args.cmd == "schedule":
        publish_time = args.time or os.getenv("PUBLISH_SCHEDULE", "09:00")
        print(f"定时任务已启动，每天 {publish_time} 发布：{args.topic}")
        schedule.every().day.at(publish_time).do(publish_article, topic=args.topic)
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
