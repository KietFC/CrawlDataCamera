#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chạy Webcam Data Crawler với các tùy chọn
"""

import argparse
import sys
from crawler import WebcamCrawler
from config import CRAWLER_CONFIG, OUTPUT_CONFIG
from save_results_multi import extract_minimal  # reuse minimal extractor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from datetime import datetime
import json

def main():
    parser = argparse.ArgumentParser(
        description='Webcam Data Crawler Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python run_crawler.py                           # Chạy với cấu hình mặc định
  python run_crawler.py --selenium                # Sử dụng Selenium
  python run_crawler.py --format csv              # Output dạng CSV
  python run_crawler.py --urls custom_urls.txt    # Sử dụng file URLs tùy chỉnh
  python run_crawler.py --delay 5                 # Delay 5 giây giữa requests
        """
    )
    
    parser.add_argument(
        '--selenium',
        action='store_true',
        help='Sử dụng Selenium thay vì Requests'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'excel'],
        default=OUTPUT_CONFIG['default_format'],
        help='Định dạng output (mặc định: json)'
    )
    parser.add_argument(
        '--minimal',
        action='store_true',
        help='Xuất kết quả tối giản và lưu file theo tên country (country.json)'
    )
    
    parser.add_argument(
        '--urls',
        default='url.txt',
        help='File chứa danh sách URLs (mặc định: url.txt)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=CRAWLER_CONFIG['request_delay'],
        help=f'Delay giữa các requests (mặc định: {CRAWLER_CONFIG["request_delay"]}s)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=CRAWLER_CONFIG['headless'],
        help='Chạy browser ở chế độ headless'
    )
    
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Hiển thị thông tin chi tiết'
    )
    
    args = parser.parse_args()
    
    print("=== Webcam Data Crawler Tool ===")
    print(f"URLs file: {args.urls}")
    print(f"Output format: {args.format}")
    print(f"Minimal: {args.minimal}")
    print(f"Method: {'Selenium' if args.selenium else 'Requests'}")
    print(f"Delay: {args.delay}s")
    print(f"Headless: {args.headless}")
    # print(f"Screenshot: {args.screenshot}")
    print("=" * 40)
    
    try:
        if args.minimal:
            # Minimal flow using Selenium (English locale) and save country.json per URL
            # Read URLs
            try:
                with open(args.urls, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"❌ Không tìm thấy file {args.urls}")
                sys.exit(1)

            # Chrome options
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
                    print(f"Processing: {url}")
                    data = extract_minimal(driver, url)
                    # Post-fix country/city via breadcrumb anchors like crawler.py
                    try:
                        html = driver.page_source
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        breadcrumbs = []
                        navs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in x.lower())
                        for nav in navs:
                            trail = []
                            for a in nav.find_all('a'):
                                trail.append({'text': a.get_text(strip=True), 'url': a.get('href',''), 'title': a.get('title','')})
                            if trail:
                                breadcrumbs.append(trail)
                        from urllib.parse import urlparse
                        country_fix = ''
                        city_fix = ''
                        for trail in breadcrumbs:
                            for crumb in trail:
                                href = str(crumb.get('url',''))
                                title_attr = str(crumb.get('title','')).strip()
                                parts = urlparse(href).path.strip('/').split('/')
                                if len(parts) == 2 and parts[0] == 'countries' and not country_fix:
                                    country_fix = title_attr or parts[1].replace('-', ' ').title()
                                elif len(parts) == 3 and parts[0] == 'countries' and not city_fix:
                                    city_fix = title_attr or parts[2].replace('-', ' ').title()
                        if (not data.get('country')) or (str(data.get('country')).strip().lower() in ['countries','']):
                            if country_fix:
                                data['country'] = country_fix
                        if (not data.get('city')) or (str(data.get('city')).strip().lower() in ['countries','country', data.get('country','').lower()]):
                            if city_fix:
                                data['city'] = city_fix
                        if not data.get('city'):
                            data['city'] = data.get('country')
                    except Exception:
                        pass
                    safe_country = (data.get('country') or 'Unknown').strip().replace(' ', '_')
                    out_file = f"{safe_country}.json"
                    with open(out_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"  -> Saved {out_file}")
            finally:
                driver.quit()
        else:
            # Khởi tạo crawler thường
            crawler = WebcamCrawler(headless=args.headless)
            CRAWLER_CONFIG['request_delay'] = args.delay
            print(f"Đang bắt đầu crawl data từ {args.urls}...")
            results = crawler.crawl_urls_from_file(args.urls, use_selenium=args.selenium)
            if results:
                print(f"\n✅ Đã crawl thành công {len(results)} URLs")
                output_file = crawler.save_results(results, args.format)
                print(f"📁 Kết quả đã được lưu vào: {output_file}")
            else:
                print("❌ Không có kết quả nào được crawl")
            
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file {args.urls}")
        print("Vui lòng tạo file với danh sách URLs, mỗi URL một dòng")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Đã dừng crawl theo yêu cầu của người dùng")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Dọn dẹp
        if 'crawler' in locals():
            crawler.close_driver()
        print("\n🎉 Đã hoàn thành crawl data!")

if __name__ == "__main__":
    main()
