# adhoc_TwitterScraping

## Mục đích

Script này dùng để tự động cào (scrape) tất cả các tweet trong 90 ngày gần nhất của 10 tài khoản X (Twitter) bằng cách sử dụng Puppeteer Core kết hợp với Bright Data Browser API.

## Cấu trúc thư mục

```
adhoc_TwitterScraping/
├── code/
│   └── twitter_crawler_puppeteer_continue.js
└── README.md
```

## Hướng dẫn sử dụng

### 1. Cài đặt thư viện cần thiết

Chạy lệnh sau trong thư mục `code/`:
```bash
npm install puppeteer-core fs
```

### 2. Cấu hình Bright Data

- Đảm bảo bạn đã có tài khoản Bright Data, đã tạo zone loại **Browser API** và còn credit.
- Lấy thông tin endpoint WebSocket, username, password từ Bright Data dashboard và thay vào biến `browserWSEndpoint` trong file code nếu cần.

### 3. Chạy script

```bash
node twitter_crawler_puppeteer_continue.js
```

### 4. Kết quả

- Mỗi tài khoản sẽ có một file CSV chứa toàn bộ tweet trong 90 ngày gần nhất, lưu cùng thư mục với file code.

## Lưu ý

- Script chỉ push file code, không push bất kỳ dữ liệu nào lên repo.
- Nếu gặp lỗi 403 khi chạy, kiểm tra lại số dư tài khoản Bright Data và cấu hình zone.
- Nếu muốn thay đổi danh sách tài khoản hoặc số ngày, chỉnh sửa trực tiếp trong file code.

---

**Tác giả:** [mnhtan](https://github.com/mnhtan)  
**Repo:** [campaign-management](https://github.com/mnhtan/campaign-management) 