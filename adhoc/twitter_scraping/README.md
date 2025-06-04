# Twitter Scraping Project

## Mô tả
Dự án này thực hiện việc crawl dữ liệu từ Twitter sử dụng Puppeteer.

## Cấu trúc thư mục
- `raw_data/`: Chứa dữ liệu thô được crawl từ Twitter
- `code/`: Chứa mã nguồn của dự án

## Link Google Sheet
[Link tới Google Sheet](https://drive.google.com/drive/folders/1lTj5NRiKa85twenF8PvpqeBSLjV_TRHq)

## Hướng dẫn sử dụng
1. Cài đặt dependencies:
```bash
npm install
```

2. Chạy script:
```bash
node code/twitter_crawler_puppeteer_continue.js
```

## Lưu ý
- Cần có tài khoản Twitter để sử dụng
- Đảm bảo có kết nối internet ổn định
- Dữ liệu được lưu vào file JSON trong thư mục raw_data 