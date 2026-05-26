import requests
import re
from datetime import datetime, timedelta

# ========== 配置 ==========
PUSHPLUS_TOKEN = ""  # 由 GitHub Secrets 注入，这里留空

# ========== 1. 获取文章列表 ==========
def get_articles():
    """通过搜狗微信搜索获取机器之心最近一周的文章"""
    query = "机器之心 site:mp.weixin.qq.com"
    url = f"https://weixin.sogou.com/weixin?type=2&query={query}&ie=utf8"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'
    html = resp.text

    # 提取文章链接和标题
    articles = []
    pattern = r'<a[^>]+href="(https://mp\.weixin\.qq\.com/[^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html)

    for link, title in matches:
        if link not in [a[0] for a in articles]:
            articles.append((link, title))

    return articles


# ========== 2. 提取 GitHub 内容 ==========
def extract_github_content(article_url):
    """抓取文章正文，提取包含 .github 的行"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(article_url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        html = resp.text

        # 提取正文（微信公众号文章的正文在 js_content 里）
        content_match = re.search(r'id="js_content"(.*?)</script>', html, re.DOTALL)
        if not content_match:
            return []

        text = content_match.group(1)
        text = re.sub(r'<[^>]+>', '', text)        # 去掉 HTML 标签
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)

        # 提取包含 .github 的行
        github_lines = []
        for line in text.split('\n'):
            if '.github' in line.lower():
                line = line.strip()
                if line:
                    github_lines.append(line)

        return github_lines

    except Exception as e:
        print(f"  ❌ 提取失败: {e}")
        return []


# ========== 3. PushPlus 推送 ==========
def push_to_wechat(title, content):
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("  ⚠️ 未配置 PushPlus Token，跳过推送")
        return

    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"🤖 机器之心 | {title}",
        "content": content,
        "template": "html"
    }

    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        if result.get('code') == 200:
            print("  ✅ 推送成功！")
        else:
            print(f"  ❌ 推送失败: {result}")
    except Exception as e:
        print(f"  ❌ 推送异常: {e}")


# ========== 4. 主函数 ==========
def main():
    print(f"\n{'='*50}")
    print(f"🔍 机器之心监控 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    articles = get_articles()
    print(f"📰 找到 {len(articles)} 篇文章\n")

    all_results = []

    for url, title in articles[:10]:  # 最多处理10篇，避免超时
        print(f"📝 正在处理: {title[:40]}...")
        github_lines = extract_github_content(url)

        if github_lines:
            result = f"【{title}】\n" + "\n".join(f"  → {line}" for line in github_lines)
            all_results.append(result)
            print(f"  ✅ 发现 {len(github_lines)} 条 GitHub 相关内容\n")
        else:
            print(f"  ! 无 GitHub 内容\n")

    if all_results:
        content = "\n---\n\n".join(all_results)
        push_to_wechat("GitHub内容提取", content)
        print(f"\n🎉 共发现 {len(all_results)} 篇含 GitHub 的文章")
    else:
        print("\n! 本周无 GitHub 相关内容")


if __name__ == "__main__":
    main()
