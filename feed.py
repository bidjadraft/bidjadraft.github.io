import os
import glob
import re
from datetime import datetime
import xml.etree.ElementTree as ET

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

def generate_feed_and_sitemap():
    # إعداد feed.xml
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "أخبار مدونتي"
    ET.SubElement(channel, 'link').text = f"{SITE_URL}/news/"
    ET.SubElement(channel, 'description').text = "تحديثات الأخبار التقنية"

    # إعداد sitemap.xml
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    # أضف الصفحة الرئيسية
    url = ET.SubElement(urlset, 'url')
    ET.SubElement(url, 'loc').text = f"{SITE_URL}/"
    ET.SubElement(url, 'lastmod').text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(url, 'changefreq').text = "weekly"
    ET.SubElement(url, 'priority').text = "1.0"

    md_files = sorted(glob.glob(os.path.join(NEWS_DIR, "*.md")), reverse=True)
    for md_file in md_files:
        meta = extract_md_meta(md_file)
        title = meta.get("title", "بدون عنوان")
        image = meta.get("image", "")
        date = meta.get("date") or datetime.fromtimestamp(os.path.getmtime(md_file)).strftime("%Y-%m-%d")
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        link = f"{SITE_URL}/news/{base_name}.html"

        # أضف إلى feed.xml
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'link').text = link
        if image:
            ext = os.path.splitext(image)[-1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/webp"
            ET.SubElement(item, 'enclosure', url=image, type=mime)

        # أضف إلى sitemap.xml
        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = link
        ET.SubElement(url, 'lastmod').text = date
        ET.SubElement(url, 'changefreq').text = "monthly"
        ET.SubElement(url, 'priority').text = "0.8"

    # حفظ feed.xml
    tree_feed = ET.ElementTree(rss)
    tree_feed.write(FEED_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث {FEED_FILE}")

    # حفظ sitemap.xml
    tree_sitemap = ET.ElementTree(urlset)
    tree_sitemap.write(SITEMAP_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم تحديث {SITEMAP_FILE}")

if __name__ == "__main__":
    generate_feed_and_sitemap()
