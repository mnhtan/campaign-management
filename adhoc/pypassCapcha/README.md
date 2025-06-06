# PypassCapcha - Google News Crawler

## Mô tả dự án

PypassCapcha là một công cụ crawling dữ liệu Google News mạnh mẽ, được thiết kế để thu thập tin tức từ Google News mà không bị chặn bởi captcha hay các cơ chế anti-bot. Dự án sử dụng RSS feeds của Google News để đảm bảo tỷ lệ thành công 100% và khả năng crawl quy mô lớn.

## Tính năng chính

### ✅ Crawling ổn định
- **Không bị captcha**: Sử dụng RSS feeds thay vì scraping HTML
- **Tỷ lệ thành công cao**: 97-100% success rate trong testing
- **Xử lý lỗi thông minh**: Tự động retry và skip các request failed

### ✅ Crawling quy mô lớn  
- **Multi-keyword**: Crawl hàng chục keywords cùng lúc
- **Deep crawling**: Lấy ~200 bài báo cho mỗi keyword
- **Keyword variations**: Tự động tạo ra các biến thể của keyword để lấy nhiều bài hơn

### ✅ Xuất dữ liệu linh hoạt
- **CSV export**: Xuất kết quả ra CSV với timestamp
- **CSV input**: Đọc danh sách keywords từ file CSV
- **Structured data**: Dữ liệu được cấu trúc rõ ràng với các trường: keyword, headline, link, date, source, domain

### ✅ Kiểm soát tốc độ
- **Smart delays**: Tự động delay 8-15s giữa các keywords, 2-4s giữa các pages
- **Random timing**: Mô phỏng hành vi người dùng thật
- **Rate limiting**: Tránh gửi quá nhiều request cùng lúc

## Cấu trúc dự án

```
pypassCapcha/
├── code/
│   ├── pypassCapcha_clean.py      # File chính - version sạch và tối ưu
│   ├── pypassCapcha.py           # File gốc với đầy đủ tính năng
│   ├── Keywords.csv              # File chứa danh sách keywords mẫu
│   ├── keyword_csvs/            # Thư mục chứa các file CSV input
│   └── *.csv                    # File kết quả crawl với timestamp
├── requirements.txt             # Danh sách dependencies
└── README.md                   # File này
```

## Hướng dẫn cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd pypassCapcha
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Chuẩn bị file keywords (tùy chọn)
Tạo file CSV chứa danh sách keywords cần crawl:
```csv
keyword
bitcoin news
cryptocurrency trends
dogecoin price
ethereum updates
```

## Hướng dẫn sử dụng

### Chạy crawling cơ bản
```bash
cd code
python pypassCapcha_clean.py
```

### Các tùy chọn crawling

#### 1. Interactive Menu
Chạy file và chọn từ menu:
- Option 1: Crawl keyword đơn lẻ
- Option 2: Crawl multiple keywords thủ công
- Option 3: Crawl từ CSV file
- Option 4: Thoát

#### 2. Direct CSV Processing
Để crawl trực tiếp từ file CSV mà không cần menu:
```python
# Sửa trong main() function
keywords = read_keywords_from_csv("Keywords.csv")
crawl_multiple_keywords_deep(keywords, target_articles_per_keyword=200)
```

#### 3. Programmatic Usage
```python
from pypassCapcha_clean import crawl_multiple_keywords_deep, read_keywords_from_csv

# Đọc keywords từ CSV
keywords = read_keywords_from_csv("your_keywords.csv")

# Crawl với 200 bài/keyword
result_file = crawl_multiple_keywords_deep(
    keywords=keywords,
    target_articles_per_keyword=200
)

print(f"Kết quả được lưu trong: {result_file}")
```

## API và Functions chính

### Core Functions

#### `simple_crawl_rss(keyword, max_results=20)`
- Crawl RSS feed của Google News cho 1 keyword
- Trả về list các NewsArticle objects
- Ít bị chặn nhất, tỷ lệ thành công cao

#### `crawl_multiple_keywords_deep(keywords, target_articles_per_keyword=200)`
- Crawl multiple keywords với deep search
- Mỗi keyword được crawl ~200 bài báo
- Tự động export ra CSV với timestamp

#### `read_keywords_from_csv(csv_file_path, keyword_column=None)`
- Đọc danh sách keywords từ file CSV
- Tự động detect column chứa keywords
- Support cho các format CSV khác nhau

#### `generate_keyword_variations(base_keyword, max_pages=10)`
- Tạo các biến thể của keyword để crawl sâu hơn
- Ví dụ: "AI" → "AI news", "AI latest", "AI trends"
- Giúp lấy nhiều bài báo hơn cho mỗi chủ đề

### Data Structures

#### `NewsArticle`
```python
@dataclass
class NewsArticle:
    headline: str    # Tiêu đề bài báo
    link: str       # Link đến bài báo gốc
    date: str       # Ngày đăng
    source: str     # Nguồn tin (tên website)
```

#### `CrawlStats`
```python
@dataclass  
class CrawlStats:
    total_keywords: int
    total_articles: int
    captcha_skipped: int
    errors: int
    successful_requests: int
    failed_requests: int
```

## Format dữ liệu xuất ra

### CSV Output Format
File CSV kết quả có các cột sau:
- `keyword`: Keyword đã crawl
- `article_number`: Số thứ tự bài báo (1-based)
- `headline`: Tiêu đề bài báo
- `link`: Link đến bài báo gốc  
- `date`: Ngày đăng bài
- `source`: Tên nguồn tin
- `domain`: Domain của nguồn tin
- `crawl_timestamp`: Thời điểm crawl

### Ví dụ CSV output:
```csv
keyword,article_number,headline,link,date,source,domain,crawl_timestamp
bitcoin news,1,"Bitcoin Hits New High Amid Market Rally",https://example.com/bitcoin-high,Mon 02 Dec 2024,CoinDesk,coindesk.com,2024-12-05 14:44:44
bitcoin news,2,"Cryptocurrency Market Analysis for December",https://example.com/crypto-analysis,Mon 02 Dec 2024,CryptoNews,cryptonews.com,2024-12-05 14:44:44
```

## Kết quả thử nghiệm

### Test với 5 keywords crypto:
- **Target**: 1000 bài báo (200/keyword)
- **Kết quả**: 971 bài báo (97.1% target)
- **Success rate**: 100% (0 captcha, 0 blocks)
- **Trung bình**: ~194 bài/keyword
- **Thời gian**: ~15 phút

### Performance metrics:
- **Crawling speed**: ~65 bài/phút
- **Error rate**: <3%
- **Duplicate rate**: ~5-10% (được tự động loại bỏ)
- **Memory usage**: Low (~50MB cho 1000 bài)

## Troubleshooting

### Lỗi thường gặp

#### ImportError: No module named 'bs4'
```bash
pip install beautifulsoup4 lxml
```

#### ImportError: No module named 'fake_useragent'  
```bash
pip install fake-useragent
```

#### Lỗi encoding khi đọc CSV
- Đảm bảo file CSV được save với UTF-8 encoding
- Hoặc sử dụng Excel để save as CSV UTF-8





## Changelog

### Version 2.0 (Current - Clean)
- ✅ Cleaned up code, removed unused features
- ✅ Focus on RSS crawling only (most stable)
- ✅ Improved error handling and logging
- ✅ Better CSV input/output handling
- ✅ Removed dependency on crawlbase API

### Version 1.0 (Legacy)
- ✅ Multiple crawling methods (API, scraping, RSS)
- ✅ Interactive menu system
- ✅ Full-featured but complex

## Link Google Sheet
[Link tới Google Sheet](https://docs.google.com/spreadsheets/d/13H6XJlU0XD4Aa9bO9QC0NLp8_QWk9dpzGKetJY3rYRE/edit?gid=0#gid=0)
