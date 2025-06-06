# 🔥 Google News Batch Crawler - High Frequency Test

## 📋 Tổng quan
Tool này được cập nhật để crawl Google News theo batch với tần suất cao nhằm test xem có bị block hay không.

## ⚙️ Cấu hình Batch
- **Tần suất**: Mỗi 1 tiếng
- **Thời gian hoạt động**: Từ lúc kích hoạt đến khi dừng lại
- **Số bài mỗi keyword**: 10 bài
- **Tổng số bài mỗi batch**: ~600 bài (60 keywords × 10 bài)

## 🚀 Cách sử dụng

### 1. Test thủ công
```bash
python pypassCapcha.py --test
```
Hoặc chọn option 1 khi chạy:
```bash
python pypassCapcha.py
```

### 2. Tạo file setup cho Task Scheduler
```bash
python pypassCapcha.py --setup
```
Hoặc chọn option 2 khi chạy.

### 3. Setup Windows Task Scheduler

1. **Chạy lệnh setup** để tạo file `run_scheduled_crawler.bat`
2. **Mở Task Scheduler** (Windows + R → `taskschd.msc`)
3. **Create Basic Task...**
4. **Cấu hình như sau:**
   - **Name**: Google News Crawler
   - **Trigger**: Once (start immediately)
   - **Start time**: Ngay lập tức
   - **Repeat task every**: 1 hour
   - **For a duration of**: Indefinitely (cho đến khi dừng)
   - **Action**: Start a program
   - **Program/script**: `[đường dẫn đến run_scheduled_crawler.bat]`

### 4. Chạy scheduled crawl thủ công
```bash
python pypassCapcha.py --scheduled
```

## 📁 Cấu trúc file output

### Thư mục `batches/`
Mỗi batch sẽ tạo 1 file CSV với format:
```
batches/batch_20241215_100000.csv
```

### Cấu trúc CSV
```csv
batch_id,keyword,article_number,headline,link,date,source,domain,crawl_timestamp,keyword_index
batch_20241215_100000,AI,1,AI breakthrough in healthcare,https://...,2024-12-15,TechNews,technews.com,2024-12-15 10:05:30,1
```

## 🎯 Mục đích Test
- **Test tần suất cao**: Crawl mỗi 1 tiếng liên tục để test xem có bị Google block không
- **Monitor performance**: Theo dõi success rate, errors, captcha
- **Optimize timing**: Tìm ra tần suất tối ưu không bị chặn
- **24/7 monitoring**: Chạy liên tục để test threshold blocking

## 📊 Monitoring

### Thống kê mỗi batch:
- Batch ID
- Thời gian bắt đầu/kết thúc
- Số keywords processed
- Số articles crawl được
- Success rate
- Tốc độ crawl (keywords/minute, articles/minute)

### Files theo dõi:
- `batches/batch_*.csv` - Dữ liệu mỗi batch
- Console output - Logs real-time

## ⚠️ Lưu ý

1. **Chạy liên tục**: Tool sẽ chạy mỗi tiếng từ lúc kích hoạt đến khi dừng lại
2. **Delay**: Có delay ngắn 1-3 giây giữa các keywords để tránh spam
3. **Error handling**: Có xử lý lỗi và fallback
4. **File structure**: Tự động tạo thư mục `batches/` nếu chưa có
5. **Cách dừng**: Disable/Delete task trong Task Scheduler để dừng

## 🛠️ Troubleshooting

### Lỗi "No keywords loaded"
- Kiểm tra file `keyword_csvs/Keywords.csv` có tồn tại không
- Kiểm tra column name có đúng là "Keywords" không

### Task Scheduler không chạy
- Kiểm tra đường dẫn file .bat có đúng không
- Kiểm tra permissions của file
- Test chạy file .bat thủ công trước

### Bị block/CAPTCHA
- Tool sẽ tự động log số lần bị CAPTCHA
- Có thể điều chỉnh delay nếu cần

## 📈 Next Steps
Sau khi chạy được vài ngày, phân tích data để:
- Xem có pattern nào bị block không
- Tối ưu tần suất crawl
- Điều chỉnh delay nếu cần 