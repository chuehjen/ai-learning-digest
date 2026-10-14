#!/usr/bin/env python3
"""Build the next Saturday's video/podcast learning plan."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BJT = ZoneInfo("Asia/Shanghai")
FIRST_SATURDAY = date(2026, 10, 17)

COURSES = [
    {
        "topic": "LLM 如何工作",
        "title": "Transformers, the tech behind LLMs",
        "url": "https://www.3blue1brown.com/lessons/gpt/",
        "podcast_title": "AI Fundamentals: Datasets 101",
        "podcast_url": "https://www.latent.space/p/datasets-101",
        "exercise": "挑一个熟悉的产品任务，写出 LLM 能做、不能可靠完成的部分，并列出 3 个需要人工核验的事实。",
    },
    {
        "topic": "提示词与任务拆解",
        "title": "ChatGPT Prompt Engineering for Developers",
        "url": "https://www.deeplearning.ai/courses/chatgpt-prompt-eng",
        "podcast_title": "The Ultimate Guide to Prompting",
        "podcast_url": "https://www.latent.space/p/learn-prompting",
        "exercise": "把一个工作任务写成 3 版提示词，比较输出质量、核验时间和总耗时。",
    },
    {
        "topic": "多步骤 AI 工作流",
        "title": "Building Systems with the ChatGPT API",
        "url": "https://www.deeplearning.ai/courses/chatgpt-building-system",
        "podcast_title": "The Point of LangChain",
        "podcast_url": "https://www.latent.space/p/langchain",
        "exercise": "画出一个 3 步 AI 工作流，注明每步输入、输出、失败条件和人工确认点。",
    },
    {
        "topic": "检索增强生成 RAG",
        "title": "Building and Evaluating Advanced RAG",
        "url": "https://www.deeplearning.ai/courses/building-evaluating-advanced-rag",
        "podcast_title": "RAG Is A Hack",
        "podcast_url": "https://www.latent.space/p/llamaindex",
        "exercise": "选一份公开文档，设计 5 个检索问题，并区分有证据的回答与无法回答的情况。",
    },
    {
        "topic": "评估与回归测试",
        "title": "Automated Testing for LLMOps",
        "url": "https://www.deeplearning.ai/short-courses/automated-testing-llmops",
        "podcast_title": "AI Fundamentals: Benchmarks 101",
        "podcast_url": "https://www.latent.space/p/benchmarks-101",
        "exercise": "为一个 AI 功能写 10 条测试案例，包含漏答、误答和高风险错误。",
    },
    {
        "topic": "Agent 工作机制",
        "title": "Agentic AI",
        "url": "https://www.deeplearning.ai/courses/agentic-ai",
        "podcast_title": "Vercel's Andrew Qu on why agents are a new kind of software",
        "podcast_url": "https://www.latent.space/p/vercel-agents-new-software",
        "exercise": "把一个任务拆成工具调用步骤，写清哪些步骤能自动执行、哪些必须人工批准。",
    },
    {
        "topic": "AI 产品机会判断",
        "title": "Generative AI for Everyone",
        "url": "https://www.deeplearning.ai/courses/generative-ai-for-everyone",
        "podcast_title": "ChatGPT, GPT4 hype, and Building LLM-native products",
        "podcast_url": "https://www.latent.space/p/chatgpt-gpt4-hype-and-building-llm",
        "exercise": "列出 3 个产品机会，按用户价值、可验证性、总人工工时和风险排序。",
    },
    {
        "topic": "安全与上线决策",
        "title": "Red Teaming LLM Applications",
        "url": "https://www.deeplearning.ai/courses/red-teaming-llm-applications",
        "podcast_title": "Red-Teaming after Mythos",
        "podcast_url": "https://www.latent.space/p/gray-swan",
        "exercise": "为前几周的 AI 功能写上线检查表：证据、误用场景、责任人和回滚条件。",
    },
]


def saturday_on_or_after(day: date) -> date:
    return day + timedelta(days=(5 - day.weekday()) % 7)


def build(now: datetime) -> dict:
    today = now.astimezone(BJT).date()
    saturday = saturday_on_or_after(today)
    if saturday < FIRST_SATURDAY:
        saturday = FIRST_SATURDAY
    week = (saturday - FIRST_SATURDAY).days // 7 + 1
    course = COURSES[(week - 1) % len(COURSES)]
    podcast = {"title": course["podcast_title"], "url": course["podcast_url"], "source": "Latent Space", "format": "podcast"}
    date_bjt = saturday.isoformat()
    course_item = {"title": course["title"], "url": course["url"], "source": "Course", "format": "video"}
    message = "\n".join([
        f"【AI 系统学习｜第{week}周｜{course['topic']}】",
        f"主课视频：{course['title']}",
        course["url"],
        f"配套播客：{podcast['title']}",
        podcast["url"],
        "本周 5 小时：看课与笔记 90 分钟；听播客 60 分钟；动手练习 120 分钟；复盘 30 分钟。",
        f"练习：{course['exercise']}",
        "课程可能需要登录；以页面实际开放内容为准。",
    ])
    return {
        "schema_version": 1,
        "kind": "weekly",
        "date_bjt": date_bjt,
        "generated_at_utc": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "week_number": week,
        "message": message,
        "items": [course_item, podcast],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    data = build(datetime.now(timezone.utc))
    output = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(output)
    else:
        (ROOT / "archive" / "weekly").mkdir(parents=True, exist_ok=True)
        (ROOT / "weekly.json").write_text(output, encoding="utf-8")
        (ROOT / "archive" / "weekly" / f"{data['date_bjt']}.json").write_text(output, encoding="utf-8")
        print(f"Wrote weekly plan for {data['date_bjt']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Weekly plan generation failed: {error}", file=sys.stderr)
        sys.exit(1)
