#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler with coordinates: extract minimal fields + camera coordinates (lat/lng)
Saves one JSON per URL named as Country_City.json (country and city derived from breadcrumbs/URL)
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _strip_accents(text: str) -> str:
    import unicodedata
    try:
        text = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in text if not unicodedata.combining(c))
    except Exception:
        return text


def _derive_key_mapping(thumbnail_url: str) -> str:
    if isinstance(thumbnail_url, str) and '/thumbnail' in thumbnail_url:
        return thumbnail_url.split('/thumbnail')[0] + '/thumbnail'
    return ''


def _infer_country_and_city(url: str, soup: BeautifulSoup) -> Dict[str, str]:
    country = ''
    city = ''
    # Collect breadcrumbs
    try:
        breadcrumbs: List[List[Dict[str, str]]] = []
        navs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
        for nav in navs:
            trail: List[Dict[str, str]] = []
            for a in nav.find_all('a'):
                trail.append({'text': a.get_text(strip=True), 'url': a.get('href', ''), 'title': a.get('title', '')})
            if trail:
                breadcrumbs.append(trail)
        from urllib.parse import urlparse
        # country
        try:
            for trail in breadcrumbs:
                for crumb in trail:
                    href = str(crumb.get('url', ''))
                    title_attr = str(crumb.get('title', '')).strip()
                    parts = urlparse(href).path.strip('/').split('/')
                    if len(parts) == 2 and parts[0] == 'countries':
                        country = title_attr or parts[1].replace('-', ' ').title()
                        raise StopIteration
        except StopIteration:
            pass
        if not country:
            parts = urlparse(url).path.strip('/').split('/')
            if len(parts) >= 2 and parts[0] == 'countries':
                country = parts[1].replace('-', ' ').title()
        # city
        try:
            for trail in breadcrumbs:
                for crumb in trail:
                    href = str(crumb.get('url', ''))
                    title_attr = str(crumb.get('title', '')).strip()
                    parts = urlparse(href).path.strip('/').split('/')
                    if len(parts) == 3 and parts[0] == 'countries':
                        city = title_attr or parts[2].replace('-', ' ').title()
                        raise StopIteration
        except StopIteration:
            pass
        if not city:
            parts = urlparse(url).path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'countries':
                city = parts[2].replace('-', ' ').title()
        if not city:
            city = country
    except Exception:
        pass
    return {'country': country, 'city': city}


def extract_minimal_with_coords(driver, url: str) -> Dict[str, Any]:
    # Normalize URL
    raw = (url or '').strip()
    # Remove leading markers like '@' or surrounding quotes/spaces
    while raw.startswith('@'):
        raw = raw[1:]
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1]
    # Force English if needed
    if '/vi/' in raw:
        url_to_visit = url.replace('/vi/', '/en/')
    else:
        url_to_visit = raw

    # Validate URL
    if not (url_to_visit.startswith('http://') or url_to_visit.startswith('https://')):
        raise ValueError(f'Invalid URL scheme: {url_to_visit}')

    # Navigate
    driver.get(url_to_visit)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    title_text = ''
    h1 = soup.find('h1', class_='page-heading')
    if h1 and h1.get_text(strip=True):
        title_text = h1.get_text(strip=True)
    else:
        t = soup.find('title')
        if t:
            title_text = t.get_text(strip=True)

    # JSON-LD capture for YouTube + thumbnails
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
        def harvest(obj: Dict[str, Any]):
            nonlocal embed, content, thumb
            if not isinstance(obj, dict):
                return
            if not embed and obj.get('embedUrl'):
                embed = obj.get('embedUrl')
            if not content and obj.get('contentUrl'):
                content = obj.get('contentUrl')
            tu = obj.get('thumbnailUrl')
            if isinstance(tu, list) and tu:
                thumb = thumb or tu[0]
            elif isinstance(tu, str):
                thumb = thumb or tu
            if isinstance(obj.get('@graph'), list):
                for it in obj['@graph']:
                    harvest(it)
        if isinstance(data, dict):
            harvest(data)
        elif isinstance(data, list):
            for it in data:
                harvest(it)

    # Fallback thumbnail
    if not thumb:
        og = soup.find('meta', attrs={'property': 'og:image'})
        if og and og.get('content'):
            thumb = og.get('content')
        else:
            tw = soup.find('meta', attrs={'name': 'twitter:image'})
            if tw and tw.get('content'):
                thumb = tw.get('content')

    # Derive country/city
    cc = _infer_country_and_city(url_to_visit, soup)
    country = cc.get('country') or ''
    city = cc.get('city') or country

    # Extract coordinates by scanning scripts for patterns like {"lat":..., "lng":..., "active":true}
    lat = ''
    lng = ''
    try:
        import re
        scripts = soup.find_all('script')
        # Patterns to match coordinates in various forms (unescaped/escaped JSON, JS vars)
        coord_patterns = [
            # JSON with active flag (unescaped)
            r'\{\s*"lat"\s*:\s*([\-0-9\.]+)\s*,\s*"lng"\s*:\s*([\-0-9\.]+)\s*,\s*"active"\s*:\s*(?:true|false)\s*\}',
            # JSON with lat then lng (unescaped)
            r'"lat"\s*:\s*([\-0-9\.]+)\s*,\s*"lng"\s*:\s*([\-0-9\.]+)',
            # JSON with lng then lat (unescaped)
            r'"lng"\s*:\s*([\-0-9\.]+)\s*,\s*"lat"\s*:\s*([\-0-9\.]+)',
            # Escaped JSON inside strings (lat then lng)
            r'\\"lat\\"\s*:\s*([\-0-9\.]+)[^\n\r]*?\\"lng\\"\s*:\s*([\-0-9\.]+)',
            # Escaped JSON inside strings (lng then lat)
            r'\\"lng\\"\s*:\s*([\-0-9\.]+)[^\n\r]*?\\"lat\\"\s*:\s*([\-0-9\.]+)',
            # JS assignments/objects
            r'lat\s*[:=]\s*([\-0-9\.]+)[,\s]+lng\s*[:=]\s*([\-0-9\.]+)',
            # Alternate keys
            r'"latitude"\s*:\s*([\-0-9\.]+)\s*,\s*"longitude"\s*:\s*([\-0-9\.]+)',
            r'\\"latitude\\"\s*:\s*([\-0-9\.]+)\s*,\s*\\"longitude\\"\s*:\s*([\-0-9\.]+)'
        ]
        for i, sc in enumerate(scripts):
            text = sc.string or sc.get_text()
            if not text:
                continue
            # Print any script content that contains 'lat"' (escaped) or "lat"
            try:
                if ('lat\\"' in text) or ('"lat"' in text):
                    pass
            except Exception:
                pass
            for idx, pat in enumerate(coord_patterns):
                m = re.search(pat, text)
                if m:
                    # For patterns that captured lng first (indices 2 and 4), swap
                    if idx in (2, 4):
                        lng, lat = m.group(1), m.group(2)
                    else:
                        lat, lng = m.group(1), m.group(2)
                    print(f"Coordinates captured from script #{i}: lat={lat}, lng={lng}")
                    break
            if lat and lng:
                break
        # As a final fallback, search the full HTML once
        if not (lat and lng):
            page = str(soup)
            m = re.search(r'"lat"\s*:\s*([\-0-9\.]+)[^\n\r]{0,200}?"lng"\s*:\s*([\-0-9\.]+)', page)
            if m:
                lat, lng = m.group(1), m.group(2)
                print(f"Coordinates captured from page fallback: lat={lat}, lng={lng}")
    except Exception:
        pass

    key_mapping_data = _derive_key_mapping(thumb)

    return {
        'url': url_to_visit,
        'embedUrl': embed,
        'contentUrl': content,
        'thumbnailUrl': thumb,
        'key_mapping_data': key_mapping_data,
        'country': country,
        'city': city,
        'title': title_text,
        'coordinates': {'lat': lat, 'lng': lng}
    }


def main():
    from argparse import ArgumentParser
    p = ArgumentParser(description='Crawler with coordinates (per URL -> Country_City.json)')
    p.add_argument('--urls', default='url.txt', help='File containing URLs list (default: url.txt)')
    p.add_argument('--urls-dir', default='cam_urls', help='Directory containing *.txt files with URLs (one per line)')
    args = p.parse_args()

    urls: List[str] = []
    # Prefer directory of URL files if present
    urls_dir = Path(args.urls_dir)
    if urls_dir.exists() and urls_dir.is_dir():
        txt_files = sorted(urls_dir.glob('*.txt'))
        total_in_dir = 0
        for fp in txt_files:
            try:
                lines = [u.strip() for u in fp.read_text(encoding='utf-8').splitlines() if u.strip()]
                urls.extend(lines)
                total_in_dir += len(lines)
            except Exception as e:
                print(f"Skip {fp.name}: {e}")
        if not urls:
            print(f"❌ No URLs found in {urls_dir}")
            return
        print(f"Found {len(txt_files)} URL files in {urls_dir}, total URLs: {total_in_dir}")
    else:
        try:
            urls = [u.strip() for u in Path(args.urls).read_text(encoding='utf-8').splitlines() if u.strip()]
        except FileNotFoundError:
            print('❌ url.txt not found')
            return

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

    driver = webdriver.Chrome(options=chrome_options)
    try:
        total = len(urls)
        print(f'Total URLs to crawl: {total}')
        for idx, url in enumerate(urls, start=1):
            print(f'Processing ({idx}/{total}): {url}')
            # Normalize quick here too (for logging clarity and early skip)
            url_norm = url.strip().lstrip('@').strip('"').strip("'")
            if not (url_norm.startswith('http://') or url_norm.startswith('https://')):
                print(f'  -> Skip: invalid URL scheme ({url})')
                continue
            try:
                data = extract_minimal_with_coords(driver, url_norm)
            except Exception as e:
                print(f'  -> Skip: navigation/extract error: {e}')
                continue
            from urllib.parse import urlparse
            # Skip non-YouTube contentUrl
            content_url = (data or {}).get('contentUrl') or ''
            if not content_url:
                print(f'  -> Skip: no contentUrl ({idx}/{total})')
                continue
            host = urlparse(content_url).netloc.lower()
            if not any(d in host for d in ['youtube.com', 'youtu.be', 'youtube-nocookie.com']):
                print(f"  -> Skip: contentUrl not YouTube ({host}) ({idx}/{total})")
                continue
            # ensure country/city safe naming
            safe_country = (data.get('country') or 'Unknown').strip().replace(' ', '_')
            safe_city = (data.get('city') or safe_country).strip().replace(' ', '_')
            out_file = f'{safe_country}_Location.json'
            # Merge logic: append if file exists and is list; if dict, convert to list and dedupe
            try:
                pth = Path(out_file)
                if pth.exists():
                    try:
                        existing = json.loads(pth.read_text(encoding='utf-8'))
                    except Exception:
                        existing = None
                    merged: List[Dict[str, Any]]
                    if isinstance(existing, list):
                        keys = {(item.get('embedUrl'), item.get('title')) for item in existing if isinstance(item, dict)}
                        if (data.get('embedUrl'), data.get('title')) not in keys and (data.get('embedUrl') or data.get('contentUrl')):
                            existing.append(data)
                        merged = existing
                    elif isinstance(existing, dict) and existing:
                        merged = [existing] if (existing.get('embedUrl') or existing.get('contentUrl')) else []
                        if (data.get('embedUrl') or data.get('contentUrl')) and not (existing.get('embedUrl') == data.get('embedUrl') and existing.get('title') == data.get('title')):
                            merged.append(data)
                    else:
                        merged = [data]
                    pth.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
                else:
                    pth.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                Path(out_file).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'  -> Saved {out_file} ({idx}/{total})')
    finally:
        driver.quit()
    print('🎉 Done.')


if __name__ == '__main__':
    main()


