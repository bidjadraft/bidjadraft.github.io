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
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    meta = {}
    match = re.search(r'^---(.*?)---', content, re.DOTALL | re.MULTILINE)
    if match:
        for line in match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip().strip('"')
    return meta

def update_feed_xml():
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "أخبار مدونتي"
    ET.SubElement(channel, 'link').text = f"{SITE_URL}/news/"
    ET.SubElement(channel, 'description').text = "تحديثات الأخبار التقنية"

    md_files = sorted(glob.glob(os.path.join(NEWS_DIR, "*.md")), reverse=True)
    for md_file in md_files:
        meta = extract_md_meta(md_file)
        title = meta.get("title", "بدون عنوان")
        image = meta.get("image", "")
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

def update_sitemap_xml():
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    md_files = sorted(glob.glob(os.path.join(NEWS_DIR, "*.md")))
    for md_file in md_files:
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = f"{SITE_URL}/news/{base_name}.html"

        # محاولة استخراج تاريخ التحديث من ملف الميتا أو من تاريخ تعديل الملف
        meta = extract_md_meta(md_file)
        lastmod_str = meta.get("date", None)  # نفترض وجود حقل date في الميتا
        if lastmod_str:
            try:
                # تحويل التاريخ إلى صيغة ISO 8601 (YYYY-MM-DD)
                lastmod_date = datetime.fromisoformat(lastmod_str)
                lastmod = ET.SubElement(url, 'lastmod')
                lastmod.text = lastmod_date.date().isoformat()
            except ValueError:
                pass
        else:
            # استخدام تاريخ تعديل الملف كبديل
            mtime = os.path.getmtime(md_file)
            lastmod = ET.SubElement(url, 'lastmod')
            lastmod.text = datetime.utcfromtimestamp(mtime).date().isoformat()

        # يمكن إضافة أولوية أو تكرار التحديث هنا إذا أردت

    tree = ET.ElementTree(urlset)
    tree.write(SITEMAP_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث {SITEMAP_FILE}")

if __name__ == "__main__":
    update_feed_xml()
    update_sitemap_xml()
