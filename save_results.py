#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to crawl and save results with full information
"""

import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import unicodedata

def crawl_and_save_results():
    """Crawl data and save results"""
    print("💾 === CRAWL AND SAVE RESULTS ===")
    
    # Test URL
    url = "https://webcamera24.com/camera/austria/radstadt-cow-sanctuary-cam/?_rsc=1xov6"
    print(f"URL: {url}")
    
    driver = None
    
    try:
        # Configure Chrome options
        print("\n🔄 Configuring Chrome options...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        # Force English locale for requests and rendering
        chrome_options.add_argument('--lang=en-US')
        chrome_prefs = {
            'intl.accept_languages': 'en-US,en'
        }
        chrome_options.add_experimental_option('prefs', chrome_prefs)
        
        # User agent
        ua = UserAgent()
        chrome_options.add_argument(f'--user-agent={ua.random}')
        
        # Initialize WebDriver
        print("🚗 Initializing WebDriver...")
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("✅ ChromeDriver initialized successfully")
        except Exception as e:
            print(f"❌ ChromeDriver failed: {e}")
            return False
        
        # Visit page (force English if URL contains /vi/)
        if '/vi/' in url:
            url_to_visit = url.replace('/vi/', '/en/')
        else:
            url_to_visit = url
        print(f"\n🌐 Visiting: {url_to_visit}")
        driver.get(url_to_visit)
        
        # Wait for page load
        print("⏳ Waiting for page to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a little for JavaScript rendering (no scroll/zoom map)
        time.sleep(2)

        # Get page source
        print("📄 Getting page source...")
        page_source = driver.page_source
        
        # Parse HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract information
        print("🔍 Extracting information...")
        
        # Build result object
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'method': 'selenium',
            'status': 'success',
            'page_info': {
                'title': '',
                'h1': '',
                'meta_description': '',
                'content_length': len(page_source)
            },
            'location': {
                'breadcrumbs': [],
                'location_from_url': '',
                'location_from_page': '',
                'coordinates': {
                    'latitude': None,
                    'longitude': None,
                    'zoom': None,
                    'source': ''
                }
            },
            'camera_info': {
                'youtube_streams': {},
                'thumbnails': [],
                'other_streams': [],
                'embed_codes': []
            },
            'map_info': {
                'openstreetmap': {},
                'google_maps': {},
                'other_maps': []
            }
        }
        
        # Extract title: prioritize h1.page-heading
        h1_heading = soup.find('h1', class_='page-heading')
        if h1_heading and h1_heading.get_text(strip=True):
            result['page_info']['title'] = h1_heading.get_text(strip=True)
            result['page_info']['h1'] = result['page_info']['title']
        else:
            # Fallback <title>
            title_tag = soup.find('title')
            if title_tag:
                result['page_info']['title'] = title_tag.get_text(strip=True)
            # Fallback any H1
            h1_tags = soup.find_all('h1')
            if h1_tags and not result['page_info']['h1']:
                result['page_info']['h1'] = h1_tags[0].get_text(strip=True)
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            result['page_info']['meta_description'] = meta_desc.get('content', '')
        
        # Extract breadcrumbs
        breadcrumbs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
        for breadcrumb in breadcrumbs:
            breadcrumb_data = []
            links = breadcrumb.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')
                breadcrumb_data.append({
                    'text': text,
                    'url': href,
                    'title': link.get('title', '')
                })
            if breadcrumb_data:
                result['location']['breadcrumbs'].append(breadcrumb_data)
        
        # Extract location from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if 'vietnam' in path_parts:
            result['location']['location_from_url'] = "Vietnam"
        if 'quang-trung' in path_parts:
            result['location']['location_from_url'] = "Quang Trung Street, Vietnam"
        
        # Extract JSON-LD data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            text = (script.string or script.get_text() or '').strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except Exception as e:
                print(f"JSON-LD parse error: {e}")
                continue

            def _harvest_from_obj(obj):
                if not isinstance(obj, dict):
                    return
                # YouTube streams
                embed = obj.get('embedUrl')
                content = obj.get('contentUrl')
                thumb = obj.get('thumbnailUrl')
                if embed and 'embedUrl' not in result['camera_info']['youtube_streams']:
                    result['camera_info']['youtube_streams']['embedUrl'] = embed
                if content and 'contentUrl' not in result['camera_info']['youtube_streams']:
                    result['camera_info']['youtube_streams']['contentUrl'] = content
                if thumb and 'thumbnailUrl' not in result['camera_info']['youtube_streams']:
                    # thumbnailUrl có thể là list hoặc str
                    if isinstance(thumb, list):
                        if thumb:
                            result['camera_info']['youtube_streams']['thumbnailUrl'] = thumb[0]
                    elif isinstance(thumb, str):
                        result['camera_info']['youtube_streams']['thumbnailUrl'] = thumb

                # Thumbnails list
                if thumb:
                    thumb_url = thumb[0] if isinstance(thumb, list) and thumb else thumb
                    if thumb_url:
                        result['camera_info']['thumbnails'].append({
                            'type': 'json_ld',
                            'url': thumb_url,
                            'source': 'thumbnailUrl'
                        })

                # Location from JSON-LD
                if 'name' in obj and not result['location']['location_from_page']:
                    result['location']['location_from_page'] = obj['name']

                # If @graph exists, traverse deeper
                if '@graph' in obj and isinstance(obj['@graph'], list):
                    for it in obj['@graph']:
                        _harvest_from_obj(it)

            if isinstance(data, dict):
                _harvest_from_obj(data)
            elif isinstance(data, list):
                for item in data:
                    _harvest_from_obj(item)
        
        # Extract YouTube iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'youtu.be' in src or 'youtube-nocookie.com' in src:
                if 'embedUrl' not in result['camera_info']['youtube_streams']:
                    result['camera_info']['youtube_streams']['embedUrl'] = src
                
                # Convert embed URL to content URL
                if '/embed/' in src:
                    video_id = src.split('/embed/')[-1].split('?')[0]
                    if 'contentUrl' not in result['camera_info']['youtube_streams']:
                        result['camera_info']['youtube_streams']['contentUrl'] = f'https://www.youtube.com/watch?v={video_id}'

        # Fallback thumbnail from meta tags if missing
        if not result['camera_info']['youtube_streams'].get('thumbnailUrl'):
            og_image = soup.find('meta', attrs={'property': 'og:image'})
            if og_image and og_image.get('content'):
                result['camera_info']['youtube_streams']['thumbnailUrl'] = og_image.get('content')
                result['camera_info']['thumbnails'].append({
                    'type': 'meta',
                    'url': og_image.get('content'),
                    'source': 'og:image'
                })
            else:
                tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
                if tw_image and tw_image.get('content'):
                    result['camera_info']['youtube_streams']['thumbnailUrl'] = tw_image.get('content')
                    result['camera_info']['thumbnails'].append({
                        'type': 'meta',
                        'url': tw_image.get('content'),
                        'source': 'twitter:image'
                    })
        
        # Extract map information and coordinates
        print("🗺️  Extracting map information...")
        map_info = extract_map_information(soup, driver)
        result['map_info'].update(map_info)
        
        # Extract coordinates from OpenStreetMap
        print("🗺️  Extracting OpenStreetMap coordinates...")
        coordinates = extract_openstreetmap_coordinates(soup, driver)
        if coordinates:
            result['location']['coordinates'].update(coordinates)
        
        # Extract coordinates from map (fallback)
        if not coordinates.get('latitude'):
            coordinates = extract_coordinates(soup, driver)
            if coordinates:
                result['location']['coordinates'].update(coordinates)
        
        # Country via breadcrumb title anchor (generic: /countries/<country>/)
        country = ''
        try:
            from urllib.parse import urlparse
            for trail in result['location'].get('breadcrumbs', []) or []:
                for crumb in trail:
                    href = str(crumb.get('url', ''))
                    title_attr = str(crumb.get('title', '')).strip()
                    parts = urlparse(href).path.strip('/').split('/')
                    # /countries/<country>/ -> len(parts)==2
                    if len(parts) == 2 and parts[0] == 'countries':
                        country = title_attr or parts[1].replace('-', ' ').title()
                        raise StopIteration
        except StopIteration:
            pass
        if not country:
            from urllib.parse import urlparse
            parts = urlparse(url).path.strip('/').split('/')
            if len(parts) >= 2 and parts[0] == 'countries':
                country = parts[1].replace('-', ' ').title()

        yt = result['camera_info'].get('youtube_streams', {})
        
        # City via breadcrumb title anchor (generic: /countries/<country>/<city>/)
        city = ''
        try:
            from urllib.parse import urlparse
            for trail in result['location'].get('breadcrumbs', []) or []:
                for crumb in trail:
                    href = str(crumb.get('url', ''))
                    title_attr = str(crumb.get('title', '')).strip()
                    parts = urlparse(href).path.strip('/').split('/')
                    # /countries/<country>/<city>/ -> len(parts)==3
                    if len(parts) == 3 and parts[0] == 'countries':
                        city = title_attr or parts[2].replace('-', ' ').title()
                        raise StopIteration
        except StopIteration:
            pass
        if not city:
            # fallback from URL path
            from urllib.parse import urlparse
            parts = urlparse(url).path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'countries':
                city = parts[2].replace('-', ' ').title()
        if not city:
            city = infer_city_english(result, url)
        # Final fallback: if still empty, use country as city
        if not city:
            city = country
        
        # Use the title taken from h1.page-heading (English when accessing /en/)
        eng_title = result['page_info'].get('title', '')
        minimal_result = {
            'embedUrl': yt.get('embedUrl', ''),
            'contentUrl': yt.get('contentUrl', ''),
            'thumbnailUrl': yt.get('thumbnailUrl', ''),
            'country': country,
            'city': city,
            'title': eng_title
        }

        # Skip if no URL (embed/content)
        if not (minimal_result.get('embedUrl') or minimal_result.get('contentUrl')):
            print("⚠️ Skip: no embedUrl/contentUrl")
            return True

        # Save result (minimal as required) with filename = country
        safe_country = (country or 'Unknown').strip().replace(' ', '_')
        filename = f"{safe_country}.json"
        print(f"\n💾 Saving results to: {filename}")
        # Avoid overwrite: if country file exists, merge into array
        try:
            import os
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as rf:
                    try:
                        existing = json.load(rf)
                    except Exception:
                        existing = None
                merged = None
                if isinstance(existing, list):
                    # Remove old entries without URL
                    existing = [it for it in existing if isinstance(it, dict) and (it.get('embedUrl') or it.get('contentUrl'))]
                    merged = existing
                    # dedupe theo embedUrl hoặc title
                    keys = {(item.get('embedUrl'), item.get('title')) for item in existing if isinstance(item, dict)}
                    if (minimal_result.get('embedUrl'), minimal_result.get('title')) not in keys and (minimal_result.get('embedUrl') or minimal_result.get('contentUrl')):
                        merged.append(minimal_result)
                elif isinstance(existing, dict) and existing:
                    # chuyển sang list
                    # Bỏ dict nếu không có URL
                    merged = [existing] if (existing.get('embedUrl') or existing.get('contentUrl')) else []
                    if (minimal_result.get('embedUrl') or minimal_result.get('contentUrl')) and not (existing.get('embedUrl') == minimal_result.get('embedUrl') and existing.get('title') == minimal_result.get('title')):
                        merged.append(minimal_result)
                else:
                    merged = [minimal_result]
                with open(filename, 'w', encoding='utf-8') as wf:
                    json.dump(merged, wf, ensure_ascii=False, indent=2)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(minimal_result, f, ensure_ascii=False, indent=2)
        except Exception:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(minimal_result, f, ensure_ascii=False, indent=2)
        
        # Display summary (minimal)
        print("\n📊 Crawl results (minimal):")
        print(f"📝 Title: {minimal_result['title']}")
        print(f"🌍 Country: {minimal_result['country']}")
        print(f"🏙️  City: {minimal_result['city']}")
        print(f"🎥 embedUrl: {minimal_result['embedUrl']}")
        print(f"🎥 contentUrl: {minimal_result['contentUrl']}")
        print(f"🖼️  thumbnailUrl: {minimal_result['thumbnailUrl']}")
        
        print(f"\n💾 Results saved to: {filename}")
        print("🎉 Crawl and save completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if driver:
            driver.quit()
            print("🚗 WebDriver has been closed")

def extract_map_information(soup, driver):
    """Extract map information"""
    map_info = {
        'openstreetmap': {},
        'google_maps': {},
        'other_maps': []
    }
    
    try:
        # Search OpenStreetMap
        osm_elements = soup.find_all(['div', 'iframe'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['map', 'osm', 'openstreetmap', 'leaflet']))
        
        for element in osm_elements:
            # Check OpenStreetMap iframe
            if element.name == 'iframe':
                src = element.get('src', '')
                if any(domain in src.lower() for domain in ['openstreetmap.org', 'osm.org', 'leaflet']):
                    map_info['openstreetmap']['iframe_src'] = src
                    map_info['openstreetmap']['type'] = 'iframe'
            
            # Check div containing map
            elif element.name == 'div':
                # Search data attributes containing coordinates
                for attr, value in element.attrs.items():
                    if any(keyword in attr.lower() for keyword in ['lat', 'lon', 'zoom', 'center']):
                        map_info['openstreetmap'][attr] = value
                
                # Search in data attributes
                data_lat = element.get('data-lat') or element.get('data-latitude')
                data_lon = element.get('data-lon') or element.get('data-longitude')
                data_zoom = element.get('data-zoom')
                
                if data_lat and data_lon:
                    map_info['openstreetmap']['data_lat'] = data_lat
                    map_info['openstreetmap']['data_lon'] = data_lon
                    if data_zoom:
                        map_info['openstreetmap']['data_zoom'] = data_zoom
        
        # Search Google Maps
        google_elements = soup.find_all(['div', 'iframe'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['google-map', 'googlemap', 'gmap']))
        
        for element in google_elements:
            if element.name == 'iframe':
                src = element.get('src', '')
                if 'google.com/maps' in src or 'maps.google.com' in src:
                    map_info['google_maps']['iframe_src'] = src
                    map_info['google_maps']['type'] = 'iframe'
            
            # Search Google Maps data attributes
            for attr, value in element.attrs.items():
                if any(keyword in attr.lower() for keyword in ['lat', 'lng', 'zoom', 'center']):
                    map_info['google_maps'][attr] = value
        
        # Search in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Search OpenStreetMap coordinates
                import re
                osm_patterns = [
                    r'lat["\']?\s*:\s*([0-9.-]+)',
                    r'lon["\']?\s*:\s*([0-9.-]+)',
                    r'latitude["\']?\s*:\s*([0-9.-]+)',
                    r'longitude["\']?\s*:\s*([0-9.-]+)',
                    r'center["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'zoom["\']?\s*:\s*([0-9]+)',
                    # Additional patterns for Leaflet/OpenStreetMap
                    r'L\.map\(["\']([^"\']+)["\']\s*,\s*{\s*center:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'setView\(\[([0-9.-]+),\s*([0-9.-]+)\]\s*,\s*([0-9]+)',
                    r'center:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'lat:\s*([0-9.-]+)',
                    r'lng:\s*([0-9.-]+)',
                    r'zoom:\s*([0-9]+)',
                    # Additional patterns for React/Next.js
                    r'position["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'coordinates["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'location["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    # Patterns for JSON data
                    r'"lat":\s*([0-9.-]+)',
                    r'"lon":\s*([0-9.-]+)',
                    r'"latitude":\s*([0-9.-]+)',
                    r'"longitude":\s*([0-9.-]+)',
                    r'"center":\s*\[([0-9.-]+),\s*([0-9.-]+)\]'
                ]
                
                for pattern in osm_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if 'center' in pattern:
                            if len(match) == 2:
                                map_info['openstreetmap']['center_lat'] = match[0]
                                map_info['openstreetmap']['center_lon'] = match[1]
                        elif 'lat' in pattern or 'latitude' in pattern:
                            map_info['openstreetmap']['lat'] = match
                        elif 'lon' in pattern or 'longitude' in pattern:
                            map_info['openstreetmap']['lon'] = match
                        elif 'zoom' in pattern:
                            map_info['openstreetmap']['zoom'] = match
                
                # Search Google Maps coordinates
                google_patterns = [
                    r'google\.maps\.LatLng\(([0-9.-]+),\s*([0-9.-]+)\)',
                    r'center["\']?\s*:\s*new\s+google\.maps\.LatLng\(([0-9.-]+),\s*([0-9.-]+)\)',
                    r'zoom["\']?\s*:\s*([0-9]+)'
                ]
                
                for pattern in google_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if 'LatLng' in pattern:
                            if len(match) == 2:
                                map_info['google_maps']['lat'] = match[0]
                                map_info['google_maps']['lng'] = match[1]
                        elif 'zoom' in pattern:
                            map_info['google_maps']['zoom'] = match
        
        # Search for other map types
        other_map_elements = soup.find_all(['div', 'iframe'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['map', 'ban do', 'carto', 'mapbox']))
        
        for element in other_map_elements:
            if element.name == 'iframe':
                src = element.get('src', '')
                if src and 'map' in src.lower():
                    map_info['other_maps'].append({
                        'type': 'iframe',
                        'src': src,
                        'class': element.get('class', [])
                    })
            else:
                map_info['other_maps'].append({
                    'type': 'div',
                    'class': element.get('class', []),
                    'id': element.get('id', ''),
                    'attrs': dict(element.attrs)
                })
    
    except Exception as e:
        print(f"Error extracting map information: {e}")
    
    return map_info

def extract_coordinates(soup, driver):
    """Extract coordinates from maps"""
    coordinates = {}
    
    try:
        # Search coordinates from OpenStreetMap
        osm_info = {}
        
        # Search in data attributes
        map_divs = soup.find_all('div', class_=lambda x: x and 'map' in x.lower())
        for div in map_divs:
            data_lat = div.get('data-lat') or div.get('data-latitude')
            data_lon = div.get('data-lon') or div.get('data-longitude')
            data_zoom = div.get('data-zoom')
            
            if data_lat and data_lon:
                osm_info['data_lat'] = data_lat
                osm_info['data_lon'] = data_lon
                if data_zoom:
                    osm_info['data_zoom'] = data_zoom
        
        # Search in divs with class containing 'Map'
        map_class_divs = soup.find_all('div', class_=lambda x: x and any(keyword in x for keyword in ['Map', 'map']))
        for div in map_class_divs:
            # Check all attributes
            for attr, value in div.attrs.items():
                if any(keyword in attr.lower() for keyword in ['lat', 'lon', 'zoom', 'center', 'coord']):
                    osm_info[f'map_{attr}'] = value
                
                # Check data attributes
                if attr.startswith('data-'):
                    if any(keyword in attr.lower() for keyword in ['lat', 'lon', 'zoom', 'center', 'coord']):
                        osm_info[f'data_{attr}'] = value
        
        # Search in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_content = script.string
                
                import re
                # Search OpenStreetMap coordinates
                osm_patterns = [
                    r'lat["\']?\s*:\s*([0-9.-]+)',
                    r'lon["\']?\s*:\s*([0-9.-]+)',
                    r'latitude["\']?\s*:\s*([0-9.-]+)',
                    r'longitude["\']?\s*:\s*([0-9.-]+)',
                    r'center["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                    r'zoom["\']?\s*:\s*([0-9]+)'
                ]
                
                for i, pattern in enumerate(osm_patterns):
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if 'center' in pattern and 'L\.map' not in pattern:
                            if len(match) == 2:
                                osm_info['center_lat'] = match[0]
                                osm_info['center_lon'] = match[1]
                        elif 'L\.map' in pattern:
                            if len(match) == 3:
                                osm_info['map_id'] = match[0]
                                osm_info['center_lat'] = match[0]
                                osm_info['center_lon'] = match[1]
                        elif 'setView' in pattern:
                            if len(match) == 3:
                                osm_info['center_lat'] = match[0]
                                osm_info['center_lon'] = match[1]
                                osm_info['zoom'] = match[2]
                        elif 'position' in pattern or 'coordinates' in pattern or 'location' in pattern:
                            if len(match) == 2:
                                osm_info['center_lat'] = match[0]
                                osm_info['center_lon'] = match[1]
                        elif 'lat' in pattern or 'latitude' in pattern:
                            osm_info['lat'] = match
                        elif 'lon' in pattern or 'longitude' in pattern:
                            osm_info['lon'] = match
                        elif 'lng' in pattern:
                            osm_info['lon'] = match
                        elif 'zoom' in pattern:
                            osm_info['zoom'] = match
                
                # Search Google Maps coordinates
                google_patterns = [
                    r'google\.maps\.LatLng\(([0-9.-]+),\s*([0-9.-]+)\)',
                    r'center["\']?\s*:\s*new\s+google\.maps\.LatLng\(([0-9.-]+),\s*([0-9.-]+)\)',
                    r'zoom["\']?\s*:\s*([0-9]+)'
                ]
                
                for pattern in google_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if 'LatLng' in pattern:
                            if len(match) == 2:
                                osm_info['google_lat'] = match[0]
                                osm_info['google_lon'] = match[1]
                        elif 'zoom' in pattern:
                            osm_info['google_zoom'] = match
        
        # Prioritize coordinates from OpenStreetMap
        if 'lat' in osm_info and 'lon' in osm_info:
            coordinates['latitude'] = osm_info['lat']
            coordinates['longitude'] = osm_info['lon']
            coordinates['source'] = 'openstreetmap_data'
            if 'zoom' in osm_info:
                coordinates['zoom'] = osm_info['zoom']
        elif 'center_lat' in osm_info and 'center_lon' in osm_info:
            coordinates['latitude'] = osm_info['center_lat']
            coordinates['longitude'] = osm_info['center_lon']
            coordinates['source'] = 'openstreetmap_center'
            if 'zoom' in osm_info:
                coordinates['zoom'] = osm_info['zoom']
        elif 'google_lat' in osm_info and 'google_lon' in osm_info:
            coordinates['latitude'] = osm_info['google_lat']
            coordinates['longitude'] = osm_info['google_lon']
            coordinates['source'] = 'google_maps'
            if 'google_zoom' in osm_info:
                coordinates['zoom'] = osm_info['google_zoom']
        
        # Search coordinates from URL parameters
        if not coordinates.get('latitude'):
            # Kiểm tra URL hiện tại của driver
            current_url = driver.current_url
            if 'lat=' in current_url and 'lon=' in current_url:
                import re
                lat_match = re.search(r'lat=([0-9.-]+)', current_url)
                lon_match = re.search(r'lon=([0-9.-]+)', current_url)
                zoom_match = re.search(r'zoom=([0-9]+)', current_url)
                
                if lat_match and lon_match:
                    coordinates['latitude'] = lat_match.group(1)
                    coordinates['longitude'] = lon_match.group(1)
                    coordinates['source'] = 'url_parameters'
                    if zoom_match:
                        coordinates['zoom'] = zoom_match.group(1)
    
    except Exception as e:
        print(f"Error extracting coordinates: {e}")
    
    return coordinates

def extract_openstreetmap_coordinates(soup, driver):
    """Extract coordinates from OpenStreetMap"""
    coordinates = {}
    
    try:
        print("🔍 Searching OpenStreetMap elements...")
        
        # Find div with id="mapContainer"
        map_container = soup.find('div', id='mapContainer')
        if map_container:
            print("✅ Found mapContainer")
        
        # Find Leaflet map wrapper
        leaflet_container = soup.find('div', class_=lambda x: x and 'leaflet-container' in x)
        if leaflet_container:
            print("✅ Found Leaflet container")
            
            # Find tile images to compute coordinates
            tile_images = soup.find_all('img', class_='leaflet-tile')
            if tile_images:
                print(f"✅ Found {len(tile_images)} tile images")
                
                # Get info from the first tile
                first_tile = tile_images[0]
                tile_src = first_tile.get('src', '')
                
                # Extract information from tile URL
                import re
                tile_pattern = r'https://[a-z]\.tile\.openstreetmap\.org/(\d+)/(\d+)/(\d+)\.png'
                tile_match = re.search(tile_pattern, tile_src)
                
                if tile_match:
                    zoom_level = int(tile_match.group(1))
                    tile_x = int(tile_match.group(2))
                    tile_y = int(tile_match.group(3))
                    
                    print(f"📍 Tile info: zoom={zoom_level}, x={tile_x}, y={tile_y}")
                    
                    # Compute coordinates from tile coordinates
                    lat, lon = tile_to_lat_lon(tile_x, tile_y, zoom_level)
                    
                    # Validate whether coordinates are reasonable (example range for Vietnam)
                    if 8.0 <= lat <= 23.0 and 102.0 <= lon <= 110.0:
                        coordinates['latitude'] = str(lat)
                        coordinates['longitude'] = str(lon)
                        coordinates['zoom'] = str(zoom_level)
                        coordinates['source'] = 'leaflet_tile_calculation'
                        coordinates['tile_x'] = tile_x
                        coordinates['tile_y'] = tile_y
                        
                        print(f"✅ Computed coordinates from tile: {lat}, {lon}")
                    else:
                        print(f"⚠️  Tile coordinates not reasonable for Vietnam: {lat}, {lon}")
                        # Skip these coordinates
            
            # Find marker to compute precise coordinates
            marker = soup.find('img', class_='leaflet-marker-icon')
            if marker:
                print("✅ Found map marker")
                
                # Read transform style of marker
                style = marker.get('style', '')
                transform_match = re.search(r'translate3d\(([^,]+),\s*([^,]+)', style)
                
                if transform_match:
                    marker_x = float(transform_match.group(1).replace('px', ''))
                    marker_y = float(transform_match.group(2).replace('px', ''))
                    print(f"📍 Marker position: x={marker_x}, y={marker_y}")

                    # Use a tile as reference to translate marker -> coordinates
                    ref_tile = None
                    for ti in tile_images:
                        if ti.get('src', '').startswith('https://'):
                            ref_tile = ti
                            break
                    if ref_tile:
                        ref_src = ref_tile.get('src', '')
                        m = re.search(r'https://[a-z]\.tile\.openstreetmap\.org/(\d+)/(\d+)/(\d+)\.png', ref_src)
                        mpos = re.search(r'translate3d\(([-0-9.]+)px,\s*([-0-9.]+)px', ref_tile.get('style', '') or '')
                        if m and mpos:
                            z = int(m.group(1))
                            tx = int(m.group(2))
                            ty = int(m.group(3))
                            tile_px = float(mpos.group(1))
                            tile_py = float(mpos.group(2))

                            # Difference between marker and ref tile top-left corner
                            dx = marker_x - tile_px
                            dy = marker_y - tile_py
                            # Convert to real tile coordinates (fractional)
                            adj_tx = tx + (dx / 256.0)
                            adj_ty = ty + (dy / 256.0)
                            lat2, lon2 = tile_to_lat_lon(adj_tx, adj_ty, z)
                            coordinates['latitude'] = str(lat2)
                            coordinates['longitude'] = str(lon2)
                            coordinates['zoom'] = str(z)
                            coordinates['source'] = 'leaflet_marker_ref_tile'
                            coordinates['marker_x'] = marker_x
                            coordinates['marker_y'] = marker_y
                            print(f"✅ Computed coordinates from marker + tile: {lat2}, {lon2}")
            
            # Search in all scripts
            scripts = soup.find_all('script')
            osm_data = {}
            
            for script in scripts:
                if script.string:
                    script_content = script.string
                    
                    # Search special patterns for OpenStreetMap/Leaflet
                    import re
                    osm_patterns = [
                        # Leaflet map initialization
                        r'L\.map\(["\']([^"\']+)["\']\s*,\s*{\s*center:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                        r'setView\(\[([0-9.-]+),\s*([0-9.-]+)\]\s*,\s*([0-9]+)',
                        r'center:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                        
                        # OpenStreetMap specific patterns
                        r'openstreetmap\.org.*?lat=([0-9.-]+).*?lon=([0-9.-]+)',
                        r'osm\.org.*?lat=([0-9.-]+).*?lon=([0-9.-]+)',
                        
                        # React/Next.js map data
                        r'"latitude":\s*([0-9.-]+)',
                        r'"longitude":\s*([0-9.-]+)',
                        r'"lat":\s*([0-9.-]+)',
                        r'"lon":\s*([0-9.-]+)',
                        r'"center":\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                        
                        # JavaScript variables
                        r'lat["\']?\s*=\s*([0-9.-]+)',
                        r'lon["\']?\s*=\s*([0-9.-]+)',
                        r'latitude["\']?\s*=\s*([0-9.-]+)',
                        r'longitude["\']?\s*=\s*([0-9.-]+)',
                        
                        # Map configuration objects
                        r'config["\']?\s*:\s*{[^}]*"lat["\']?\s*:\s*([0-9.-]+)',
                        r'config["\']?\s*:\s*{[^}]*"lon["\']?\s*:\s*([0-9.-]+)',
                        r'options["\']?\s*:\s*{[^}]*"center["\']?\s*:\s*\[([0-9.-]+),\s*([0-9.-]+)\]',
                        
                        # Camera location data
                        r'camera["\']?\s*:\s*{[^}]*"lat["\']?\s*:\s*([0-9.-]+)',
                        r'camera["\']?\s*:\s*{[^}]*"lon["\']?\s*:\s*([0-9.-]+)',
                        r'location["\']?\s*:\s*{[^}]*"lat["\']?\s*:\s*([0-9.-]+)',
                        r'location["\']?\s*:\s*{[^}]*"lon["\']?\s*:\s*([0-9.-]+)'
                    ]
                    
                    for pattern in osm_patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            if 'center' in pattern or 'setView' in pattern:
                                if len(match) == 2:
                                    osm_data['center_lat'] = match[0]
                                    osm_data['center_lon'] = match[1]
                                elif len(match) == 3:
                                    osm_data['center_lat'] = match[0]
                                    osm_data['center_lon'] = match[1]
                                    osm_data['zoom'] = match[2]
                            elif 'lat' in pattern or 'latitude' in pattern:
                                osm_data['lat'] = match
                            elif 'lon' in pattern or 'longitude' in pattern:
                                osm_data['lon'] = match
                            elif 'openstreetmap.org' in pattern or 'osm.org' in pattern:
                                if len(match) == 2:
                                    osm_data['osm_lat'] = match[0]
                                    osm_data['osm_lon'] = match[1]
            
            # Search in JSON-LD data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            # Search coordinates in JSON-LD
                            if 'geo' in data:
                                geo = data['geo']
                                if isinstance(geo, dict):
                                    if 'latitude' in geo:
                                        osm_data['json_ld_lat'] = geo['latitude']
                                    if 'longitude' in geo:
                                        osm_data['json_ld_lon'] = geo['longitude']
                            elif 'location' in data:
                                location = data['location']
                                if isinstance(location, dict):
                                    if 'latitude' in location:
                                        osm_data['json_ld_lat'] = location['latitude']
                                    if 'longitude' in location:
                                        osm_data['json_ld_lon'] = location['longitude']
                    except:
                        pass
            
            # Search in meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name', '').lower()
                content = meta.get('content', '')
                
                if 'geo.position' in name or 'geo.position-latitude' in name:
                    osm_data['meta_lat'] = content
                elif 'geo.position-longitude' in name:
                    osm_data['meta_lon'] = content
                elif 'geo.coordinates' in name:
                    # Format: "latitude;longitude"
                    if ';' in content:
                        parts = content.split(';')
                        if len(parts) == 2:
                            osm_data['meta_lat'] = parts[0]
                            osm_data['meta_lon'] = parts[1]
            
            # Prioritize coordinates from various sources
            if 'center_lat' in osm_data and 'center_lon' in osm_data:
                coordinates['latitude'] = osm_data['center_lat']
                coordinates['longitude'] = osm_data['center_lon']
                coordinates['source'] = 'openstreetmap_center'
                if 'zoom' in osm_data:
                    coordinates['zoom'] = osm_data['zoom']
            elif 'lat' in osm_data and 'lon' in osm_data:
                coordinates['latitude'] = osm_data['lat']
                coordinates['longitude'] = osm_data['lon']
                coordinates['source'] = 'openstreetmap_data'
            elif 'osm_lat' in osm_data and 'osm_lon' in osm_data:
                coordinates['latitude'] = osm_data['osm_lat']
                coordinates['longitude'] = osm_data['osm_lon']
                coordinates['source'] = 'openstreetmap_url'
            elif 'json_ld_lat' in osm_data and 'json_ld_lon' in osm_data:
                coordinates['latitude'] = osm_data['json_ld_lat']
                coordinates['longitude'] = osm_data['json_ld_lon']
                coordinates['source'] = 'json_ld'
            elif 'meta_lat' in osm_data and 'meta_lon' in osm_data:
                coordinates['latitude'] = osm_data['meta_lat']
                coordinates['longitude'] = osm_data['meta_lon']
                coordinates['source'] = 'meta_tags'
            
            if coordinates:
                print(f"✅ Found coordinates: {coordinates['latitude']}, {coordinates['longitude']}")
            else:
                print("❌ Coordinates not found in OpenStreetMap")
        
        # Search in OpenStreetMap iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if 'openstreetmap.org' in src or 'osm.org' in src:
                print(f"✅ Found OpenStreetMap iframe: {src}")
                
                # Trích xuất tọa độ từ URL
                import re
                lat_match = re.search(r'lat=([0-9.-]+)', src)
                lon_match = re.search(r'lon=([0-9.-]+)', src)
                zoom_match = re.search(r'zoom=([0-9]+)', src)
                
                if lat_match and lon_match:
                    coordinates['latitude'] = lat_match.group(1)
                    coordinates['longitude'] = lon_match.group(1)
                    coordinates['source'] = 'openstreetmap_iframe'
                    if zoom_match:
                        coordinates['zoom'] = zoom_match.group(1)
                    break
    
    except Exception as e:
        print(f"Error extracting OpenStreetMap coordinates: {e}")
    
    return coordinates

def tile_to_lat_lon(tile_x, tile_y, zoom):
    """Convert tile coordinates to latitude/longitude"""
    import math
    
    n = 2.0 ** zoom
    lon_deg = tile_x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
    lat_deg = math.degrees(lat_rad)
    
    return lat_deg, lon_deg

def pixel_to_lat_lon(pixel_x, pixel_y, tile_x, tile_y, zoom):
    """Convert pixel position to latitude/longitude"""
    import math
    
    # Tile size (256x256 pixels)
    tile_size = 256
    
    # Compute pixel offset within tile
    pixel_offset_x = pixel_x % tile_size
    pixel_offset_y = pixel_y % tile_size
    
    # Compute tile coordinates with offset
    adjusted_tile_x = tile_x + (pixel_offset_x / tile_size)
    adjusted_tile_y = tile_y + (pixel_offset_y / tile_size)
    
    # Convert to lat/lon
    return tile_to_lat_lon(adjusted_tile_x, adjusted_tile_y, zoom)

def lat_lon_to_tile(lat, lon, zoom):
    """Convert latitude/longitude to tile coordinates"""
    import math
    
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    tile_x = int((lon + 180.0) / 360.0 * n)
    tile_y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    
    return tile_x, tile_y

def global_pixel_to_lat_lon(px, py, zoom, world_size=None):
    """Convert global pixel (from top-left of world) to lat/lon (Web Mercator).
    px/py: global pixel coordinates in the world
    zoom: zoom level
    world_size: world size in pixels, default 256 * 2^zoom
    """
    import math
    if world_size is None:
        world_size = 256 * (2 ** zoom)
    x = px / world_size - 0.5
    y = 0.5 - py / world_size
    lon = 360.0 * x
    lat = 90.0 - 360.0 * math.atan(math.exp(-y * 2.0 * math.pi)) / math.pi
    return lat, lon

def strip_accents(text):
    try:
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        return text
    except Exception:
        return text

def translate_vi_title_to_en(text):
    if not text:
        return text or ''
    base = strip_accents(text)
    # Basic replacements for common Vietnamese keywords
    replacements = {
        'truc tuyen': 'live',
        'truc tiep': 'live',
        'webcam': 'Webcam',
        'phat truc tiep': 'live',
        'qua webcam': 'via webcam',
        'viet nam': 'Vietnam',
        'da nang': 'Da Nang',
        'quang trung': 'Quang Trung',
    }
    lowered = base.lower()
    for vi, en in replacements.items():
        lowered = lowered.replace(vi, en)
    # Capitalize first letter
    return lowered[:1].upper() + lowered[1:]

def infer_city_english(result, url):
    # Prefer breadcrumbs
    try:
        if result.get('location', {}).get('breadcrumbs'):
            for trail in result['location']['breadcrumbs']:
                for crumb in trail:
                    text = str(crumb.get('text', '')).strip()
                    t = strip_accents(text).lower()
                    if 'da nang' in t or 'da nang' in text.lower():
                        return 'Da Nang'
                    # Mapping can be extended for other cities if needed
    except Exception:
        pass
    # Based on title/h1
    for key in ['page_info']:
        try:
            title = (result.get(key, {}) or {}).get('title', '')
            if title:
                t = strip_accents(title).lower()
                if 'da nang' in t:
                    return 'Da Nang'
        except Exception:
            pass
    # From URL
    try:
        if '/da-nang/' in url:
            return 'Da Nang'
    except Exception:
        pass
    return ''

if __name__ == "__main__":
    crawl_and_save_results()
