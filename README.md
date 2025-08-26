# Webcam Data Crawler Tool

Tool crawl data từ các webcam streaming URLs, được thiết kế đặc biệt cho việc thu thập thông tin từ các trang webcam.

## Tính năng

- ✅ **Web Scraping**: Sử dụng cả Requests và Selenium
- ✅ **Data Extraction**: Trích xuất thông tin tiêu đề, mô tả, vị trí, thông tin camera
- ✅ **Multiple Output Formats**: JSON, CSV, Excel
- ✅ **Screenshot**: Chụp ảnh màn hình trang web
- ✅ **Logging**: Ghi log chi tiết quá trình crawl
- ✅ **Error Handling**: Xử lý lỗi và retry
- ✅ **User Agent Rotation**: Thay đổi User Agent để tránh bị chặn
- ✅ **Configurable**: Dễ dàng cấu hình các thông số

## Cài đặt

### 1. Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Cài đặt Chrome/Chromium (cho Selenium)

Tool sử dụng Chrome WebDriver để crawl JavaScript-heavy pages. Đảm bảo bạn đã cài đặt Chrome hoặc Chromium.

## Sử dụng

### 1. Chuẩn bị file URLs

Tạo file `url.txt` với danh sách URLs cần crawl, mỗi URL một dòng:

```
https://webcamera24.com/vi/camera/vietnam/quang-trung-st-cam/
https://webcamera24.com/vi/camera/vietnam/another-camera/
```

### 2. Chạy crawler

```bash
python crawler.py
```

### 3. Kết quả

Tool sẽ tạo các file output:
- `crawl_results_YYYYMMDD_HHMMSS.json` - Kết quả dạng JSON
- `crawl_results_YYYYMMDD_HHMMSS.csv` - Kết quả dạng CSV  
- `crawl_results_YYYYMMDD_HHMMSS.xlsx` - Kết quả dạng Excel
- `screenshots/` - Thư mục chứa screenshots
- `crawler.log` - File log chi tiết

## Cấu hình

### Thay đổi cấu hình trong `config.py`:

```python
CRAWLER_CONFIG = {
    'request_delay': 2,      # Delay giữa requests
    'timeout': 30,           # Timeout cho requests
    'max_retries': 3,        # Số lần retry
    'headless': True,        # Chế độ headless
    'screenshot': True,      # Có chụp screenshot không
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

## Cách hoạt động

### 1. Requests-based Crawling (Mặc định)
- Nhanh và hiệu quả
- Phù hợp với static HTML pages
- Sử dụng BeautifulSoup để parse HTML

### 2. Selenium-based Crawling
- Chậm hơn nhưng mạnh mẽ hơn
- Xử lý được JavaScript-heavy pages
- Có thể chụp screenshot
- Tự động cài đặt ChromeDriver

## Data được trích xuất

- **URL**: URL gốc
- **Title**: Tiêu đề trang
- **Description**: Mô tả trang
- **Location**: Thông tin vị trí (từ URL và nội dung trang)
  - **breadcrumbs**: Breadcrumb navigation
  - **location_from_url**: Vị trí trích xuất từ URL
  - **location_from_page**: Vị trí trích xuất từ nội dung trang
  - **coordinates**: Tọa độ từ OpenStreetMap
    - **latitude**: Vĩ độ
    - **longitude**: Kinh độ
    - **zoom**: Mức zoom
    - **source**: Nguồn tọa độ (openstreetmap_center, json_ld, meta_tags, etc.)
- **Camera Info**: Thông tin chi tiết về camera và streams
  - **embedUrl**: YouTube embed URL
  - **contentUrl**: YouTube content URL
  - **thumbnailUrl**: Thumbnail URL chính
  - **thumbnails**: Danh sách tất cả thumbnail URLs
  - **other_streams**: Các link stream khác (m3u8, mp4, rtmp, etc.)
  - **embed_codes**: Các embed codes
- **Map Info**: Thông tin bản đồ
  - **openstreetmap**: Thông tin OpenStreetMap (type, center_lat, center_lon, zoom, tile_layer)
  - **google_maps**: Thông tin Google Maps
  - **other_maps**: Các loại bản đồ khác
- **Screenshot**: Đường dẫn file screenshot (nếu có)
- **Timestamp**: Thời gian crawl
- **Status**: Trạng thái crawl (success/error)

## Ví dụ output

```json
{
  "url": "https://webcamera24.com/vi/camera/vietnam/quang-trung-st-cam/",
  "timestamp": "2025-08-25T11:42:22.123456",
  "method": "selenium",
  "status": "success",
  "page_info": {
    "title": "Webcam trực tuyến Quang Trung, Đà Nẵng",
    "h1": "Quang Trung, Đà Nẵng phát trực tiếp qua webcam",
    "meta_description": "Webcam trực tiếp trên đường phố này cho bạn thấy đường Quang Trung bận rộn và bên phải trường trung học Nguyễn Huệ nằm ở thành phố lớn Đà Nẵng, huyện Hải Châu",
    "content_length": 236411
  },
  "location": {
    "breadcrumbs": [
      [
        {"text": "Chủ chốt", "url": "/vi/"},
        {"text": "Quốc gia", "url": "/vi/countries/"},
        {"text": "Việt Nam", "url": "/vi/countries/vietnam/"},
        {"text": "Đà Nẵng", "url": "/vi/countries/vietnam/da-nang/"},
        {"text": "Quang Trung, Đà Nẵng", "url": "/vi/camera/vietnam/quang-trung-st-cam/"}
      ]
    ],
    "location_from_url": "Vietnam",
    "location_from_page": "Quang Trung, Đà Nẵng phát trực tiếp qua webcam",
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

### Lỗi ChromeDriver
```bash
# Tự động cài đặt ChromeDriver
pip install webdriver-manager
```

### Lỗi permissions
```bash
# Cấp quyền thực thi
chmod +x crawler.py
```

### Lỗi dependencies
```bash
# Cài đặt lại dependencies
pip install --upgrade -r requirements.txt
```

## Tính năng nâng cao

### 1. Custom Data Extraction
Chỉnh sửa các method trong class `WebcamCrawler` để trích xuất thông tin cụ thể:

```python
def extract_custom_info(self, soup):
    # Logic trích xuất tùy chỉnh
    pass
```

### 2. Proxy Support
Thêm proxy để tránh bị chặn:

```python
proxies = {
    'http': 'http://proxy:port',
    'https': 'https://proxy:port'
}
self.session.proxies.update(proxies)
```

### 3. Rate Limiting
Điều chỉnh delay giữa các requests:

```python
time.sleep(CRAWLER_CONFIG['request_delay'])
```

## Bảo mật

- Tool sử dụng User Agent rotation để tránh bị phát hiện
- Có thể thêm proxy để ẩn IP
- Respect robots.txt (cần implement thêm)
- Delay giữa requests để không gây quá tải server

## License

MIT License - Sử dụng tự do cho mục đích cá nhân và thương mại.

## Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo issue hoặc pull request.
