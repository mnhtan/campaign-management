# 📁 GOOGLE NEWS CRAWLER - CẤU TRÚC THƯ MỤC

## 📂 Cấu trúc tổng quan:

```
📁 pypassCapcha/
├── 📁 batches/                    # 📊 Batch crawl results
│   ├── batch_20250606_135643.csv
│   ├── batch_20250606_133929.csv
│   └── ...
├── 📁 code/                       # 💻 Source code
│   ├── pypassCapcha.py           # Main crawler script
│   ├── analyze_batches.py        # Batch analysis tool
│   └── ...
├── 📁 scripts/                    # 🔧 PowerShell & Batch scripts
│   ├── monitor_crawler.ps1       # Interactive monitoring dashboard
│   ├── quick_check.ps1           # Quick status check
│   ├── crawler_commands.ps1      # Command reference
│   ├── run_scheduled_crawler.bat # Task scheduler batch file
│   └── ...
├── 📁 reports/                    # 📈 Analysis reports
│   ├── batch_analysis_report_*.json
│   └── ...
├── 📁 data/                       # 📋 Input data (keywords, etc.)
├── 📄 run_monitoring.bat          # 🖱️ Quick launcher for monitoring
├── 📄 quick_status.bat           # 🖱️ Quick launcher for status check
├── 📄 analyze_results.bat        # 🖱️ Quick launcher for analysis
├── 📄 requirements.txt           # Python dependencies
└── 📄 README.md                  # Main documentation
```

## 🚀 Cách sử dụng nhanh:

### **DOUBLE-CLICK các file .bat từ thư mục gốc:**

- **`run_monitoring.bat`** → Mở dashboard theo dõi crawler
- **`quick_status.bat`** → Kiểm tra trạng thái nhanh
- **`analyze_results.bat`** → Phân tích kết quả batch

### **PowerShell commands (từ thư mục gốc):**

```powershell
# Stop/Start crawler
Disable-ScheduledTask -TaskName "GoogleNewsCrawler"
Enable-ScheduledTask -TaskName "GoogleNewsCrawler"

# View batch files
Get-ChildItem "batches" -Filter "batch_*.csv" | Sort-Object LastWriteTime -Descending

# Get commands reference
cd scripts; powershell -ExecutionPolicy Bypass -File "crawler_commands.ps1"
```

## 📊 Quản lý batch files:

- **Vị trí**: `batches/batch_YYYYMMDD_HHMMSS.csv`
- **Định dạng**: CSV với đầy đủ metadata
- **Tự động**: Crawler tạo file mới mỗi giờ
- **Phân tích**: Chạy `analyze_results.bat` để xem báo cáo

## 📈 Reports & Analytics:

- **Vị trí**: `reports/batch_analysis_report_*.json`
- **Nội dung**: 
  - Thống kê tổng quan
  - Phát hiện blocking patterns
  - Performance trends
  - Keyword analysis

## 🔧 Scripts chính:

### **scripts/monitor_crawler.ps1**
- Dashboard tương tác đầy đủ
- Điều khiển start/stop crawler
- Xem real-time stats
- Chạy test và analysis

### **scripts/quick_check.ps1**  
- Kiểm tra nhanh trạng thái
- Thời gian chạy tiếp theo
- Số batch files hiện có
- Batch gần nhất

### **code/analyze_batches.py**
- Phân tích chi tiết batch results
- Phát hiện blocking patterns
- Export báo cáo JSON
- Timeline performance

## ⚠️ Lưu ý quan trọng:

1. **Luôn chạy từ thư mục gốc** `pypassCapcha/`
2. **Scripts tự động tìm đúng đường dẫn** 
3. **Batch files được lưu tập trung** trong `batches/`
4. **Reports được lưu tập trung** trong `reports/`
5. **Task Scheduler vẫn hoạt động bình thường**

## 🎯 Quick Actions:

```batch
# Từ thư mục gốc pypassCapcha/
run_monitoring.bat     # Mở dashboard
quick_status.bat       # Xem status
analyze_results.bat    # Phân tích kết quả
```

```powershell
# PowerShell commands
cd scripts
.\monitor_crawler.ps1     # Dashboard đầy đủ
.\quick_check.ps1         # Status nhanh
.\crawler_commands.ps1    # Danh sách lệnh
``` 
## Link Google Sheet
[Link tới Google Sheet](https://docs.google.com/spreadsheets/d/13H6XJlU0XD4Aa9bO9QC0NLp8_QWk9dpzGKetJY3rYRE/edit?gid=0#gid=0)