#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webcam Data Crawler Tool
Crawl data từ các webcam streaming URLs
"""

import requests
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import os

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import helper extraction functions from save_results.py to reuse tested logic
from save_results import (
    extract_map_information,
    extract_openstreetmap_coordinates,
    extract_coordinates,
    infer_city_english,
)

class WebcamCrawler:
    """Class chính để crawl data từ webcam URLs"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.session = requests.Session()
        self.ua = UserAgent()
        self.setup_session()
        self.driver = None
        
    def setup_session(self):
        """Thiết lập session requests với headers phù hợp"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def setup_driver(self):
        """Thiết lập Selenium WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={self.ua.random}')
            
            # Thêm options để xử lý macOS ARM64
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            try:
                # Thử sử dụng ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Selenium WebDriver đã được khởi tạo thành công với ChromeDriverManager")
                return True
            except Exception as e:
                logger.warning(f"ChromeDriverManager failed: {e}")
                
                # Fallback: thử tìm ChromeDriver trong PATH
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    logger.info("Selenium WebDriver đã được khởi tạo thành công với ChromeDriver trong PATH")
                    return True
                except Exception as e2:
                    logger.warning(f"ChromeDriver trong PATH failed: {e2}")
                    
                    # Fallback cuối cùng: thử với Safari (trên macOS)
                    try:
                        from selenium.webdriver.safari.webdriver import SafariDriver
                        self.driver = SafariDriver()
                        logger.info("Selenium WebDriver đã được khởi tạo thành công với Safari")
                        return True
                    except Exception as e3:
                        logger.error(f"Safari fallback failed: {e3}")
                        return False
                        
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo WebDriver: {e}")
            return False
            
    def close_driver(self):
        """Đóng WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver đã được đóng")
            
    def crawl_with_requests(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl data sử dụng requests (nhanh hơn)"""
        try:
            logger.info(f"Đang crawl URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trích xuất thông tin cơ bản
            data = {
                'url': url,
                'title': self.extract_title(soup),
                'description': self.extract_description(soup),
                'location': self.extract_location(soup, url),
                'camera_info': self.extract_camera_info(soup),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # Kiểm tra xem có cần dùng Selenium không
            if self.should_use_selenium(soup):
                logger.info("Phát hiện JavaScript content, chuyển sang Selenium...")
                selenium_result = self.crawl_with_selenium(url)
                if selenium_result and selenium_result.get('status') == 'success':
                    # Cập nhật data với kết quả từ Selenium
                    data.update({
                        'title': selenium_result.get('title', data['title']),
                        'description': selenium_result.get('description', data['description']),
                        'location': selenium_result.get('location', data['location']),
                        'camera_info': selenium_result.get('camera_info', data['camera_info']),
                        'method': 'selenium_fallback'
                    })
                else:
                    data['method'] = 'requests_only'
            else:
                data['method'] = 'requests_only'
            
            logger.info(f"Crawl thành công: {data['title']}")
            return data
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl với requests: {e}")
            return {
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
            
    def crawl_with_selenium(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl data sử dụng Selenium (cho JavaScript-heavy pages)"""
        if not self.driver:
            if not self.setup_driver():
                return None
        try:
            logger.info(f"Đang crawl URL với Selenium: {url}")
            self.driver.get(url)
            # Chờ page load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Lấy page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            # Trích xuất thông tin
            data = {
                'url': url,
                'title': self.extract_title(soup),
                'location': self.extract_location(soup, url),
                'description': self.extract_description(soup),
                'camera_info': self.extract_camera_info(soup),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            logger.info(f"Crawl với Selenium thành công: {data['title']}")
            return data
        except Exception as e:
            logger.error(f"Lỗi khi crawl với Selenium: {e}")
            return {
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
            
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Trích xuất tiêu đề trang"""
        # Tìm kiếm title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            if title_text and title_text != "Không có tiêu đề":
                return title_text
        
        # Tìm kiếm trong h1 tags
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            h1_text = h1.get_text(strip=True)
            if h1_text and len(h1_text) > 5:
                return h1_text
        
        # Tìm kiếm trong các class có chứa title
        title_selectors = [
            '.page-title',
            '.main-title',
            '.title',
            '[class*="title"]',
            '.heading',
            '.header-title',
            '.page-heading'
        ]
        
        for selector in title_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5:
                    return text
        
        # Tìm kiếm trong JSON-LD data
        json_ld_title = self.extract_title_from_json_ld(soup)
        if json_ld_title:
            return json_ld_title
        
        return "Không có tiêu đề"
    
    def extract_title_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Trích xuất tiêu đề từ JSON-LD data"""
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                if script.string:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'name' in data:
                        return data['name']
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'name' in item:
                                return item['name']
        except:
            pass
        return ""
        
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Trích xuất mô tả trang"""
        # Tìm kiếm meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = meta_desc.get('content', '').strip()
            if content and len(content) > 10:
                return content
        
        # Tìm kiếm meta description khác
        meta_desc_alt = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc_alt and meta_desc_alt.get('content'):
            content = meta_desc_alt.get('content', '').strip()
            if content and len(content) > 10:
                return content
        
        # Tìm kiếm trong JSON-LD data
        json_ld_desc = self.extract_description_from_json_ld(soup)
        if json_ld_desc:
            return json_ld_desc
        
        # Tìm kiếm trong các paragraph đầu tiên
        paragraphs = soup.find_all('p')
        for p in paragraphs[:3]:  # Chỉ xem 3 paragraph đầu tiên
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Loại bỏ text quá ngắn
                return text
        
        # Tìm kiếm trong các div có class description
        desc_selectors = [
            '.description',
            '.desc',
            '.summary',
            '.intro',
            '.content-summary',
            '.TextContent_desc__zXjP_'
        ]
        
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 20:
                    return text
        
        return "Không có mô tả"
    
    def extract_description_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Trích xuất mô tả từ JSON-LD data"""
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                if script.string:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'description' in data:
                        return data['description']
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'description' in item:
                                return item['description']
        except:
            pass
        return ""
        
    def extract_location(self, soup: BeautifulSoup, url: str) -> str:
        """Trích xuất thông tin vị trí từ URL và nội dung trang"""
        # Trích xuất vị trí từ URL trước
        url_location = self.extract_location_from_url(url)
        
        # Tìm kiếm vị trí trong nội dung trang
        page_location = self.extract_location_from_page(soup)
        
        # Ưu tiên vị trí từ trang, nếu không có thì dùng từ URL
        if page_location and page_location != "Không xác định được vị trí":
            return page_location
        elif url_location:
            return url_location
        else:
            return "Không xác định được vị trí"
    
    def extract_location_from_url(self, url: str) -> str:
        """Trích xuất vị trí từ URL"""
        try:
            # Parse URL để lấy path
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Tìm kiếm các từ khóa vị trí trong path
            location_keywords = ['vietnam', 'quang-trung', 'quang_trung', 'cam']
            
            for part in path_parts:
                if any(keyword in part.lower() for keyword in location_keywords):
                    # Chuyển đổi format
                    if 'quang-trung' in part.lower():
                        return "Quang Trung Street, Vietnam"
                    elif 'vietnam' in part.lower():
                        return "Vietnam"
                    elif 'cam' in part.lower():
                        return "Camera Location"
            
            return ""
        except:
            return ""
    
    def extract_location_from_page(self, soup: BeautifulSoup) -> str:
        """Trích xuất vị trí từ nội dung trang"""
        # Tìm kiếm các element chứa thông tin vị trí
        location_selectors = [
            '.location',
            '.address',
            '[class*="location"]',
            '[class*="address"]',
            '[class*="city"]',
            '[class*="country"]',
            'h1', 'h2', 'h3',
            '.breadcrumb',
            '.nav-breadcrumb'
        ]
        
        for selector in location_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 3:  # Loại bỏ text quá ngắn
                    # Kiểm tra xem có chứa từ khóa vị trí không
                    if any(keyword in text.lower() for keyword in ['vietnam', 'quang trung', 'cam', 'street', 'đường']):
                        return text
        country = None
        city = None
        breadcrumbs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
        # Duyệt toàn bộ các link breadcrumb
        for breadcrumb in breadcrumbs:
            links = breadcrumb.find_all('a')
            for link in links:
                href = link.get('href', '')
                parts = href.strip('/').split('/')
                print(f"DEBUG breadcrumb href: {href}, parts: {parts}")
                # country: /countries/<country>/
                if len(parts) == 2 and parts[0] == 'countries':
                    country = parts[1].replace('-', ' ').title()
                    print(f"DEBUG set country: {country}")
                # city: /countries/<country>/<city>/
                elif len(parts) == 3 and parts[0] == 'countries':
                    city = parts[2].replace('-', ' ').title()
                    print(f"DEBUG set city: {city}")
        # Nếu không có city thì city sẽ trùng với country
        if not city and country:
            city = country
        if country and city:
            return f"{country} > {city}"
        elif country:
            return country
        
        # Tìm kiếm trong JSON-LD data
        json_ld_location = self.extract_location_from_json_ld(soup)
        if json_ld_location:
            return json_ld_location
        
        return "Không xác định được vị trí"
    
    def extract_location_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Trích xuất vị trí từ JSON-LD data"""
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                if script.string:
                    import json
                    data = json.loads(script.string)
                    # Tìm kiếm trong data
                    if isinstance(data, dict):
                        # Kiểm tra các thuộc tính có thể chứa vị trí
                        for key in ['location', 'address', 'place', 'area']:
                            if key in data and data[key]:
                                return str(data[key])
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                for key in ['location', 'address', 'place', 'area']:
                                    if key in item and item[key]:
                                        return str(item[key])
        except:
            pass
        return ""
        
    def extract_camera_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin camera và stream links"""
        camera_info = {}
        
        # Tìm kiếm thông tin camera
        camera_info.update(self.extract_camera_text_info(soup))
        
        # Tìm kiếm YouTube streams với embedUrl, contentUrl
        youtube_info = self.extract_youtube_info(soup)
        if youtube_info:
            camera_info.update(youtube_info)
        
        # Tìm kiếm thumbnail URLs
        thumbnails = self.extract_thumbnail_urls(soup)
        if thumbnails:
            camera_info['thumbnails'] = thumbnails
        
        # Tìm kiếm các link stream khác
        other_streams = self.extract_other_streams(soup)
        if other_streams:
            camera_info['other_streams'] = other_streams
            
        # Tìm kiếm embed codes
        embed_codes = self.extract_embed_codes(soup)
        if embed_codes:
            camera_info['embed_codes'] = embed_codes
            
        return camera_info
    
    def extract_camera_text_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin text về camera"""
        info = {}
        
        camera_selectors = [
            '.camera-info',
            '.stream-info',
            '[class*="camera"]',
            '[class*="stream"]',
            '.webcam-info',
            '.live-info',
            '.status-info'
        ]
        
        for selector in camera_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5:  # Loại bỏ text quá ngắn
                    info[f'info_{len(info)}'] = text
                    
        return info
    
    def extract_youtube_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin YouTube với embedUrl, contentUrl"""
        youtube_info = {}
        
        # Tìm kiếm trong JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                youtube_info.update(self.extract_from_json_ld(data))
            except:
                continue
        
        # Tìm kiếm trong meta tags
        meta_info = self.extract_youtube_meta_tags(soup)
        if meta_info:
            youtube_info.update(meta_info)
        
        # Tìm kiếm YouTube iframe embeds
        iframe_info = self.extract_youtube_iframes(soup)
        if iframe_info:
            youtube_info.update(iframe_info)
        
        # Tìm kiếm trong scripts
        script_info = self.extract_youtube_from_scripts(soup)
        if script_info:
            youtube_info.update(script_info)
        
        return youtube_info
    
    def extract_from_json_ld(self, data: Dict) -> Dict[str, Any]:
        """Trích xuất thông tin từ JSON-LD structured data"""
        info = {}
        
        # Xử lý data có thể là list hoặc dict
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    info.update(self.extract_from_json_ld(item))
        elif isinstance(data, dict):
            # Tìm kiếm embedUrl, contentUrl, thumbnailUrl
            if 'embedUrl' in data:
                info['embedUrl'] = data['embedUrl']
            if 'contentUrl' in data:
                info['contentUrl'] = data['contentUrl']
            if 'thumbnailUrl' in data:
                info['thumbnailUrl'] = data['thumbnailUrl']
            
            # Tìm kiếm trong các thuộc tính nested
            for key, value in data.items():
                if isinstance(value, dict):
                    nested_info = self.extract_from_json_ld(value)
                    if nested_info:
                        info.update(nested_info)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            nested_info = self.extract_from_json_ld(item)
                            if nested_info:
                                info.update(nested_info)
        
        return info
    
    def extract_youtube_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin YouTube từ meta tags"""
        meta_info = {}
        
        # Tìm kiếm các meta tags liên quan đến YouTube
        meta_selectors = [
            'meta[property="og:video"]',
            'meta[property="og:video:url"]',
            'meta[property="og:video:secure_url"]',
            'meta[name="twitter:player"]',
            'meta[name="twitter:player:stream"]'
        ]
        
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                content = meta.get('content')
                if 'youtube.com' in content:
                    if 'embed' in content:
                        meta_info['embedUrl'] = content
                    else:
                        meta_info['contentUrl'] = content
        
        return meta_info
    
    def extract_youtube_iframes(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin từ YouTube iframes"""
        iframe_info = {}
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'youtu.be' in src:
                iframe_info['embedUrl'] = src
                
                # Chuyển đổi embed URL thành content URL
                if '/embed/' in src:
                    video_id = src.split('/embed/')[-1].split('?')[0]
                    iframe_info['contentUrl'] = f'https://www.youtube.com/watch?v={video_id}'
                elif 'youtu.be/' in src:
                    video_id = src.split('youtu.be/')[-1].split('?')[0]
                    iframe_info['contentUrl'] = f'https://www.youtube.com/watch?v={video_id}'
        
        return iframe_info
    
    def extract_youtube_from_scripts(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Trích xuất thông tin YouTube từ scripts"""
        script_info = {}
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Tìm kiếm các pattern YouTube
                import re
                patterns = [
                    r'embedUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'contentUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'thumbnailUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                    r'youtu\.be/([a-zA-Z0-9_-]+)',
                    r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
                ]
                
                for i, pattern in enumerate(patterns):
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if i == 0:  # embedUrl
                            script_info['embedUrl'] = match
                        elif i == 1:  # contentUrl
                            script_info['contentUrl'] = match
                        elif i == 2:  # thumbnailUrl
                            script_info['thumbnailUrl'] = match
                        elif i >= 3:  # YouTube video IDs
                            if 'embedUrl' not in script_info:
                                script_info['embedUrl'] = f'https://www.youtube.com/embed/{match}'
                            if 'contentUrl' not in script_info:
                                script_info['contentUrl'] = f'https://www.youtube.com/watch?v={match}'
        
        return script_info
    
    def should_use_selenium(self, soup: BeautifulSoup) -> bool:
        """Kiểm tra xem có cần dùng Selenium không"""
        # Kiểm tra các dấu hiệu của JavaScript-rendered content
        indicators = [
            # Kiểm tra có script tags không
            len(soup.find_all('script')) > 5,
            # Kiểm tra có Next.js indicators không
            soup.find('script', src=lambda x: x and 'next' in x) is not None,
            # Kiểm tra có React/Vue indicators không
            soup.find('div', {'id': 'root'}) is not None or soup.find('div', {'id': 'app'}) is not None,
            # Kiểm tra có template tags không
            soup.find('template') is not None,
            # Kiểm tra có noscript tags không
            soup.find('noscript') is not None,
            # Kiểm tra content quá ngắn (có thể là JavaScript-rendered)
            len(soup.get_text(strip=True)) < 1000,
            # Kiểm tra không có title
            not soup.find('title') or not soup.find('title').get_text(strip=True),
            # Kiểm tra không có h1
            not soup.find('h1'),
            # Kiểm tra không có meta description
            not soup.find('meta', attrs={'name': 'description'})
        ]
        
        # Nếu có nhiều dấu hiệu, sử dụng Selenium
        return sum(indicators) >= 3
    
    def extract_thumbnail_urls(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất thumbnail URLs"""
        thumbnails = []
        
        # Tìm kiếm trong JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                thumbnails.extend(self.extract_thumbnails_from_json_ld(data))
            except:
                continue
        
        # Tìm kiếm trong meta tags
        meta_thumbnails = self.extract_thumbnail_meta_tags(soup)
        if meta_thumbnails:
            thumbnails.extend(meta_thumbnails)
        
        # Tìm kiếm trong img tags
        img_thumbnails = self.extract_thumbnail_from_images(soup)
        if img_thumbnails:
            thumbnails.extend(img_thumbnails)
        
        # Tìm kiếm trong scripts
        script_thumbnails = self.extract_thumbnail_from_scripts(soup)
        if script_thumbnails:
            thumbnails.extend(script_thumbnails)
        
        return thumbnails
    
    def extract_thumbnails_from_json_ld(self, data: Dict) -> List[Dict[str, str]]:
        """Trích xuất thumbnails từ JSON-LD data"""
        thumbnails = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    thumbnails.extend(self.extract_thumbnails_from_json_ld(item))
        elif isinstance(data, dict):
            # Tìm kiếm thumbnailUrl
            if 'thumbnailUrl' in data:
                thumbnails.append({
                    'type': 'json_ld',
                    'url': data['thumbnailUrl'],
                    'source': 'thumbnailUrl'
                })
            
            # Tìm kiếm image
            if 'image' in data:
                image_data = data['image']
                if isinstance(image_data, str):
                    thumbnails.append({
                        'type': 'json_ld',
                        'url': image_data,
                        'source': 'image'
                    })
                elif isinstance(image_data, dict) and 'url' in image_data:
                    thumbnails.append({
                        'type': 'json_ld',
                        'url': image_data['url'],
                        'source': 'image.url'
                    })
                elif isinstance(image_data, list):
                    for img in image_data:
                        if isinstance(img, str):
                            thumbnails.append({
                                'type': 'json_ld',
                                'url': img,
                                'source': 'image[list]'
                            })
                        elif isinstance(img, dict) and 'url' in img:
                            thumbnails.append({
                                'type': 'json_ld',
                                'url': img['url'],
                                'source': 'image[list].url'
                            })
            
            # Tìm kiếm trong các thuộc tính nested
            for key, value in data.items():
                if isinstance(value, dict):
                    thumbnails.extend(self.extract_thumbnails_from_json_ld(value))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            thumbnails.extend(self.extract_thumbnails_from_json_ld(item))
        
        return thumbnails
    
    def extract_thumbnail_meta_tags(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất thumbnails từ meta tags"""
        thumbnails = []
        
        # Tìm kiếm các meta tags liên quan đến thumbnail
        meta_selectors = [
            'meta[property="og:image"]',
            'meta[property="og:image:url"]',
            'meta[property="og:image:secure_url"]',
            'meta[name="twitter:image"]',
            'meta[name="thumbnail"]',
            'meta[name="image"]'
        ]
        
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                content = meta.get('content')
                if content.startswith('http'):
                    thumbnails.append({
                        'type': 'meta_tag',
                        'url': content,
                        'source': selector
                    })
        
        return thumbnails
    
    def extract_thumbnail_from_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất thumbnails từ img tags"""
        thumbnails = []
        
        # Tìm kiếm các img tags có thể là thumbnail
        img_selectors = [
            'img[class*="thumbnail"]',
            'img[class*="thumb"]',
            'img[class*="preview"]',
            'img[alt*="thumbnail"]',
            'img[alt*="preview"]'
        ]
        
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src', '')
                if src and src.startswith('http'):
                    thumbnails.append({
                        'type': 'img_tag',
                        'url': src,
                        'source': selector,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    })
        
        return thumbnails
    
    def extract_thumbnail_from_scripts(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất thumbnails từ scripts"""
        thumbnails = []
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Tìm kiếm thumbnailUrl pattern
                import re
                thumbnail_patterns = [
                    r'thumbnailUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'thumbnail["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'image["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'preview["\']?\s*:\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in thumbnail_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if match.startswith('http'):
                            thumbnails.append({
                                'type': 'script',
                                'url': match,
                                'source': 'script_pattern'
                            })
        
        return thumbnails
    
    def extract_other_streams(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất các link stream khác"""
        other_streams = []
        
        # Tìm kiếm các link stream
        stream_links = soup.find_all('a', href=True)
        for link in stream_links:
            href = link.get('href', '')
            title = link.get_text(strip=True) or link.get('title', 'Stream Link')
            
            # Kiểm tra các loại stream
            if any(ext in href.lower() for ext in ['.m3u8', '.mp4', '.flv', '.avi', '.mov']):
                other_streams.append({
                    'type': 'video_stream',
                    'url': href,
                    'title': title,
                    'format': href.split('.')[-1].upper()
                })
            elif 'rtmp://' in href.lower() or 'rtsp://' in href.lower():
                other_streams.append({
                    'type': 'rtmp_rtsp',
                    'url': href,
                    'title': title
                })
            elif 'stream' in href.lower() or 'live' in href.lower():
                other_streams.append({
                    'type': 'stream_link',
                    'url': href,
                    'title': title
                })
        
        # Tìm kiếm trong video tags
        video_tags = soup.find_all('video')
        for video in video_tags:
            src = video.get('src', '')
            if src:
                other_streams.append({
                    'type': 'video_tag',
                    'url': src,
                    'title': video.get('title', 'Video Stream')
                })
        
        return other_streams
    
    def extract_embed_codes(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Trích xuất embed codes"""
        embed_codes = []
        
        # Tìm kiếm embed tags
        embeds = soup.find_all('embed')
        for embed in embeds:
            src = embed.get('src', '')
            if src:
                embed_codes.append({
                    'type': 'embed',
                    'url': src,
                    'title': embed.get('title', 'Embed Stream')
                })
        
        # Tìm kiếm object tags
        objects = soup.find_all('object')
        for obj in objects:
            data = obj.get('data', '')
            if data:
                embed_codes.append({
                    'type': 'object',
                    'url': data,
                    'title': obj.get('title', 'Object Stream')
                })
        
        return embed_codes
        
    # Đã xoá hàm take_screenshot vì không cần chụp screenshot nữa
            
    def crawl_urls_from_file(self, file_path: str, use_selenium: bool = False) -> List[Dict[str, Any]]:
        """Crawl tất cả URLs từ file"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
                
            logger.info(f"Tìm thấy {len(urls)} URLs để crawl")
            
            for i, url in enumerate(urls, 1):
                logger.info(f"Đang crawl URL {i}/{len(urls)}: {url}")
                
                if use_selenium:
                    result = self.crawl_with_selenium(url)
                else:
                    result = self.crawl_with_requests(url)
                    
                if result:
                    results.append(result)
                    
                # Delay giữa các request
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Lỗi khi đọc file URLs: {e}")
            
        return results
        
    def save_results(self, results: List[Dict[str, Any]], output_format: str = 'json') -> str:
        """Lưu kết quả crawl"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == 'json':
            filename = f"crawl_results_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
        elif output_format.lower() == 'csv':
            filename = f"crawl_results_{timestamp}.csv"
            df = pd.DataFrame(results)
            df.to_csv(filename, index=False, encoding='utf-8')
            
        elif output_format.lower() == 'excel':
            filename = f"crawl_results_{timestamp}.xlsx"
            df = pd.DataFrame(results)
            df.to_excel(filename, index=False, engine='openpyxl')
            
        logger.info(f"Đã lưu kết quả vào file: {filename}")
        return filename


def extract_minimal(driver, url: str) -> Dict[str, Any]:
    """Extract minimal info (embedUrl, contentUrl, thumbnailUrl, country, city, title)
    using the same logic that works in save_results.py."""
    # Force English path if needed
    if '/vi/' in url:
        url_to_visit = url.replace('/vi/', '/en/')
    else:
        url_to_visit = url

    driver.get(url_to_visit)

    # Wait for page body
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(2)  # small render delay

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Title: prioritize h1.page-heading
    title_text = ''
    h1_heading = soup.find('h1', class_='page-heading')
    if h1_heading and h1_heading.get_text(strip=True):
        title_text = h1_heading.get_text(strip=True)
    else:
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
        if not title_text:
            h1_tags = soup.find_all('h1')
            if h1_tags:
                title_text = h1_tags[0].get_text(strip=True)

    # Extract YouTube from JSON-LD
    youtube_streams: Dict[str, Any] = {}
    thumbnails: List[Dict[str, Any]] = []
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        text = (script.string or script.get_text() or '').strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue

        def _harvest_from_obj(obj: Dict[str, Any]):
            if not isinstance(obj, dict):
                return
            embed = obj.get('embedUrl')
            content = obj.get('contentUrl')
            thumb = obj.get('thumbnailUrl')
            if embed and 'embedUrl' not in youtube_streams:
                youtube_streams['embedUrl'] = embed
            if content and 'contentUrl' not in youtube_streams:
                youtube_streams['contentUrl'] = content
            if thumb and 'thumbnailUrl' not in youtube_streams:
                if isinstance(thumb, list) and thumb:
                    youtube_streams['thumbnailUrl'] = thumb[0]
                elif isinstance(thumb, str):
                    youtube_streams['thumbnailUrl'] = thumb
            # Thumbnails list
            if thumb:
                thumb_url = thumb[0] if isinstance(thumb, list) and thumb else thumb
                if thumb_url:
                    thumbnails.append({'type': 'json_ld', 'url': thumb_url, 'source': 'thumbnailUrl'})
            # Recurse graph
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
            if 'embedUrl' not in youtube_streams:
                youtube_streams['embedUrl'] = src
            if '/embed/' in src:
                video_id = src.split('/embed/')[-1].split('?')[0]
                if 'contentUrl' not in youtube_streams:
                    youtube_streams['contentUrl'] = f'https://www.youtube.com/watch?v={video_id}'

    # Thumbnail meta fallback
    if not youtube_streams.get('thumbnailUrl'):
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and og_image.get('content'):
            youtube_streams['thumbnailUrl'] = og_image.get('content')
            thumbnails.append({'type': 'meta', 'url': og_image.get('content'), 'source': 'og:image'})
        else:
            tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if tw_image and tw_image.get('content'):
                youtube_streams['thumbnailUrl'] = tw_image.get('content')
                thumbnails.append({'type': 'meta', 'url': tw_image.get('content'), 'source': 'twitter:image'})

    # Map info + coordinates
    try:
        map_info = extract_map_information(soup, driver)
    except Exception:
        map_info = {'openstreetmap': {}, 'google_maps': {}, 'other_maps': []}

    coordinates: Dict[str, Any] = {}
    try:
        coordinates = extract_openstreetmap_coordinates(soup, driver)
    except Exception:
        coordinates = {}
    if not coordinates.get('latitude'):
        try:
            coordinates2 = extract_coordinates(soup, driver)
            if coordinates2:
                coordinates.update(coordinates2)
        except Exception:
            pass

    # Breadcrumbs to compute country/city
    country = ''
    city = ''
    try:
        from urllib.parse import urlparse
        breadcrumbs = []
        navs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
        for nav in navs:
            trail = []
            for a in nav.find_all('a'):
                trail.append({'text': a.get_text(strip=True), 'url': a.get('href', ''), 'title': a.get('title', '')})
            if trail:
                breadcrumbs.append(trail)
        # country
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
    except Exception:
        pass
    if not country:
        from urllib.parse import urlparse
        parts = urlparse(url_to_visit).path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'countries':
            country = parts[1].replace('-', ' ').title()

    # city
    try:
        from urllib.parse import urlparse
        for trail in breadcrumbs or []:
            for crumb in trail:
                href = str(crumb.get('url', ''))
                title_attr = str(crumb.get('title', '')).strip()
                parts = urlparse(href).path.strip('/').split('/')
                if len(parts) == 3 and parts[0] == 'countries':
                    city = title_attr or parts[2].replace('-', ' ').title()
                    raise StopIteration
    except StopIteration:
        pass
    except Exception:
        pass
    if not city:
        from urllib.parse import urlparse
        parts = urlparse(url_to_visit).path.strip('/').split('/')
        if len(parts) >= 3 and parts[0] == 'countries':
            city = parts[2].replace('-', ' ').title()
    if not city:
        try:
            city = infer_city_english({'location': {'breadcrumbs': breadcrumbs}, 'page_info': {'title': title_text}}, url_to_visit)
        except Exception:
            city = ''
    if not city:
        city = country

    minimal_result = {
        'embedUrl': youtube_streams.get('embedUrl', ''),
        'contentUrl': youtube_streams.get('contentUrl', ''),
        'thumbnailUrl': youtube_streams.get('thumbnailUrl', ''),
        'country': country,
        'city': city,
        'title': title_text,
    }

    return minimal_result


def main():
    """Hàm chính - minimal mode mặc định: xuất country.json per URL"""
    print("=== Webcam Data Crawler Tool (Minimal) ===")
    from selenium.webdriver.chrome.options import Options
    from fake_useragent import UserAgent

    # Đọc URL từ url.txt
    try:
        with open('url.txt', 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print('❌ Không tìm thấy url.txt')
        return

    # Selenium English options
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
        for url in urls:
            print(f'Processing: {url}')
            data = extract_minimal(driver, url)
            # Guard: fix misparsed country/city if needed using breadcrumb anchors (kept from previous logic)
            try:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                # Collect breadcrumbs
                breadcrumbs = []
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
                # Compute country/city by path segments
                from urllib.parse import urlparse
                country_fix = ''
                city_fix = ''
                for trail in breadcrumbs:
                    for crumb in trail:
                        href = str(crumb.get('url', ''))
                        title_attr = str(crumb.get('title', '')).strip()
                        parts = urlparse(href).path.strip('/').split('/')
                        if len(parts) == 2 and parts[0] == 'countries' and not country_fix:
                            country_fix = title_attr or parts[1].replace('-', ' ').title()
                        elif len(parts) == 3 and parts[0] == 'countries' and not city_fix:
                            city_fix = title_attr or parts[2].replace('-', ' ').title()
                # Apply fixes if detected bad values
                if (not data.get('country')) or (str(data.get('country')).strip().lower() in ['countries', '']):
                    if country_fix:
                        data['country'] = country_fix
                if (not data.get('city')) or (str(data.get('city')).strip().lower() in ['countries', 'country', 'australia'] and city_fix):
                    data['city'] = city_fix or data.get('city') or data.get('country')
                if not data.get('city'):
                    data['city'] = data.get('country')
            except Exception:
                pass
            # Filter: only keep items where contentUrl host is YouTube
            from urllib.parse import urlparse
            content_url = data.get('contentUrl')
            if not content_url:
                print('  -> Skip: no contentUrl')
                continue
            host = urlparse(content_url).netloc.lower()
            if not any(d in host for d in ['youtube.com', 'youtu.be', 'youtube-nocookie.com']):
                print(f"  -> Skip: contentUrl not YouTube ({host})")
                continue
            safe_country = (data.get('country') or 'Unknown').strip().replace(' ', '_')
            out_file = f'{safe_country}.json'
            # Merge/append per country
            try:
                if os.path.exists(out_file):
                    try:
                        existing = json.load(open(out_file, 'r', encoding='utf-8'))
                    except Exception:
                        existing = None
                    merged = None
                    if isinstance(existing, list):
                        # Lọc bỏ entries cũ không có URL
                        existing = [it for it in existing if isinstance(it, dict) and (it.get('embedUrl') or it.get('contentUrl'))]
                        keys = {(item.get('embedUrl'), item.get('title')) for item in existing if isinstance(item, dict)}
                        if (data.get('embedUrl'), data.get('title')) not in keys and (data.get('embedUrl') or data.get('contentUrl')):
                            existing.append(data)
                        merged = existing
                    elif isinstance(existing, dict) and existing:
                        # Nếu dict cũ không có URL thì bỏ
                        merged = [existing] if (existing.get('embedUrl') or existing.get('contentUrl')) else []
                        if (data.get('embedUrl') or data.get('contentUrl')) and not (existing.get('embedUrl') == data.get('embedUrl') and existing.get('title') == data.get('title')):
                            merged.append(data)
                    else:
                        merged = [data]
                    json.dump(merged, open(out_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
                else:
                    json.dump(data, open(out_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            except Exception:
                json.dump(data, open(out_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f'  -> Saved {out_file}')
    finally:
        driver.quit()
    print('🎉 Done.')

if __name__ == "__main__":
    main()
