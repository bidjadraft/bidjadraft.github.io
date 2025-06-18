import os
import time
import feedparser
import requests
from datetime import datetime
import re
import xml.etree.ElementTree as ET
from dateutil import parser  # تحتاج تثبيت المكتبة: pip install python-dateutil

RSS_URL = "https://feed.alternativeto.net/news/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_DIR = "news"
LASTPOST_FILE = os.path.join(NEWS_DIR, "lastpost.txt")
FEED_FILE = os.path.join(NEWS_DIR, "feed.xml")
SITE_URL = "https://bidjadraft.github.io"

os.makedirs(NEWS_DIR, exist_ok=True)

def gemini_ask(prompt, max_retries=8, wait_seconds=10):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
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

def detect_category(text, max_retries=8, wait_seconds=10):
    prompt = f"""النص التالي هو خبر تقني:
{text}
رجاءً حدد الفئة المناسبة من القائمة التالية فقط:
- تطبيقات
- أجهزة
- أنظمة
- تواصل اجتماعي
- ذكاء اصطناعي

أجب بكلمة واحدة فقط من القائمة أعلاه تصف موضوع الخبر بدقة."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    for attempt in range(max_retries):
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            try:
                category = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                valid_categories = ["تطبيقات", "أجهزة", "أنظمة", "تواصل اجتماعي", "ذكاء اصطناعي"]
                if category in valid_categories:
                    return category
                else:
                    return "التقنية"
            except Exception:
                return "التقنية"
        if r.status_code == 503 or "overloaded" in r.text:
            time.sleep(wait_seconds)
        else:
            return "التقنية"
    return "التقنية"

def sanitize_filename(text):
    text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)
    text = re.sub(r'_', '', text)
    text = re.sub(r'\s+', '-', text)
    text = text.strip('-')
    return text[:60]

def make_markdown(title, image, date, body, category):
    md = f"""---
layout: default
title: "{title}"
image: "{image}"
category: {category}
date: {date}
---

{body.strip()}
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

def append_to_feed_xml(title, link, image):
    if not os.path.exists(FEED_FILE) or os.stat(FEED_FILE).st_size == 0:
        xml_content = '''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>أخبار مدونتي</title>
    <link>https://bidjadraft.github.io/news/</link>
    <description>تحديثات الأخبار التقنية</description>
  </channel>
</rss>
'''
        with open(FEED_FILE, "w", encoding="utf-8") as f:
            f.write(xml_content)

    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    channel = root.find('channel')

    item = ET.Element('item')
    ET.SubElement(item, 'title').text = title
    ET.SubElement(item, 'link').text = link
    if image:
        ext = os.path.splitext(image)[-1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/webp"
        ET.SubElement(item, 'enclosure', url=image, type=mime)

    channel.insert(0, item)
    tree.write(FEED_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تمت إضافة خبر جديد إلى {FEED_FILE}")

def main():
    feed = feedparser.parse(RSS_URL)
    entries = feed.entries
    if not entries:
        print("لا توجد منشورات في الخلاصة.")
        return

    last_post_link = read_last_post()
    entries = sorted(entries, key=lambda e: e.get('published_parsed', 0))

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

        published_str = entry.get('published', '')
        if published_str:
            try:
                dt = parser.parse(published_str)
                date = dt.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                dt = datetime.now()
                date = dt.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            dt = datetime.now()
            date = dt.strftime('%Y-%m-%dT%H:%M:%S')

        image = None
        if 'media_content' in entry and len(entry.media_content) > 0:
            image = entry.media_content[0]['url']
        elif 'enclosures' in entry and len(entry.enclosures) > 0:
            image = entry.enclosures[0]['url']
        if not image:
            image = "https://via.placeholder.com/600x400.png?text=No+Image"

        arabic_title = None
        for attempt in range(10):
            prompt_title = f"""العنوان التالي هو لخبر تقني:
{original_title}
رجاءً لخص العنوان إلى عنوان صحفي جذاب باللغة العربية لا يتعدى 9 كلمات فقط.
يجب أن يحتوي العنوان فقط على كلمات عربية أو إنجليزية بدون أي رموز أو علامات ترقيم مثل (، . : * - _ " ' ! ؟) أو أرقام أو رموز خاصة أخرى.
لا تضف أي علامات أو رموز، فقط الكلمات مفصولة بمسافات."""
            arabic_title = gemini_ask(prompt_title)
            if arabic_title:
                break
            print(f"فشل تلخيص العنوان، محاولة {attempt+1}/10...")
        else:
            print("فشل تلخيص العنوان بعد 10 محاولات. إيقاف البرنامج.")
            return

        arabic_body = None
        for attempt in range(10):
            prompt_body = f"""النص التالي هو خبر تقني:
{description}
رجاءً لخص الخبر إلى فقرتين أو ثلاث فقرات تسرد كل ما يخص الموضوع باللغة العربية، مع الحفاظ على الأسلوب الصحفي الجذاب والواضح. لا تكرر العنوان ولا تضف عناوين فرعية."""
            arabic_body = gemini_ask(prompt_body)
            if arabic_body:
                break
            print(f"فشل تلخيص الخبر، محاولة {attempt+1}/10...")
        else:
            print("فشل تلخيص الخبر بعد 10 محاولات. إيقاف البرنامج.")
            return

        category = detect_category(arabic_body)

        filename = sanitize_filename(arabic_title or original_title) + ".md"
        filepath = os.path.join(NEWS_DIR, filename)
        if not os.path.exists(filepath):
            md = make_markdown(arabic_title, image, date, arabic_body, category)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"تم إنشاء: {filepath}")

        html_link = f"{SITE_URL}/news/{os.path.splitext(filename)[0]}.html"
        append_to_feed_xml(arabic_title, html_link, image)

        write_last_post(link)

if __name__ == "__main__":
    main()
