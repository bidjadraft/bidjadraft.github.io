import os
import glob
import re
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse

NEWS_DIR = "news"
FEED_FILE = "feed.xml"
SITE_URL = "https://bidjadraft.github.io"
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# إعدادات Gemini API (ضع مفتاحك في متغير البيئة GEMINI_API_KEY)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
UPLOAD_START_URL = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

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
            return None
    else:
        print(f"خطأ في Gemini API: {response.status_code}")
        return None

def analyze_image_from_url(url):
    parsed_url = urlparse(url)
    ext = os.path.splitext(parsed_url.path)[1].lower()
    if parsed_url.scheme not in ["http", "https"] or ext not in [".jpg", ".jpeg", ".png"]:
        print("الرابط غير صالح. الرجاء استخدام رابط مباشر لصورة jpg أو jpeg أو png.")
        return None

    filename = os.path.basename(parsed_url.path)
    file_path = os.path.join(TEMP_DIR, filename)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        print(f"فشل تحميل الصورة من الرابط: {e}")
        return None

    mime_type = f"image/{'jpeg' if ext in ['.jpg', '.jpeg'] else 'png'}"
    upload_url = start_upload_session(file_path, mime_type)
    if not upload_url:
        os.remove(file_path)
        return None

    file_uri = upload_file_data(upload_url, file_path, mime_type)
    if not file_uri:
        os.remove(file_path)
        return None

    response = send_request_to_gemini(file_uri, mime_type)
    os.remove(file_path)
    return response

def get_unsplash_image_url(topic):
    base_url = "https://source.unsplash.com/600x400/?"
    query = topic.replace(" ", ",")
    return base_url + query

def extract_md_meta(md_path):
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    meta = {}
    match = re.search(r'^---(.*?)---', content, re.DOTALL | re.MULTILINE)
    if match:
        for line in match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip().strip('"')
    return meta, content

def replace_image_in_md(md_path, new_image_url):
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r'(image:\s*")[^"]+(")', f'\\1{new_image_url}\\2', content)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def update_feed_xml():
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "أخبار مدونتي"
    ET.SubElement(channel, 'link').text = f"{SITE_URL}/news/"
    ET.SubElement(channel, 'description').text = "تحديثات الأخبار التقنية"

    md_files = sorted(glob.glob(os.path.join(NEWS_DIR, "*.md")), reverse=True)
    for md_file in md_files:
        meta, _ = extract_md_meta(md_file)
        title = meta.get("title", "بدون عنوان")
        image = meta.get("image", "")
        # تحليل الصورة
        if image:
            analysis = analyze_image_from_url(image)
            if analysis and "نعم" in analysis:
                print(f"الصورة في {md_file} تحتوي امرأة، استبدالها بصورة من Unsplash.")
                replacement = get_unsplash_image_url(title)
                replace_image_in_md(md_file, replacement)
                image = replacement
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        link = f"{SITE_URL}/news/{base_name}.html"

        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'link').text = link
        if image:
            ext = os.path.splitext(image)[-1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/webp"
            ET.SubElement(item, 'enclosure', url=image, type=mime)

    tree = ET.ElementTree(rss)
    tree.write(FEED_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث {FEED_FILE}")

if __name__ == "__main__":
    update_feed_xml()
