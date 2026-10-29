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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict


# 搜索关键词
KEYWORDS = [
    "免费", "free", "token", "api", "key",
    "claude", "gpt", "openai", "anthropic",
    "openrouter", "白嫖", "赠送", "领取",
    "额度", "试用", "gemini", "copilot"
]

# Discourse API 端点
LATEST_URL = "https://linux.do/latest.json"
SEARCH_URL = "https://linux.do/search.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch_latest_posts(page: int = 0) -> Dict:
    """获取最新帖子列表"""
    url = f"{LATEST_URL}" if page == 0 else f"{LATEST_URL}?page={page}"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        print(f"  Fetching: {url}", file=sys.stderr)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        print(f"Error fetching latest posts: {e}", file=sys.stderr)
        return {}


def search_posts(query: str) -> Dict:
    """搜索帖子（备选方案）"""
    encoded_query = urllib.parse.quote(query)
    url = f"{SEARCH_URL}?q={encoded_query}"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        print(f"  Searching: {query}", file=sys.stderr)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        print(f"Error searching '{query}': {e}", file=sys.stderr)
        return {}


def extract_posts_from_latest(data: Dict) -> List[Dict]:
    """从 latest.json 响应中提取帖子信息"""
    posts = []

    if not data or "topic_list" not in data:
        return posts

    topics = data.get("topic_list", {}).get("topics", [])

    for topic in topics:
        post_info = {
            "id": topic.get("id"),
            "title": topic.get("title", ""),
            "slug": topic.get("slug", ""),
            "created_at": topic.get("created_at", ""),
            "updated_at": topic.get("last_posted_at", topic.get("created_at", "")),
            "views": topic.get("views", 0),
            "posts_count": topic.get("posts_count", 0),
            "like_count": topic.get("like_count", 0),
            "url": f"https://linux.do/t/{topic.get('slug', '')}/{topic.get('id')}",
            "category_id": topic.get("category_id"),
            "tags": topic.get("tags", []),
        }
        posts.append(post_info)

    return posts


def extract_posts_from_search(data: Dict) -> List[Dict]:
    """从 search.json 响应中提取帖子信息"""
    posts = []

    if not data:
        return posts

    # Discourse 搜索结果结构
    topics = data.get("topics", [])

    for topic in topics:
        post_info = {
            "id": topic.get("id"),
            "title": topic.get("title", ""),
            "slug": topic.get("slug", ""),
            "created_at": topic.get("created_at", ""),
            "updated_at": topic.get("last_posted_at", topic.get("created_at", "")),
            "views": topic.get("views", 0),
            "posts_count": topic.get("posts_count", 0),
            "like_count": topic.get("like_count", 0),
            "url": f"https://linux.do/t/{topic.get('slug', '')}/{topic.get('id')}",
            "category_id": topic.get("category_id"),
            "tags": topic.get("tags", []),
        }
        posts.append(post_info)

    return posts


def check_relevance(post: Dict) -> bool:
    """检查帖子是否与免费 token 相关"""
    text = f"{post.get('title', '')} {' '.join(post.get('tags', []))}".lower()

    # 必须包含至少一个关键词
    for keyword in KEYWORDS:
        if keyword.lower() in text:
            return True
    return False


def filter_recent_posts(posts: List[Dict], days: int = 7) -> List[Dict]:
    """只保留最近 N 天的帖子"""
    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for post in posts:
        created_str = post.get("created_at", "")
        if created_str:
            try:
                # Parse ISO format datetime
                created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                if created.replace(tzinfo=None) >= cutoff:
                    recent.append(post)
            except:
                # If parsing fails, include the post
                recent.append(post)

    return recent


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
            "> 💡 提示：监控会持续运行，一旦有相关帖子会立即更新。",
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
        "## 📖 项目说明",
        "",
        "本项目自动监控 [linux.do](https://linux.do) 论坛上关于免费 AI API token 的帖子。",
        "",
        "### 功能",
        "",
        "- ✅ 每 30 分钟自动检查",
        "- ✅ 智能关键词匹配",
        "- ✅ 自动更新 README",
        "- ✅ 保存历史数据 (JSON)",
        "- ✅ 支持手动触发",
        "",
        "---",
        "",
        "*自动监控 by GitHub Actions*",
    ])

    return "\n".join(lines)


def main():
    """主函数"""
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 开始监控 linux.do...", file=sys.stderr)

    all_posts = []
    seen_ids = set()

    # 方法 1: 获取最新帖子（前 5 页）
    print("\n📥 获取最新帖子...", file=sys.stderr)
    for page in range(5):
        data = fetch_latest_posts(page)
        posts = extract_posts_from_latest(data)
        print(f"  Page {page}: 获取到 {len(posts)} 个帖子", file=sys.stderr)

        for post in posts:
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                if check_relevance(post):
                    all_posts.append(post)

    # 方法 2: 使用搜索 API（备选）
    search_queries = [
        "免费 token",
        "free api",
        "openai 免费",
        "claude 额度",
        "白嫖 api",
    ]

    print("\n🔎 搜索特定关键词...", file=sys.stderr)
    for query in search_queries:
        data = search_posts(query)
        posts = extract_posts_from_search(data)
        print(f"  '{query}': 找到 {len(posts)} 个结果", file=sys.stderr)

        for post in posts:
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                if check_relevance(post):
                    all_posts.append(post)

    # 只保留最近 7 天的帖子
    all_posts = filter_recent_posts(all_posts, days=7)

    # 按创建时间排序（最新在前）
    all_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # 只保留最新的 20 个
    all_posts = all_posts[:20]

    print(f"\n✅ 找到 {len(all_posts)} 个相关帖子", file=sys.stderr)

    # 生成报告
    search_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    markdown = generate_markdown(all_posts, search_time)

    # 保存结果
    output_file = output_dir / "README.md"
    output_file.write_text(markdown, encoding="utf-8")
    print(f"📝 报告已保存: {output_file}", file=sys.stderr)

    # 保存 JSON 数据
    data_file = output_dir / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({
            "search_time": search_time,
            "count": len(all_posts),
            "posts": all_posts,
        }, f, ensure_ascii=False, indent=2)
    print(f"📊 数据已保存: {data_file}", file=sys.stderr)

    # 输出摘要到 stdout
    print(f"\n{'='*60}")
    print(f"监控完成 - {search_time}")
    print(f"找到 {len(all_posts)} 个相关帖子")
    print(f"{'='*60}\n")

    for post in all_posts[:5]:
        print(f"• {post['title'][:60]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
