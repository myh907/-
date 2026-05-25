name: 公众号自动发布

on:
  # 每天北京时间 09:00（UTC+8 = UTC 01:00）自动发布
  schedule:
    - cron: "0 1 * * *"

  # 手动触发，可自定义主题
  workflow_dispatch:
    inputs:
      topic:
        description: "文章主题（留空则从 topics.txt 自动选取）"
        required: false
        default: ""
      preview_only:
        description: "仅预览，不发布（true/false）"
        required: false
        default: "false"

jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: 拉取代码
        uses: actions/checkout@v4

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: 安装依赖
        run: pip install -r requirements.txt

      - name: 生成并发布文章
        env:
          WECHAT_APP_ID: ${{ secrets.WECHAT_APP_ID }}
          WECHAT_APP_SECRET: ${{ secrets.WECHAT_APP_SECRET }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DEFAULT_THUMB_MEDIA_ID: ${{ secrets.DEFAULT_THUMB_MEDIA_ID }}
          AUTHOR_NAME: ${{ secrets.AUTHOR_NAME }}
        run: |
          TOPIC="${{ github.event.inputs.topic }}"
          PREVIEW="${{ github.event.inputs.preview_only }}"

          if [ "$PREVIEW" = "true" ]; then
            if [ -z "$TOPIC" ]; then
              echo "预览模式需要指定主题"
              exit 1
            fi
            python main.py generate --topic "$TOPIC"
          elif [ -z "$TOPIC" ]; then
            # 定时任务：从 topics.txt 自动选取今日主题
            python main.py publish
          else
            # 手动指定主题
            python main.py publish --topic "$TOPIC"
          fi

      - name: 发布摘要
        if: always()
        run: |
          echo "## 发布结果" >> $GITHUB_STEP_SUMMARY
          echo "- 触发方式：${{ github.event_name }}" >> $GITHUB_STEP_SUMMARY
          echo "- 主题：${{ github.event.inputs.topic || '自动选取（topics.txt）' }}" >> $GITHUB_STEP_SUMMARY
          echo "- 时间：$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S') (北京时间)" >> $GITHUB_STEP_SUMMARY