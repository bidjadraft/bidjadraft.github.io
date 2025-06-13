import os
import time
import feedparser
import requests
from datetime import datetime
import re
import xml.etree.ElementTree as ET

RSS_URL = "https://feed.alternativeto.net/news/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_DIR = "news"
LASTPOST_FILE = os.path.join(NEWS_DIR, "lastpost.txt")
RSS_FILE = os.path.join(NEWS_DIR, "feed.xml")
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

def sanitize_filename(text):
    text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)
    text = re.sub(r'_', '', text)
    text = re.sub(r'\s+', '-', text)
    text = text.strip('-')
    return text[:60]

def make_markdown(entry, arabic_title, arabic_body):
    title = arabic_title.strip()
    date = entry.get('published', '')[:10] or datetime.now().strftime('%Y-%m-%d')
    category = "التقنية"
    image = None
    if 'media_content' in entry and len(entry.media_content) > 0:
        image = entry.media_content[0]['url']
    elif 'enclosures' in entry and len(entry.enclosures) > 0:
        image = entry.enclosures[0]['url']
    if not image:
        image = "https://via.placeholder.com/600x400.png?text=No+Image"
    md = f"""---
layout: default
title: "{title}"
image: "{image}"
category: {category}
date: {date}
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

def load_existing_rss_links():
    if not os.path.exists(RSS_FILE):
        return set()
    try:
        tree = ET.parse(RSS_FILE)
        root = tree.getroot()
        items = root.findall('./channel/item')
        links = set()
        for item in items:
            link = item.find('link').text
            links.add(link)
        return links
    except Exception as e:
        print(f"خطأ في قراءة ملف RSS: {e}")
        return set()

def update_rss(arabic_title, pub_date, link, description):
    existing_links = load_existing_rss_links()
    if link in existing_links:
        print("الرابط موجود مسبقًا في RSS، تخطي الإضافة.")
        return

    if os.path.exists(RSS_FILE):
        tree = ET.parse(RSS_FILE)
        root = tree.getroot()
    else:
        root = ET.Element('rss', version='2.0')
        channel = ET.SubElement(root, 'channel')
        ET.SubElement(channel, 'title').text = "أخبار مدونتي"
        ET.SubElement(channel, 'link').text = SITE_URL
        ET.SubElement(channel, 'description').text = "أحدث الأخبار التقنية"
        tree = ET.ElementTree(root)

    channel = root.find('channel')
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = arabic_title
    ET.SubElement(item, 'link').text = link
    ET.SubElement(item, 'pubDate').text = pub_date
    ET.SubElement(item, 'description').text = description

    tree.write(RSS_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث ملف RSS: {RSS_FILE}")

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

        filename = sanitize_filename(arabic_title or original_title) + ".md"
        filepath = os.path.join(NEWS_DIR, filename)

        if os.path.exists(filepath):
            print(f"تم تخطي {filename} (موجود مسبقاً)")
            continue

        md = make_markdown(entry, arabic_title, arabic_body)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"تم إنشاء: {filepath}")

        # رابط HTML للمقال (نفترض أن GitHub Pages يحول md إلى html بنفس الاسم)
        html_link = f"{SITE_URL}/news/{os.path.splitext(filename)[0]}.html"

        # صيغة التاريخ لـ pubDate في RSS (RFC 2822)
        pub_date = entry.get('published', datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'))

        # تحديث ملف RSS
        update_rss(arabic_title, pub_date, html_link, arabic_body)

        # تحديث آخر منشور فقط بعد نجاح إنشاء الملف
        write_last_post(link)

if __name__ == "__main__":
    main()
