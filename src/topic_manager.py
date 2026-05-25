"""按日期轮转从 topics.txt 选取今天的主题"""

import datetime
import os


def pick_today_topic(topics_file: str = "topics.txt") -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), topics_file)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"找不到 {topics_file}，请创建该文件并每行写一个主题，或用 --topic 参数指定主题"
        )

    with open(path, encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not topics:
        raise ValueError(f"{topics_file} 没有有效主题")

    day_index = datetime.date.today().timetuple().tm_yday - 1
    topic = topics[day_index % len(topics)]
    print(f"今日主题（第 {day_index + 1} 天，共 {len(topics)} 个）：{topic}")
    return topic
