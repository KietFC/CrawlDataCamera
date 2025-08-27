#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for Webcam Data Crawler
"""

 # General configuration
CRAWLER_CONFIG = {
    'request_delay': 2,  # Delay between requests (seconds)
    'timeout': 30,       # Timeout for requests (seconds)
    'max_retries': 3,    # Maximum number of retries
    'headless': True,    # Run browser in headless mode
    'screenshot': True,  # Take screenshot or not
}

 # Output configuration
OUTPUT_CONFIG = {
    'default_format': 'json',  # json, csv, excel
    'encoding': 'utf-8',
    'indent': 2,
}

 # Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'crawler.log',
}

 # User Agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
]

 # Default headers
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

 # Selenium configuration
SELENIUM_CONFIG = {
    'window_size': '1920,1080',
    'no_sandbox': True,
    'disable_dev_shm_usage': True,
    'disable_gpu': True,
    'disable_extensions': True,
    'disable_plugins': True,
}

 # Data extraction configuration
EXTRACTION_CONFIG = {
    'title_selectors': ['title', 'h1', '.title', '.page-title', '.main-title', '.heading', '.header-title'],
    'description_selectors': [
        'meta[name="description"]', 
        'meta[property="og:description"]', 
        '.description', 
        '.desc', 
        '.summary', 
        '.intro', 
        '.content-summary'
    ],
    'location_selectors': [
        '.location', 
        '.address', 
        '[class*="location"]', 
        '[class*="address"]', 
        '[class*="city"]', 
        '[class*="country"]',
        '.breadcrumb',
        '.nav-breadcrumb'
    ],
    'camera_selectors': [
        '.camera-info', 
        '.stream-info', 
        '[class*="camera"]', 
        '[class*="stream"]',
        '.webcam-info',
        '.live-info',
        '.status-info'
    ],
    'stream_extensions': ['.m3u8', '.mp4', '.flv', '.avi', '.mov'],
    'youtube_patterns': [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'youtu\.be/([a-zA-Z0-9_-]+)',
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
    ]
}
