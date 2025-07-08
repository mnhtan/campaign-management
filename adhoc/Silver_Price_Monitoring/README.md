# 🥈 Hệ Thống Theo Dõi Giá Vàng Bạc

Hệ thống tự động theo dõi, phân tích và báo cáo giá vàng và bạc từ nhiều nguồn dữ liệu uy tín, tạo báo cáo PDF chuyên nghiệp và gửi email tự động.

## 📋 Mục Lục

- [Tổng Quan](#-tổng-quan)
- [Tính Năng Chính](#-tính-năng-chính)
- [Cấu Trúc Dự Án](#-cấu-trúc-dự-án)
- [Yêu Cầu Hệ Thống](#-yêu-cầu-hệ-thống)
- [Hướng Dẫn Cài Đặt](#-hướng-dẫn-cài-đặt)
- [Hướng Dẫn Sử Dụng](#-hướng-dẫn-sử-dụng)
- [Cấu Hình](#-cấu-hình)
- [API và Nguồn Dữ Liệu](#-api-và-nguồn-dữ-liệu)
- [Troubleshooting](#-troubleshooting)
- [Đóng Góp](#-đóng-góp)

## 🔍 Tổng Quan

**Silver Price Monitoring** là hệ thống tự động theo dõi giá kim loại quý (vàng và bạc) được phát triển bằng Python. Hệ thống thu thập dữ liệu thực từ nhiều nguồn uy tín, thực hiện phân tích kỹ thuật và tạo báo cáo PDF chuyên nghiệp.

### 🎯 Mục Tiêu
- Theo dõi giá vàng/bạc theo thời gian thực
- Phân tích xu hướng và tạo insights đầu tư
- Tự động hóa việc tạo báo cáo hàng tuần
- Cung cấp dữ liệu lịch sử đáng tin cậy

## ⭐ Tính Năng Chính

### 📊 Thu Thập Dữ Liệu
- **Giá bạc quốc tế**: TradingView XAGUSD (USD/ounce)
- **Giá vàng SJC**: phuquygroup.vn (VND/lượng)
- **Giá bạc Việt Nam**: giabac.vn API (VND/lượng)
- **Lưu trữ**: SQLite database với timestamp

### 📈 Phân Tích Kỹ Thuật
- **Moving Averages**: SMA, EMA
- **RSI (Relative Strength Index)**: Chỉ báo momentum
- **Volatility Analysis**: Phân tích độ biến động
- **Correlation Analysis**: Tương quan giữa các thị trường
- **Support/Resistance**: Xác định vùng hỗ trợ/kháng cự

### 📑 Báo Cáo Tự Động
- **PDF Reports**: Báo cáo chuyên nghiệp với biểu đồ
- **Email Integration**: Gửi báo cáo tự động
- **Time Series Charts**: Biểu đồ xu hướng giá
- **Statistical Insights**: Thống kê và dự báo

### ⏰ Tự Động Hóa
- **Scheduled Tasks**: Thu thập dữ liệu theo lịch
- **Weekly Reports**: Báo cáo hàng tuần tự động
- **Error Handling**: Xử lý lỗi và retry logic
- **Logging System**: Ghi log chi tiết

## 📁 Cấu Trúc Dự Án

```
Silver_Price_Monitoring/
├── 📁 code/                              # Mã nguồn chính
│   ├── 🐍 final_gold_silver_table_with_real_data.py  # Thu thập dữ liệu thực
│   ├── 🐍 giabac.py                      # Hệ thống theo dõi chính
│   └── 🐍 pdf_report_generator.py        # Tạo báo cáo PDF
├── 📁 data/                              # Dữ liệu thô 
│   ├── 📊 gold_silver_completely_real_data_20250708_144017.csv  # Dữ liệu CSV
│   └── 📊 gold_silver_completely_real_data_20250708_144017.xlsx # Dữ liệu Excel    
├── 📁 report/                            # Báo cáo đã tạo 
│   └── 📄 Bao_Cao_Gia_Vang_Bac_20250708.pdf  # Báo cáo mẫu
├── 📁 temp_charts/                       # Biểu đồ tạm (trống)
└── 📖 README.md                          # Tài liệu này
```

## 💻 Yêu Cầu Hệ Thống

### Python Version
- **Python 3.7+** (Khuyến nghị Python 3.8+)

### Dependencies Chính
```python
pandas>=1.3.0          # Xử lý dữ liệu
requests>=2.25.0       # HTTP requests
beautifulsoup4>=4.9.0  # Web scraping
matplotlib>=3.3.0      # Tạo biểu đồ
seaborn>=0.11.0        # Visualization nâng cao
reportlab>=3.5.0       # Tạo PDF
sqlite3                # Database (built-in)
schedule>=1.1.0        # Task scheduling
tvDatafeed>=2.0.0      # TradingView data
numpy>=1.20.0          # Tính toán số học
scipy>=1.7.0           # Phân tích thống kê
```


## 🚀 Hướng Dẫn Cài Đặt

### 1. Clone Repository
```bash
git clone <repository-url>
cd Silver_Price_Monitoring
```

### 2. Tạo Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Tạo File requirements.txt (nếu chưa có)
```bash
pip freeze > requirements.txt
```

### 5. Kiểm Tra Cài Đặt
```bash
python code/giabac.py --help
```

## 📖 Hướng Dẫn Sử Dụng

### 🔄 Thu Thập Dữ Liệu Cơ Bản

#### Chạy Thu Thập Dữ Liệu Một Lần
```bash
cd code
python final_gold_silver_table_with_real_data.py
```


### 📊 Tạo Báo Cáo PDF

#### Tạo Báo Cáo Với Dữ Liệu Mới Nhất
```bash
python pdf_report_generator.py
```

#### Tạo Báo Cáo Với Khoảng Thời Gian Tùy Chỉnh
```python
from pdf_report_generator import GoldSilverReportGenerator

# Tạo generator
generator = GoldSilverReportGenerator()

# Thu thập dữ liệu 90 ngày
generator.collect_latest_data(days=90)

# Tạo báo cáo
generator.create_pdf_report("bao_cao_vang_bac_90_ngay.pdf")
```


## 🌐 API và Nguồn Dữ Liệu

### 📊 TradingView (Giá Bạc Quốc Tế)
- **Symbol**: XAGUSD
- **Exchange**: OANDA
- **Interval**: Daily
- **Library**: tvDatafeed

```python
from tvDatafeed import TvDatafeed, Interval

tv = TvDatafeed()
data = tv.get_hist(symbol="XAGUSD", exchange="OANDA", interval=Interval.in_daily, n_bars=365)
```

### 🏅 Phu Quy Group (Giá Vàng SJC)
- **URL**: https://phuquygroup.vn/Gold/GoldPriceLast
- **Method**: Web Scraping
- **Format**: VND/lượng

### 🥈 Giabac.vn (Giá Bạc VN)
- **URL**: https://giabac.vn/SilverInfo/GetGoldPriceChartData
- **Method**: API JSON
- **Format**: VND/lượng

### 🔄 Backup APIs
- **Metals.live**: API backup cho giá bạc quốc tế
- **Fallback data**: Giá ước tính khi API chính down

## 🛠️ Troubleshooting

### ❌ Lỗi Thường Gặp

#### 1. Import Error: tvDatafeed
```bash
# Cài đặt tvDatafeed
pip install tvdatafeed

# Hoặc từ GitHub
pip install git+https://github.com/StreamAlpha/tvdatafeed.git
```

### 📄 PDF Report Sample
- **Trang 1**: Tóm tắt Executive
- **Trang 2-3**: Time Series Charts
- **Trang 4**: Technical Analysis
- **Trang 5**: Statistical Insights
- **Trang 6**: Raw Data Table

---
