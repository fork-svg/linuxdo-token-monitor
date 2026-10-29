#!/usr/bin/env python3
"""
linux.do 免费 token 监控脚本
监控 linux.do 论坛上包含免费 token/API 关键词的帖子
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# 搜索关键词
KEYWORDS = [
    "免费", "free", "token", "API", "key",
    "Claude", "GPT", "OpenAI", "Anthropic",
    "OpenRouter", "白嫖", "赠送", "领取",
    "额度", "试用", "test"
]

# Discourse API 端点
SEARCH_URL = "https://linux.do/search.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LinuxDoMonitor/1.0)",
    "Accept": "application/json",
}


def search_posts(query: str, page: int = 1) -> Dict:
    """搜索 linux.do 帖子"""
    encoded_query = urllib.parse.quote(query)
    url = f"{SEARCH_URL}?q={encoded_query}&page={page}"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error searching '{query}': {e}", file=sys.stderr)
        return {}


def extract_relevant_posts(search_results: Dict) -> List[Dict]:
    """从搜索结果中提取相关帖子信息"""
    posts = []

    if not search_results or "topics" not in search_results:
        return posts

    for topic in search_results.get("topics", []):
        # 只保留最近 7 天的帖子
        created_at = topic.get("created_at", "")
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_ago = (datetime.now(created_date.tzinfo) - created_date).days
            if days_ago > 7:
                continue

        post_info = {
            "id": topic.get("id"),
            "title": topic.get("title"),
            "slug": topic.get("slug"),
            "created_at": created_at,
            "views": topic.get("views", 0),
            "posts_count": topic.get("posts_count", 0),
            "like_count": topic.get("like_count", 0),
            "url": f"https://linux.do/t/{topic.get('slug')}/{topic.get('id')}",
            "category_id": topic.get("category_id"),
        }
        posts.append(post_info)

    return posts


def check_relevance(post: Dict) -> bool:
    """检查帖子是否与免费 token 相关"""
    text = f"{post.get('title', '')}".lower()

    # 必须包含至少一个关键词
    for keyword in KEYWORDS:
        if keyword.lower() in text:
            return True
    return False


def generate_markdown(posts: List[Dict], search_time: str) -> str:
    """生成 Markdown 格式的监控报告"""
    lines = [
        "# 🎁 Linux.do 免费 Token 监控",
        "",
        f"**最后更新**: {search_time}",
        "",
        f"**监控频率**: 每 30 分钟",
        "",
        f"**当前找到**: {len(posts)} 个相关帖子",
        "",
        "---",
        "",
    ]

    if not posts:
        lines.extend([
            "## 📭 暂无新帖",
            "",
            "暂时没有发现新的免费 token 相关帖子。",
            "",
        ])
    else:
        lines.extend([
            "## 📋 最新帖子",
            "",
        ])

        for i, post in enumerate(posts, 1):
            title = post.get("title", "无标题")
            url = post.get("url", "")
            created = post.get("created_at", "")[:10]
            views = post.get("views", 0)
            likes = post.get("like_count", 0)
            replies = post.get("posts_count", 0) - 1

            lines.extend([
                f"### {i}. {title}",
                "",
                f"- 🔗 [链接]({url})",
                f"- 📅 发布时间: {created}",
                f"- 👀 浏览: {views} | 👍 点赞: {likes} | 💬 回复: {replies}",
                "",
            ])

    lines.extend([
        "---",
        "",
        "## 🔍 监控关键词",
        "",
        "```",
        ", ".join(KEYWORDS),
        "```",
        "",
        "---",
        "",
        f"*自动监控 by GitHub Actions*",
    ])

    return "\n".join(lines)


def main():
    """主函数"""
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 开始监控 linux.do...")

    # 搜索多个关键词组合
    all_posts = []
    seen_ids = set()

    search_queries = [
        "免费 token",
        "free API",
        "OpenAI 免费",
        "Claude 额度",
        "Anthropic 白嫖",
        "OpenRouter 免费",
        "API key 赠送",
    ]

    for query in search_queries:
        print(f"  搜索: {query}")
        results = search_posts(query)
        posts = extract_relevant_posts(results)

        for post in posts:
            if post["id"] not in seen_ids and check_relevance(post):
                seen_ids.add(post["id"])
                all_posts.append(post)

    # 按创建时间排序（最新在前）
    all_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # 只保留最新的 20 个
    all_posts = all_posts[:20]

    print(f"✅ 找到 {len(all_posts)} 个相关帖子")

    # 生成报告
    search_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    markdown = generate_markdown(all_posts, search_time)

    # 保存结果
    output_file = output_dir / "README.md"
    output_file.write_text(markdown, encoding="utf-8")
    print(f"📝 报告已保存: {output_file}")

    # 保存 JSON 数据（供后续分析）
    data_file = output_dir / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({
            "search_time": search_time,
            "count": len(all_posts),
            "posts": all_posts,
        }, f, ensure_ascii=False, indent=2)
    print(f"📊 数据已保存: {data_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
