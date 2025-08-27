#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch crawler: read URLs from url.txt, force English, extract minimal fields and save one JSON per URL.
Fields: embedUrl, contentUrl, thumbnailUrl, country, city, title (English)
"""

import json
import time
from datetime import datetime
from pathlib import Path
import unicodedata

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

URL_FILE = Path('url.txt')


def strip_accents(text: str) -> str:
    try:
        text = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in text if not unicodedata.combining(c))
    except Exception:
        return text


def infer_country(url: str, breadcrumbs: list) -> str:
    try:
        for trail in breadcrumbs or []:
            for crumb in trail:
                title_attr = str(crumb.get('title', '')).strip()
                href = str(crumb.get('url', ''))
                # Country anchor: /countries/<country>/ (exact two segments after base)
                if href.startswith('/countries/') and href.count('/') == 2:
                    if title_attr:
                        return title_attr
                    # Fallback to slug
                    from urllib.parse import urlparse
                    parts = urlparse(href).path.strip('/').split('/')
                    if len(parts) >= 2:
                        return parts[1].replace('-', ' ').title()
    except Exception:
        pass
    # Fallback from URL
    try:
        from urllib.parse import urlparse
        parts = urlparse(url).path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'countries':
            return parts[1].replace('-', ' ').title()
    except Exception:
        pass
    return ''


def infer_city(result_title: str, url: str, breadcrumbs: list) -> str:
    # Prefer breadcrumbs city title anchor under /countries/<country>/<city>/
    try:
        for trail in breadcrumbs or []:
            for crumb in trail:
                title_attr = strip_accents(str(crumb.get('title', '') or '')).strip()
                href = str(crumb.get('url', ''))
                if href.startswith('/countries/') and href.count('/') >= 3 and href.rstrip('/') not in ['/countries', '/countries/']:
                    if title_attr:
                        return title_attr
                    # fallback slug
                    from urllib.parse import urlparse
                    parts = urlparse(href).path.strip('/').split('/')
                    if len(parts) >= 3:
                        return parts[2].replace('-', ' ').title()
    except Exception:
        pass
    # Fallback from URL
    try:
        from urllib.parse import urlparse
        parts = urlparse(url).path.strip('/').split('/')
        if len(parts) >= 3 and parts[0] == 'countries':
            return parts[2].replace('-', ' ').title()
    except Exception:
        pass
    return ''


def extract_minimal(driver, url: str) -> dict:
    # Navigate to English URL
    if '/vi/' in url:
        url_to_visit = url.replace('/vi/', '/en/')
    elif '/en/' not in url:
        url_to_visit = url
    else:
        url_to_visit = url

    driver.get(url_to_visit)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(2)

    # No scroll/zoom; parse directly after short wait

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Title: prefer h1.page-heading
    title = ''
    h1 = soup.find('h1', class_='page-heading')
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    else:
        ttag = soup.find('title')
        if ttag:
            title = ttag.get_text(strip=True)

    # Breadcrumbs (optional, for country/city inference)
    breadcrumbs = []
    try:
        navs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
        for nav in navs:
            trail = []
            for a in nav.find_all('a'):
                trail.append({
                    'text': a.get_text(strip=True),
                    'url': a.get('href', ''),
                    'title': a.get('title', '')
                })
            if trail:
                breadcrumbs.append(trail)
    except Exception:
        pass

    # JSON-LD for YouTube
    embed = ''
    content = ''
    thumb = ''
    for script in soup.find_all('script', type='application/ld+json'):
        text = (script.string or script.get_text() or '').strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue

        def _harvest(obj):
            nonlocal embed, content, thumb
            if not isinstance(obj, dict):
                return
            embed = embed or obj.get('embedUrl', '')
            content = content or obj.get('contentUrl', '')
            tu = obj.get('thumbnailUrl')
            if isinstance(tu, list):
                if tu:
                    thumb = thumb or tu[0]
            elif isinstance(tu, str):
                thumb = thumb or tu
            if '@graph' in obj and isinstance(obj['@graph'], list):
                for it in obj['@graph']:
                    _harvest(it)

        if isinstance(data, dict):
            _harvest(data)
        elif isinstance(data, list):
            for item in data:
                _harvest(item)

    # Fallback YouTube from iframes
    if not embed or not content:
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'youtu.be' in src or 'youtube-nocookie.com' in src:
                if not embed:
                    embed = src
                if '/embed/' in src and not content:
                    vid = src.split('/embed/')[-1].split('?')[0]
                    content = f'https://www.youtube.com/watch?v={vid}'
                break

    # Fallback thumbnail from meta tags if still missing
    if not thumb:
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and og_image.get('content'):
            thumb = og_image.get('content')
        else:
            tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if tw_image and tw_image.get('content'):
                thumb = tw_image.get('content')

    country = infer_country(url_to_visit, breadcrumbs)
    city = infer_city(title, url_to_visit, breadcrumbs)
    if not city:
        city = country

    return {
        'embedUrl': embed,
        'contentUrl': content,
        'thumbnailUrl': thumb,
        'country': country,
        'city': city,
        'title': title,
    }


def main():
    # Chrome options (English)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--lang=en-US')
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en-US,en'})
    ua = UserAgent()
    chrome_options.add_argument(f'--user-agent={ua.random}')

    urls = []
    if URL_FILE.exists():
        urls = [line.strip() for line in URL_FILE.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not urls:
        print('No URLs found in url.txt')
        return

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        for url in urls:
            print(f'Processing: {url}')
            try:
                data = extract_minimal(driver, url)
                # Skip if no URL (embed/content)
                if not (data.get('embedUrl') or data.get('contentUrl')):
                    print('  -> Skip: no embed/content URL')
                    continue

                safe_country = (data.get('country') or 'Unknown').strip().replace(' ', '_')
                out_file = f'{safe_country}.json'
                # Append/merge per country file
                try:
                    if Path(out_file).exists():
                        try:
                            existing = json.loads(Path(out_file).read_text(encoding='utf-8'))
                        except Exception:
                            existing = None
                        merged = None
                        if isinstance(existing, list):
                            # Remove old entries without URL
                            existing = [it for it in existing if isinstance(it, dict) and (it.get('embedUrl') or it.get('contentUrl'))]
                            keys = {(item.get('embedUrl'), item.get('title')) for item in existing if isinstance(item, dict)}
                            if (data.get('embedUrl'), data.get('title')) not in keys and (data.get('embedUrl') or data.get('contentUrl')):
                                existing.append(data)
                            merged = existing
                        elif isinstance(existing, dict) and existing:
                            # If the old dict does not have a URL, skip it
                            merged = [existing] if (existing.get('embedUrl') or existing.get('contentUrl')) else []
                            if (data.get('embedUrl') or data.get('contentUrl')) and not (existing.get('embedUrl') == data.get('embedUrl') and existing.get('title') == data.get('title')):
                                merged.append(data)
                        else:
                            merged = [data]
                        Path(out_file).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
                    else:
                        Path(out_file).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(f'  -> Saved {out_file}')
                except Exception as e:
                    print(f'  !! Failed to write {out_file}: {e}')
            except Exception as e:
                print(f'  !! Failed {url}: {e}')
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()
