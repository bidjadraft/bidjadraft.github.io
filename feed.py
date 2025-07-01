import os
import glob
import re
from datetime import datetime
import xml.etree.ElementTree as ET

NEWS_DIR = "news"
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

def get_file_date(md_file):
    meta = extract_md_meta(md_file)
    # استخدم تاريخ النشر من الميتاداتا أو تاريخ آخر تعديل للملف
    date_str = meta.get("date")
    if date_str:
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            pass
    return datetime.fromtimestamp(os.path.getmtime(md_file))

def update_sitemap_xml():
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # الصفحة الرئيسية
    url = ET.SubElement(urlset, 'url')
    ET.SubElement(url, 'loc').text = f"{SITE_URL}/"
    ET.SubElement(url, 'lastmod').text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(url, 'changefreq').text = "weekly"
    ET.SubElement(url, 'priority').text = "1.0"

    # جمع كل الملفات مع تاريخها
    md_files = glob.glob(os.path.join(NEWS_DIR, "*.md"))
    files_with_dates = [(md_file, get_file_date(md_file)) for md_file in md_files]
    # فرز تنازلي (من الأحدث إلى الأقدم)
    files_with_dates.sort(key=lambda x: x[1], reverse=True)

    for md_file, file_date in files_with_dates:
        meta = extract_md_meta(md_file)
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        link = f"{SITE_URL}/news/{base_name}.html"
        lastmod = file_date.strftime("%Y-%m-%d")

        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = link
        ET.SubElement(url, 'lastmod').text = lastmod
        ET.SubElement(url, 'changefreq').text = "monthly"
        ET.SubElement(url, 'priority').text = "0.8"

    tree = ET.ElementTree(urlset)
    tree.write(SITEMAP_FILE, encoding='utf-8', xml_declaration=True)
    print(f"تم إنشاء {SITEMAP_FILE} ({len(md_files)+1} صفحة)")

if __name__ == "__main__":
    update_sitemap_xml()
