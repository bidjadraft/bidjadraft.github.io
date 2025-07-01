import os
import glob
import re
import xml.etree.ElementTree as ET
from datetime import datetime

NEWS_DIR = "news"
FEED_FILE = "feed.xml"
SITEMAP_FILE = "sitemap.xml"
SITE_URL = "https://bidjadraft.github.io"

def extract_md_meta(md_path):
    """
    استخراج بيانات الميتا من ملف Markdown.
    يفترض أن الميتا بين --- في بداية الملف.
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    meta = {}
    match = re.search(r'^---(.*?)---', content, re.DOTALL | re.MULTILINE)
    if match:
        for line in match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta

def update_feed_xml():
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "أخبار مدونتي"
    ET.SubElement(channel, 'link').text = f"{SITE_URL}/news/"
    ET.SubElement(channel, 'description').text = "تحديثات الأخبار التقنية"

    md_files = glob.glob(os.path.join(NEWS_DIR, "*.md"))

    # بناء قائمة (ملف, تاريخ) مع استخراج التاريخ
    files_with_dates = []
    for md_file in md_files:
        meta = extract_md_meta(md_file)
        date_str = meta.get("date", None)
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str)
            except ValueError:
                date_obj = datetime.min
        else:
            date_obj = datetime.min
        files_with_dates.append((md_file, date_obj))

    # ترتيب تنازلي حسب التاريخ (الأحدث أولاً)
    files_with_dates.sort(key=lambda x: x[1], reverse=True)

    for md_file, date_obj in files_with_dates:
        meta = extract_md_meta(md_file)
        title = meta.get("title", "بدون عنوان")
        image = meta.get("image", "")
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        link = f"{SITE_URL}/news/{base_name}.html"

        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'link').text = link

        # إضافة تاريخ النشر بصيغة RFC 2822 (مطلوب في RSS)
        pub_date = ET.SubElement(item, 'pubDate')
        pub_date.text = date_obj.strftime('%a, %d %b %Y %H:%M:%S +0000')

        if image:
            ext = os.path.splitext(image)[-1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/webp"
            ET.SubElement(item, 'enclosure', url=image, type=mime)

    tree = ET.ElementTree(rss)
    tree.write(FEED_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث {FEED_FILE}")

def update_sitemap_xml():
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    md_files = glob.glob(os.path.join(NEWS_DIR, "*.md"))
    for md_file in md_files:
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = f
