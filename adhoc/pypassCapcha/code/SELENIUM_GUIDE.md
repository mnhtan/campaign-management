# 🤖 SELENIUM GOOGLE NEWS CRAWLER GUIDE

## Tổng quan
Phiên bản Selenium của Google News Crawler giúp lấy được **current URLs thực tế** thay vì Google redirect URLs. Điều này rất hữu ích khi bạn muốn có URLs trực tiếp đến bài báo gốc.

## ✨ Tính năng mới với Selenium

### 🎯 Ưu điểm:
- ✅ Lấy được **URLs thực tế** (không phải redirect)
- ✅ **Bypass CAPTCHA** hiệu quả hơn
- ✅ Mô phỏng người dùng thực tế
- ✅ **Auto fallback** về RSS nếu Selenium fail
- ✅ Headless mode (chạy ẩn browser)

### ⚠️ Nhược điểm:
- ⏳ **Chậm hơn** RSS (vì phải mở browser)
- 💾 **Tốn RAM** hơn (Chrome process)
- 🔧 Cần **Chrome browser** được cài đặt

## 🔧 Cài đặt

### Bước 1: Cài đặt packages
```bash
# Tạo file requirements
python pypassCapcha.py --selenium-setup

# Cài đặt packages
pip install -r requirements_selenium.txt
```

### Bước 2: Kiểm tra Chrome
- Đảm bảo **Chrome browser** đã được cài đặt
- ChromeDriver sẽ tự động download lần đầu chạy

### Bước 3: Test thử
```bash
# Test demo
python pypassCapcha.py --selenium-demo

# Hoặc chọn option 5 trong menu
python pypassCapcha.py
```

## 🚀 Cách sử dụng

### 1. Demo Test (Nhanh)
```bash
python pypassCapcha.py --selenium-demo
```
- Test với 3 keywords: "artificial intelligence", "climate change", "technology"
- Mỗi keyword lấy 5 bài
- Kết quả xuất ra `selenium_demo_[timestamp].csv`

### 2. Bulk Crawl với Selenium
```bash
python pypassCapcha.py
# Chọn option 6: 🤖 Selenium bulk crawl
```
- Đọc keywords từ `keyword_csvs/Keywords.csv`
- Cho phép chọn số bài mỗi keyword (default 20)
- Kết quả xuất ra `selenium_crawl_[timestamp].csv`

### 3. Selenium + RSS Fallback
Hệ thống sẽ:
1. **Thử Selenium trước** để lấy URLs thực tế
2. Nếu Selenium fail → **Fallback về RSS**
3. Đảm bảo luôn có kết quả

## 📊 So sánh Output

### RSS Mode (Cũ):
```csv
headline,link,date,source
"AI breakthrough in 2024","https://news.google.com/articles/xyz123...",Recent,TechNews
```

### Selenium Mode (Mới):
```csv
headline,link,date,source,method
"AI breakthrough in 2024","https://technews.com/ai-breakthrough-2024/",Recent,technews.com,Selenium+RSS
```

## ⚙️ Cấu hình nâng cao

### Tùy chỉnh Selenium Options:
Trong class `GoogleNewsScraper._setup_selenium_driver()`:

```python
# Thêm proxy
chrome_options.add_argument(f'--proxy-server=http://{proxy}')

# Tắt headless mode (hiện browser)
# chrome_options.add_argument('--headless')  # Comment dòng này

# Tăng timeout
WebDriverWait(self.driver, 30)  # Thay vì 10 giây
```

### Tùy chỉnh delay:
```python
# Trong bulk_crawl_with_selenium()
delay = random.uniform(5, 10)  # Giảm delay nếu muốn nhanh hơn
```

## 🐛 Troubleshooting

### Lỗi ChromeDriver:
```
WebDriverException: chromedriver executable needs to be in PATH
```
**Giải pháp:**
- Đảm bảo Chrome browser đã cài đặt
- Chạy lại, `webdriver-manager` sẽ tự download ChromeDriver

### Lỗi Timeout:
```
TimeoutException: Timeout khi tải trang Google News
```
**Giải pháp:**
- Kiểm tra internet connection
- Tăng timeout trong code
- Thử lại sau vài phút

### Selenium fail hoàn toàn:
- Hệ thống sẽ **tự động fallback về RSS**
- Vẫn có được kết quả, chỉ không phải URLs thực tế

### RAM/CPU cao:
- Selenium sử dụng Chrome process → tốn tài nguyên
- Có thể giảm số bài mỗi keyword
- Hoặc dùng RSS mode cho crawl lớn

## 📈 Performance Tips

### 1. Hybrid Strategy:
```python
# Dùng Selenium cho keywords quan trọng
important_keywords = ["AI", "blockchain"]
selenium_results = bulk_crawl_with_selenium(important_keywords, 10)

# Dùng RSS cho keywords thông thường  
normal_keywords = ["other keywords..."]
rss_results = bulk_crawl_to_csv(normal_keywords, 5, 20)
```

### 2. Batch Processing:
- Chia keywords thành batches nhỏ
- Chạy Selenium cho từng batch
- Tránh Chrome process chạy quá lâu

### 3. Memory Management:
```python
# Trong code, driver được đóng sau mỗi keyword
scraper.close_selenium()  # Giải phóng memory
```

## 🎯 Khi nào dùng Selenium?

### ✅ Nên dùng Selenium khi:
- Cần **URLs thực tế** (không phải Google redirect)
- Bị **CAPTCHA** thường xuyên với RSS
- Crawl **keywords nhạy cảm** (dễ bị block)
- Số lượng **ít keywords** (<50)

### ❌ Không nên dùng Selenium khi:
- Crawl **số lượng lớn** (>100 keywords)
- Máy **yếu** (RAM < 4GB)
- Cần **tốc độ nhanh**
- **Chạy trên server** không có GUI

## 🔄 Workflow đề xuất

```
1. Test với Selenium demo → Kiểm tra hoạt động
2. Chạy 1-2 keywords thật → Xem chất lượng URLs  
3. Quyết định strategy:
   - URLs thực tế quan trọng → Selenium bulk
   - Chỉ cần data nhanh → RSS mode
4. Monitor performance và adjust
```

## 📞 Support

Nếu gặp vấn đề:
1. Chạy `--selenium-demo` để test
2. Kiểm tra Chrome version
3. Thử RSS fallback mode
4. Check firewall/antivirus settings 