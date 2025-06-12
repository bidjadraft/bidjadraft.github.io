import os
import time
import feedparser
import requests
from datetime import datetime
import re

RSS_URL = "https://feed.alternativeto.net/news/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_DIR = "news"
LASTPOST_FILE = os.path.join(NEWS_DIR, "lastpost.txt")
os.makedirs(NEWS_DIR, exist_ok=True)

def gemini_ask(prompt, max_retries=8, wait_seconds=10):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    headers = {'Content-Type': 'application/json'}
    for attempt in range(max_retries):
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            try:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception:
                return None
        if r.status_code == 503 or "overloaded" in r.text:
            print(f"ازدحام Gemini، إعادة المحاولة بعد {wait_seconds} ثانية...")
            time.sleep(wait_seconds)
        else:
            print(f"خطأ في Gemini: {r.text}")
            return None
    return None

def sanitize_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = text.replace(' ', '-')
    return text[:60]

def make_markdown(entry, arabic_title, arabic_body):
    title = arabic_title.strip()
    date = entry.get('published', '')[:10] or datetime.now().strftime('%Y-%m-%d')
    category = "التقنية"
    image = None
    # محاولة جلب صورة الخبر من الخلاصة
    if 'media_content' in entry and len(entry.media_content) > 0:
        image = entry.media_content[0]['url']
    elif 'enclosures' in entry and len(entry.enclosures) > 0:
        image = entry.enclosures[0]['url']
    if not image:
        image = "https://via.placeholder.com/600x400.png?text=No+Image"
    url = entry.get('link', '')

    md = f"""---
title: "{title}"
date: {date}
category: {category}
image: {image}
source: {url}
---

{arabic_body.strip()}
"""
    return md

def read_last_post():
    if not os.path.exists(LASTPOST_FILE):
        return None
    with open(LASTPOST_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def write_last_post(link):
    with open(LASTPOST_FILE, "w", encoding="utf-8") as f:
        f.write(link)

def main():
    feed = feedparser.parse(RSS_URL)
    entries = feed.entries
    if not entries:
        print("لا توجد منشورات في الخلاصة.")
        return

    last_post_link = read_last_post()
    entries = sorted(entries, key=lambda e: e.get('published_parsed', 0))

    # إذا لم يوجد lastpost.txt، أنشئ فقط أحدث مقال
    if not last_post_link:
        entries_to_process = [entries[-1]]
    else:
        entries_to_process = []
        found_last = False
        for entry in entries:
            link = entry.get('link', '')
            if found_last:
                entries_to_process.append(entry)
            elif link == last_post_link:
                found_last = True
        if not found_last:
            entries_to_process = [entries[-1]]

    if not entries_to_process:
        print("لا توجد منشورات جديدة.")
        return

    for entry in entries_to_process:
        original_title = entry.get('title', '')
        description = entry.get('summary', '')
        link = entry.get('link', '')

        # تلخيص العنوان
        prompt_title = f"""العنوان التالي هو لخبر تقني:
{original_title}
رجاءً لخص العنوان إلى عنوان صحفي جذاب باللغة العربية لا يتعدى 9 كلمات."""
        arabic_title = gemini_ask(prompt_title)
        if not arabic_title:
            print("فشل تلخيص العنوان.")
            continue

        # تلخيص الخبر
        prompt_body = f"""النص التالي هو خبر تقني:
{description}
رجاءً لخص الخبر إلى فقرتين أو ثلاث فقرات تسرد كل ما يخص الموضوع باللغة العربية، مع الحفاظ على الأسلوب الصحفي الجذاب والواضح."""
        arabic_body = gemini_ask(prompt_body)
        if not arabic_body:
            print("فشل تلخيص الخبر.")
            continue

        filename = sanitize_filename(arabic_title or original_title) + ".md"
        filepath = os.path.join(NEWS_DIR, filename)

        if os.path.exists(filepath):
            print(f"تم تخطي {filename} (موجود مسبقاً)")
            continue

        md = make_markdown(entry, arabic_title, arabic_body)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"تم إنشاء: {filepath}")

        # تحديث رابط آخر مقال
        write_last_post(link)

if __name__ == "__main__":
    main()
