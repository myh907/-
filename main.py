"""公众号自动化主入口

用法：
    # 上传封面图并获取 media_id
    python main.py upload --image cover.jpg

    # 立即发布一篇文章
    python main.py publish --topic "2025年AI发展趋势"

    # 仅生成内容，不发布（用于预览）
    python main.py generate --topic "健康饮食的5个习惯"

    # 从文件批量发布
    python main.py batch --file topics.txt

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
    for _ in range(6):
        time.sleep(5)
        status = wechat.get_publish_status(publish_id)
        publish_status = status.get("publish_info", {}).get("status", -1)
        if publish_status == 0:
            print("发布成功！")
            return
        if publish_status in (2, 3):
            print(f"发布失败，状态：{status}")
            return
        print("发布中，稍候…")

    print("发布超时，请在公众号后台查看状态")


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


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="微信公众号自动化工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_upl = sub.add_parser("upload", help="上传封面图，获取 media_id")
    p_upl.add_argument("--image", required=True, help="本地图片路径（JPG/PNG，≤1MB）")

    p_pub = sub.add_parser("publish", help="生成并发布文章")
    p_pub.add_argument("--topic", default=None, help="文章主题，留空则从 topics.txt 自动选取")
    p_pub.add_argument("--thumb", default=None, help="封面图 media_id")

    p_gen = sub.add_parser("generate", help="仅生成预览，不发布")
    p_gen.add_argument("--topic", required=True)

    p_bat = sub.add_parser("batch", help="从文件批量发布")
    p_bat.add_argument("--file", required=True)

    p_sch = sub.add_parser("schedule", help="定时发布")
    p_sch.add_argument("--topic", required=True)
    p_sch.add_argument("--time", default=None, help="HH:MM，默认读取 PUBLISH_SCHEDULE 环境变量")

    args = parser.parse_args()

    if args.cmd == "upload":
        upload_thumb(args.image)
    elif args.cmd == "publish":
        topic = args.topic or pick_today_topic("topics.txt")
        publish_article(topic, args.thumb)
    elif args.cmd == "generate":
        generate_preview(args.topic)
    elif args.cmd == "batch":
        batch_publish(args.file)
    elif args.cmd == "schedule":
        publish_time = args.time or os.getenv("PUBLISH_SCHEDULE", "09:00")
        print(f"定时任务已启动，每天 {publish_time} 发布：{args.topic}")
        schedule.every().day.at(publish_time).do(publish_article, topic=args.topic)
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
