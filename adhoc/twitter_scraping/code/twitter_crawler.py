import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta

# Đọc danh sách account
accounts = pd.read_csv('Twitter Scraping - Twitter_Account.csv')
account_info = {
    row['x_username'].replace('@', ''): (row['name'], row['x_username'])
    for _, row in accounts.iterrows()
}
usernames = list(account_info.keys())

chrome_options = Options()
chrome_options.add_argument(r"--user-data-dir=C:\Users\ppmta\AppData\Local\Google\Chrome\User Data\Default")
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://twitter.com/login")
print("Vui lòng đăng nhập Twitter trên trình duyệt vừa mở. Chờ 90 giây để đăng nhập...")
time.sleep(30)# Chờ 90 giây cho bạn đăng nhập thủ công

results = []
since = (datetime.utcnow() - timedelta(days=90)).strftime('%Y-%m-%d')

for username in usernames:
    search_url = f"https://twitter.com/search?q=from%3A{username}%20since%3A{since}&src=typed_query&f=live"
    print(f"Đang lấy tweet của {username} ...")
    driver.get(search_url)
    time.sleep(5)

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    max_scroll = 1000  # Giới hạn số lần scroll để tránh loop vô hạn (có thể tăng nếu muốn lấy nhiều hơn)
    while True:
        # Lấy tweet hiện tại
        tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid=\"tweet\"]')
        for tweet in tweets:
            try:
                content = tweet.text.replace('\n', ' ')
                results.append({
                    "Twitter Account": account_info[username][0],
                    "Twitter Handle": account_info[username][1],
                    "Content": content
                })
            except Exception:
                continue
        # Scroll xuống cuối trang
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count += 1
        # Nếu không còn tweet mới hoặc đã scroll quá nhiều lần thì dừng
        if new_height == last_height or scroll_count >= max_scroll:
            break
        last_height = new_height
    time.sleep(2)

driver.quit()

df = pd.DataFrame(results).drop_duplicates()
df.to_csv('twitter_results.csv', index=False)
print("Đã lưu kết quả vào twitter_results.csv")