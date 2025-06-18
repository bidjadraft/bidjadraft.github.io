import os
import re
import requests

NEWS_DIR = "news"
GEMINI_API_URL = "https://api.generativelanguage.googleapis.com/v1beta2/models/gemini-1-5-turbo/chat:generate"
API_KEY = "YOUR_GEMINI_API_KEY"  # استبدلها بمفتاحك

CATEGORIES = ["تطبيقات", "أجهزة", "أنظمة", "تواصل اجتماعي", "ذكاء اصطناعي"]

def read_md_file(md_path):
    with open(md_path, encoding="utf-8") as f:
        return f.read()

def write_md_file(md_path, content):
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

def extract_front_matter(content):
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    else:
        return None, content

def parse_front_matter(fm_text):
    meta = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta

def build_front_matter(meta):
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: \"{v}\"")
    lines.append("---\n")
    return "\n".join(lines)

def call_gemini_api(text):
    prompt = f"""
حدد فئة المقال من القائمة التالية: تطبيقات، أجهزة، أنظمة، تواصل اجتماعي، ذكاء اصطناعي.
المقال التالي:\n{text}\n
أعطني فقط اسم الفئة المناسبة من القائمة بناءً على محتوى المقال.
"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    data = {
        "model": "gemini-1-5-turbo",
        "temperature": 0,
        "candidate_count": 1,
        "prompt": {
            "messages": [
                {"author": "user", "content": prompt}
            ]
        }
    }
    response = requests.post(GEMINI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    # استخرج الرد من JSON حسب هيكل API
    try:
        content = result['candidates'][0]['content'].strip()
        # أحيانًا قد يعيد النص مع علامات اقتباس أو غيرها، ننظفها:
        content = re.sub(r'["\']', '', content)
        if content in CATEGORIES:
            return content
        else:
            return None
    except Exception as e:
        print("خطأ في استخراج الفئة من الرد:", e)
        return None

def update_category_in_md(md_path):
    content = read_md_file(md_path)
    fm_text, body = extract_front_matter(content)
    if fm_text is None:
        print(f"ملف {md_path} لا يحتوي على front matter صالح.")
        return
    meta = parse_front_matter(fm_text)

    # استخدم فقط أول 1000 حرف من المقال لتقليل حجم الطلب
    snippet = body[:1000]

    category = call_gemini_api(snippet)
    if category:
        print(f"تحديد الفئة للمقال {md_path}: {category}")
        meta['category'] = category
        new_fm = build_front_matter(meta)
        new_content = new_fm + body
        write_md_file(md_path, new_content)
    else:
        print(f"لم يتم تحديد فئة واضحة للمقال {md_path}")

def main():
    md_files = [os.path.join(NEWS_DIR, f) for f in os.listdir(NEWS_DIR) if f.endswith(".md")]
    for md_file in md_files:
        update_category_in_md(md_file)

if __name__ == "__main__":
    main()
