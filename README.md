# Webcam Data Crawler Tool

Tool to crawl data from webcam streaming URLs, designed for collecting information from webcam pages.

## Features

- ✅ **Web Scraping**: Uses both Requests and Selenium
- ✅ **Data Extraction**: Extracts title, description, location, camera info
- ✅ **Multiple Output Formats**: JSON, CSV, Excel
- ✅ **Screenshot**: Capture website screenshots
- ✅ **Logging**: Detailed crawl logs
- ✅ **Error Handling**: Error handling and retries
- ✅ **User Agent Rotation**: Change User Agent to avoid blocking
- ✅ **Configurable**: Easily configurable parameters

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Chrome/Chromium (for Selenium)

This tool uses Chrome WebDriver for JavaScript-heavy pages. Ensure Chrome or Chromium is installed.

## Usage

### 1. Prepare URLs file

Create `url.txt` with the list of URLs to crawl, one per line:

```
https://webcamera24.com/vi/camera/vietnam/quang-trung-st-cam/
https://webcamera24.com/vi/camera/vietnam/another-camera/
```

### 2. Run crawler

```bash
python crawler.py
```

### 3. Results

The tool will create the following outputs:
- `crawl_results_YYYYMMDD_HHMMSS.json` - JSON results
- `crawl_results_YYYYMMDD_HHMMSS.csv` - CSV results  
- `crawl_results_YYYYMMDD_HHMMSS.xlsx` - Excel results
- `screenshots/` - Directory of screenshots
- `crawler.log` - Detailed log file

## Configuration

### Change configuration in `config.py`:

```python
CRAWLER_CONFIG = {
    'request_delay': 2,      # Delay between requests
    'timeout': 30,           # Requests timeout
    'max_retries': 3,        # Number of retries
    'headless': True,        # Headless mode
    'screenshot': True,      # Capture screenshot or not
}
```

### Output formats:

```python
OUTPUT_CONFIG = {
    'default_format': 'json',  # json, csv, excel
    'encoding': 'utf-8',
    'indent': 2,
}
```

## How it works

### 1. Requests-based Crawling (Default)
- Fast and efficient
- Suitable for static HTML pages
- Uses BeautifulSoup to parse HTML

### 2. Selenium-based Crawling
- Slower but more powerful
- Handles JavaScript-heavy pages
- Can capture screenshots
- Auto-manages ChromeDriver

## Extracted Data

- **URL**: Original URL
- **Title**: Page title
- **Description**: Page description
- **Location**: Location info (from URL and page content)
  - **breadcrumbs**: Breadcrumb navigation
  - **location_from_url**: Location extracted from URL
  - **location_from_page**: Location extracted from page content
  - **coordinates**: Coordinates from OpenStreetMap
    - **latitude**: Latitude
    - **longitude**: Longitude
    - **zoom**: Zoom level
    - **source**: Coordinate source (openstreetmap_center, json_ld, meta_tags, etc.)
- **Camera Info**: Detailed camera and streams info
  - **embedUrl**: YouTube embed URL
  - **contentUrl**: YouTube content URL
  - **thumbnailUrl**: Main thumbnail URL
  - **thumbnails**: List of all thumbnail URLs
  - **other_streams**: Other stream links (m3u8, mp4, rtmp, etc.)
  - **embed_codes**: Embed codes
- **Map Info**: Map information
  - **openstreetmap**: OpenStreetMap info (type, center_lat, center_lon, zoom, tile_layer)
  - **google_maps**: Google Maps info
  - **other_maps**: Other map types
- **Screenshot**: Screenshot file path (if any)
- **Timestamp**: Crawl time
- **Status**: Crawl status (success/error)

## Example output

```json
{
  "url": "https://webcamera24.com/en/camera/vietnam/quang-trung-st-cam/",
  "timestamp": "2025-08-25T11:42:22.123456",
  "method": "selenium",
  "status": "success",
  "page_info": {
    "title": "Quang Trung Street, Da Nang - Live Webcam",
    "h1": "Quang Trung, Da Nang live via webcam",
    "meta_description": "This live street webcam shows busy Quang Trung Street with Nguyen Hue High School on the right, located in Da Nang city, Hai Chau district.",
    "content_length": 236411
  },
  "location": {
    "breadcrumbs": [
      [
        {"text": "Home", "url": "/en/"},
        {"text": "Countries", "url": "/en/countries/"},
        {"text": "Vietnam", "url": "/en/countries/vietnam/"},
        {"text": "Da Nang", "url": "/en/countries/vietnam/da-nang/"},
        {"text": "Quang Trung, Da Nang", "url": "/en/camera/vietnam/quang-trung-st-cam/"}
      ]
    ],
    "location_from_url": "Vietnam",
    "location_from_page": "Quang Trung, Da Nang live via webcam",
    "coordinates": {
      "latitude": "16.0544",
      "longitude": "108.2022",
      "zoom": "15",
      "source": "openstreetmap_center"
    }
  },
  "camera_info": {
    "youtube_streams": {
      "embedUrl": "https://www.youtube-nocookie.com/embed/xCNRP131kNY",
      "contentUrl": "https://www.youtube.com/watch?v=xCNRP131kNY",
      "thumbnailUrl": "https://cdn.webcamera24.com/static/image/camera/detail/quang-trung-st-cam-webcamtaxi/thumbnail/968x545/maxresdefault.webp"
    },
    "thumbnails": [
      {
        "type": "json_ld",
        "url": "https://cdn.webcamera24.com/static/image/camera/detail/quang-trung-st-cam-webcamtaxi/thumbnail/968x545/maxresdefault.webp",
        "source": "thumbnailUrl"
      }
    ],
    "other_streams": [],
    "embed_codes": []
  },
  "map_info": {
    "openstreetmap": {
      "type": "leaflet",
      "center_lat": "16.0544",
      "center_lon": "108.2022",
      "zoom": "15",
      "tile_layer": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    },
    "google_maps": {},
    "other_maps": []
  }
}
```

## Troubleshooting

### ChromeDriver errors
```bash
# Auto install ChromeDriver
pip install webdriver-manager
```

### Permission errors
```bash
# Grant execute permission
chmod +x crawler.py
```

### Dependency errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## Advanced features

### 1. Custom Data Extraction
Edit methods in class `WebcamCrawler` to extract specific info:

```python
def extract_custom_info(self, soup):
    # Custom extraction logic
    pass
```

### 2. Proxy Support
Add proxy to avoid blocking:

```python
proxies = {
    'http': 'http://proxy:port',
    'https': 'https://proxy:port'
}
self.session.proxies.update(proxies)
```

### 3. Rate Limiting
Adjust delay between requests:

```python
time.sleep(CRAWLER_CONFIG['request_delay'])
```

## Security

- Uses User Agent rotation to avoid detection
- You may add proxy to hide IP
- Respect robots.txt (needs implementation)
- Delay between requests to avoid server overload

## License

MIT License - Free for personal and commercial use.

## Contributing

Contributions are welcome! Please open an issue or pull request.
