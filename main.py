import os
import time
import feedparser
import requests
from datetime import datetime
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

# إعدادات عامة
RSS_URL = "https://feed.alternativeto.net/news/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyDMAkyhm5eoo-pWfrkf-0MnAy_h26WX2sw"  # ضع مفتاحك هنا أو في متغير بيئة
NEWS_DIR = "news"
LASTPOST_FILE = os.path.join(NEWS_DIR, "lastpost.txt")
FEED_FILE = os.path.join(NEWS_DIR, "feed.xml")
SITE_URL = "https://bidjadraft.github.io"
TEMP_DIR = "temp"

os.makedirs(NEWS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# روابط رفع وتحليل الصور
UPLOAD_START_URL = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# --- دوال Gemini API لتحليل الصورة ---

def start_upload_session(file_path, mime_type):
    file_size = os.path.getsize(file_path)
    metadata = {"file": {"displayName": os.path.basename(file_path)}}
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json"
    }
    response = requests.post(UPLOAD_START_URL, headers=headers, json=metadata)
    if response.status_code != 200:
        print("فشل بدء جلسة الرفع:", response.text)
        return None
    return response.headers.get("X-Goog-Upload-URL")

def upload_file_data(upload_url, file_path, mime_type):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        data = f.read()
    headers = {
        "X-Goog-Upload-Command": "upload, finalize",
        "X-Goog-Upload-Offset": "0",
        "Content-Type": mime_type,
        "Content-Length": str(file_size)
    }
    response = requests.post(upload_url, headers=headers, data=data)
    if response.status_code != 200:
        print("فشل رفع الملف:", response.text)
        return None
    file_info = response.json()
    return file_info.get("file", {}).get("uri")

def send_request_to_gemini(file_uri, mime_type):
    prompt_text = "هل تحتوي هذه الصورة على امرأة أو بنت أو فتاة أو طفلة؟ أجب بنعم أو لا فقط بدون أي تفاصيل."
    prompt = f"أجبني باللغة العربية وبأسلوب واضح ومفهوم:\n\n{prompt_text}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "fileData": {
                            "fileUri": file_uri,
                            "mimeType": mime_type
                        }
                    }
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(GEMINI_URL, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "لم أتمكن من فهم الرد من Gemini."
    else:
        return f"خطأ في Gemini API: {response.status_code}"

def analyze_image_from_url(url):
    parsed_url = urlparse(url)
    ext = os.path.splitext(parsed_url.path)[1].lower()
    if parsed_url.scheme not in ["http", "https"] or ext not in [".jpg", ".jpeg", ".png"]:
        return "الرابط غير صالح. الرجاء استخدام رابط مباشر لصورة jpg أو jpeg أو png."

    filename = os.path.basename(parsed_url.path)
    file_path = os.path.join(TEMP_DIR, filename)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        return f"فشل تحميل الصورة من الرابط: {e}"

    mime_type = f"image/{'jpeg' if ext in ['.jpg', '.jpeg'] else 'png'}"
    upload_url = start_upload_session(file_path, mime_type)
    if not upload_url:
        os.remove(file_path)
        return "فشل بدء رفع الصورة إلى Google AI."

    file_uri = upload_file_data(upload_url, file_path, mime_type)
    if not file_uri:
        os.remove(file_path)
        return "فشل رفع بيانات الصورة إلى Google AI."

    response = send_request_to_gemini(file_uri, mime_type)
    os.remove(file_path)
    return response

# --- دوال السكربت الأصلي ---

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

def make_markdown(title, image, date, body):
    category = "التقنية"
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

# --- الدالة الرئيسية مع دمج تحليل الصورة ---

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
        date = entry.get('published', '')[:10] or datetime.now().strftime('%Y-%m-%d')

        # استخراج الصورة
        image = None
        if 'media_content' in entry and len(entry.media_content) > 0:
            image = entry.media_content[0]['url']
        elif 'enclosures' in entry and len(entry.enclosures) > 0:
            image = entry.enclosures[0]['url']
        if not image:
            image = "https://via.placeholder.com/600x400.png?text=No+Image"

        # تحليل الصورة
        analysis_result = analyze_image_from_url(image)
        print(f"نتيجة تحليل الصورة: {analysis_result}")

        if "نعم" in analysis_result:
            # استبدال الصورة برابط صورة مناسبة حسب الموضوع
            lower_title = original_title.lower()
            if "ذكاء اصطناعي" in lower_title or "ai" in lower_title:
                image = "https://example.com/ai-replacement-image.jpg"
            elif "تطبيق" in lower_title or "app" in lower_title:
                image = "https://example.com/app-replacement-image.jpg"
            else:
                image = "https://example.com/default-replacement-image.jpg"
            print("الصورة تحتوي على امرأة، تم استبدال الصورة. لن يتم إنشاء ملف md لهذا الخبر.")
            # لا يتم إنشاء ملف md ولا إضافة الخبر إلى feed.xml
            # تحديث آخر منشور لتجنب التكرار
            write_last_post(link)
            continue

        # تلخيص العنوان
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

        # تلخيص الخبر
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

        # إنشاء ملف md
        filename = sanitize_filename(arabic_title or original_title) + ".md"
        filepath = os.path.join(NEWS_DIR, filename)
        if not os.path.exists(filepath):
            md = make_markdown(arabic_title, image, date, arabic_body)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"تم إنشاء: {filepath}")

        # إنشاء الرابط
        html_link = f"{SITE_URL}/news/{os.path.splitext(filename)[0]}.html"
        # إضافة الخبر مباشرة إلى feed.xml
        append_to_feed_xml(arabic_title, html_link, image)

        # تحديث آخر منشور
        write_last_post(link)

if __name__ == "__main__":
    main()
