from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib.parse import urlparse
import re
from datetime import datetime
import argparse

class CryptoRankCrawler:
    def __init__(self, max_workers=10, test_mode=False):  # TĂNG LUỒNG LÊN 10
        self.max_workers = max_workers
        # Điều chỉnh delay dựa trên số luồng
        if max_workers >= 10:
            self.delay = 1  # Delay thấp cho nhiều luồng
        elif max_workers >= 5:
            self.delay = 1.5
        else:
            self.delay = 2
        self.results = []
        self.lock = threading.Lock()
        self.test_mode = test_mode  # Chế độ test
        
    def setup_driver(self):
        """Khởi tạo Chrome driver với incognito mode"""
        options = webdriver.ChromeOptions()
        
        # Cấu hình incognito mode
        options.add_argument("--incognito")
        print("🕵️ Chạy ở chế độ incognito (riêng tư)")
        
        # Cấu hình anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-web-security")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # User agent mới để tránh phát hiện
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Thêm các tùy chọn để tối ưu performance và tránh phát hiện
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Tắt load ảnh để tăng tốc
        options.add_argument("--disable-javascript")  # Tắt một số JS không cần thiết
        options.add_argument("--disable-gpu")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Tắt thông báo và popup
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        
        # Cấu hình để tránh memory leaks
        options.add_argument("--max_old_space_size=4096")
        
        # Tối ưu cho nhiều luồng
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--no-crash-upload")
        options.add_argument("--disable-gpu-sandbox")
        options.add_argument("--use-gl=swiftshader")
        options.add_argument("--enable-webgl")
        options.add_argument("--disable-software-rasterizer")
        
        # Tối ưu cho headless (có thể bật nếu cần)
        # options.add_argument("--headless")
        
        # Tắt logging để giảm noise
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # Cấu hình prefs để tắt ảnh và media
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.media_stream": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.media_stream": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        
        # Script để ẩn dấu hiệu automation
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array")
        driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise")
        driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol")
        
        return driver
    
    def extract_real_website(self, driver, project_url):
        """Lấy website thật của project từ trang chi tiết - CẢI TIẾN XỬ LÝ DUPLICATE"""
        try:
            driver.get(project_url)
            time.sleep(3)
            
            # Đợi trang load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Tìm website thật - ưu tiên các selector chính xác cho cả 2 giao diện
            website_selectors = [
                # Selector cho funding-rounds (mới) - class styles_coin_social_link_item__SAH_3
                "//a[contains(@class, 'styles_coin_social_link_item__SAH_3') and .//span[text()='Website']]",
                
                # Selector cho drophunting (cũ) - class styles_coin_social_link_item
                "//a[contains(@class, 'styles_coin_social_link_item') and .//span[text()='Website']]",
                
                # Backup selectors chung
                "//a[contains(@class, 'coin_social_link_item') and .//span[text()='Website']]",
                "//a[.//span[text()='Website']]",
                
                # Selector tổng quát cho social section
                "//div[contains(@class, 'social')]//a[contains(@href, 'http') and not(contains(@href, 'twitter')) and not(contains(@href, 'telegram')) and not(contains(@href, 'discord')) and not(contains(@href, 'cryptorank')) and not(contains(@href, 'hafix')) and not(contains(@href, 'bcgame'))]",
                
                # Tìm link có domain thật (không phải ads) - fallback cuối cùng
                "//a[contains(@href, 'http') and not(contains(@href, 'twitter')) and not(contains(@href, 'telegram')) and not(contains(@href, 'discord')) and not(contains(@href, 'cryptorank')) and not(contains(@href, 'hafix')) and not(contains(@href, 'bcgame')) and not(contains(@href, 'facebook'))]"
            ]
            
            for i, selector in enumerate(website_selectors, 1):
                try:
                    print(f"      🔍 Thử website selector {i}: {selector[:50]}...")
                    elements = driver.find_elements(By.XPATH, selector)
                    print(f"      📊 Tìm thấy {len(elements)} elements")
                    
                    # KIỂM TRA TẤT CẢ ELEMENTS, KHÔNG CHỈ ELEMENT ĐẦU TIÊN
                    valid_websites = []
                    
                    for j, elem in enumerate(elements, 1):
                        try:
                            href = elem.get_attribute('href')
                            is_displayed = elem.is_displayed()
                            
                            print(f"        Element {j}: href='{href}', displayed={is_displayed}")
                            
                            if href and self.is_valid_website(href):
                                valid_websites.append(href)
                                print(f"        ✅ Website hợp lệ: {href}")
                            elif href:
                                print(f"        ❌ Website không hợp lệ: {href}")
                            else:
                                print(f"        ⚠️ Element không có href")
                                
                        except Exception as e:
                            print(f"        ❌ Lỗi đọc element {j}: {e}")
                    
                    # Nếu tìm thấy website hợp lệ, trả về cái đầu tiên
                    if valid_websites:
                        best_website = valid_websites[0]
                        print(f"      ✅ Chọn website tốt nhất: {best_website}")
                        return best_website
                            
                except Exception as e:
                    print(f"      ❌ Website selector {i} failed: {e}")
                    continue
            
            print(f"      ⚠️ Không tìm thấy website hợp lệ")
            return ""
            
        except Exception as e:
            print(f"      ❌ Lỗi extract website: {e}")
            return ""
    
    def is_valid_website(self, url):
        """Kiểm tra URL có phải website hợp lệ không - CẢI TIẾN NÂNG CAO"""
        if not url or not url.startswith('http'):
            return False
        
        url_lower = url.lower().strip()
        
        # Loại bỏ URL trống hoặc chỉ có http://
        if url_lower in ['http://', 'https://']:
            return False
        
        # Danh sách domain cần loại bỏ (ads, social media, spam)
        invalid_domains = [
            'twitter.com', 'x.com', 't.me', 'telegram.org',
            'discord.gg', 'discord.com', 'github.com', 'medium.com',
            'facebook.com', 'instagram.com', 'linkedin.com',
            'cryptorank.io', 'coinmarketcap.com', 'coingecko.com',
            'hafix.care', 'bcgame.sk', 'bs_', 'ads.', 'ad.',
            'affiliate.', 'ref.', 'promo.', 'bonus.',
            'youtube.com', 'youtu.be', 'reddit.com',
            # THÊM CÁC DOMAIN SAI KHÁC
            'notion.site', 'google.com', 'typeform.com', 'keplr.app',
            'forms.gle', 'docs.google.com', 'drive.google.com'
        ]
        
        # Kiểm tra domain không hợp lệ
        for domain in invalid_domains:
            if domain in url_lower:
                print(f"        ❌ Domain không hợp lệ: {domain}")
                return False
        
        # Kiểm tra pattern spam và referral - CẢI TIẾN
        spam_patterns = [
            'i-6pv69kz2-n', 'bs_7d21491b', 'hafix', 'bcgame',
            'affiliate', 'referral', 'promo', 'bonus',
            # THÊM CÁC PATTERN SAI KHÁC
            'capable-philosophy-a3e.notion.site',
            '/refer/', '/r/', 'refcode=', '?rc=', 'signup.',
            'campaign', 'dashboard', 'collection', 'browse/',
            'explorer', 'careers-at-cryptorank', '/careers',
            '/jobs', '/hiring', '/apply', '/register'
        ]
        
        for pattern in spam_patterns:
            if pattern in url_lower:
                print(f"        ❌ Pattern spam: {pattern}")
                return False
        
        # Kiểm tra URL có domain hợp lệ (có dấu chấm)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Domain phải có ít nhất 1 dấu chấm
            if '.' not in domain:
                print(f"        ❌ Domain không hợp lệ: {domain}")
                return False
                
            # Domain không được quá ngắn
            if len(domain) < 4:
                print(f"        ❌ Domain quá ngắn: {domain}")
                return False
                
        except Exception as e:
            print(f"        ❌ Lỗi parse URL: {e}")
            return False
        
        print(f"        ✅ URL hợp lệ")
        return True
    
    def clean_project_name(self, project_text):
        """Làm sạch tên project - chỉ lấy tên chính, loại bỏ phần trùng lặp"""
        if not project_text:
            return ""
        
        # Tách theo dòng mới
        lines = [line.strip() for line in project_text.split('\n') if line.strip()]
        
        if len(lines) == 1:
            return lines[0]
        elif len(lines) == 2:
            line1, line2 = lines[0], lines[1]
            
            # Nếu dòng 2 là viết tắt của dòng 1 hoặc quá ngắn, chọn dòng 1
            if line2.upper() in line1.upper() or len(line2) <= 4:
                return line1
            # Nếu dòng 1 chứa dòng 2, chọn dòng 1
            elif line2 in line1:
                return line1
            # Nếu dòng 2 bắt đầu bằng $ (token), chọn dòng 1
            elif line2.startswith('$'):
                return line1
            # Nếu dòng 2 là viết hoa toàn bộ và ngắn, có thể là ticker
            elif line2.isupper() and len(line2) <= 6:
                return line1
            # Mặc định chọn dòng 1 (tên đầy đủ)
            else:
                return line1
        else:
            # Nếu có nhiều dòng, chọn dòng đầu tiên
            return lines[0]
    
    def clean_fund_raising(self, fund_text):
        """Làm sạch fund raising - loại bỏ phần +số"""
        if not fund_text:
            return ""
        
        # Tách theo dòng mới
        lines = [line.strip() for line in fund_text.split('\n') if line.strip()]
        
        if len(lines) == 1:
            return lines[0]
        elif len(lines) >= 2:
            # Dòng đầu thường là số tiền, dòng sau là +số
            line1 = lines[0]
            line2 = lines[1] if len(lines) > 1 else ""
            
            # Nếu dòng 2 bắt đầu bằng +, bỏ qua
            if line2.startswith('+'):
                return line1
            # Nếu dòng 2 chỉ là số, bỏ qua
            elif line2.isdigit():
                return line1
            # Mặc định chọn dòng 1
            else:
                return line1
        
        return fund_text
    
    def extract_twitter(self, driver):
        """Lấy Twitter thật của project"""
        twitter_selectors = [
            # Selector cho funding-rounds (mới) - class styles_coin_social_link_item__SAH_3
            "//a[contains(@class, 'styles_coin_social_link_item__SAH_3') and .//span[text()='X']]",
            "//a[contains(@class, 'styles_coin_social_link_item__SAH_3') and .//span[text()='Twitter']]",
            
            # Selector cho drophunting (cũ) - class styles_coin_social_link_item
            "//a[contains(@class, 'styles_coin_social_link_item') and .//span[text()='Twitter']]",
            "//a[contains(@class, 'styles_coin_social_link_item') and .//span[text()='X']]",
            
            # Backup selectors chung
            "//a[contains(@class, 'coin_social_link_item') and .//span[text()='Twitter']]",
            "//a[contains(@class, 'coin_social_link_item') and .//span[text()='X']]",
            
            # Backup: tìm link Twitter/X trong social section
            "//div[contains(@class, 'social')]//a[contains(@href, 'twitter.com') or contains(@href, 'x.com')]",
            
            # Tìm bất kỳ link Twitter nào (nhưng không phải CryptoRank)
            "//a[(contains(@href, 'twitter.com') or contains(@href, 'x.com')) and not(contains(@href, 'CryptoRank'))]"
        ]
        
        for i, selector in enumerate(twitter_selectors, 1):
            try:
                print(f"      🔍 Thử Twitter selector {i}: {selector[:50]}...")
                elements = driver.find_elements(By.XPATH, selector)
                
                for elem in elements:
                    href = elem.get_attribute('href')
                    if href and self.is_valid_twitter(href):
                        print(f"      ✅ Tìm thấy Twitter: {href}")
                        return href
                        
            except Exception as e:
                print(f"      ❌ Twitter selector {i} failed: {e}")
                continue
        
        print(f"      ⚠️ Không tìm thấy Twitter hợp lệ")
        return ""
    
    def is_valid_twitter(self, url):
        """Kiểm tra Twitter URL có hợp lệ không"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Phải là Twitter/X link
        if not ('twitter.com' in url_lower or 'x.com' in url_lower):
            return False
        
        # Loại bỏ Twitter của CryptoRank và các account không liên quan
        invalid_twitter_accounts = [
            'cryptorank_io', 'cryptorank.io', 'cryptorank',
            'coinmarketcap', 'coingecko', 'binance', 'coinbase'
        ]
        
        for account in invalid_twitter_accounts:
            if account in url_lower:
                return False
        
        return True
    
    def process_project_details(self, project_info):
        """Xử lý chi tiết 1 project với driver riêng"""
        driver = self.setup_driver()
        
        try:
            project_name_raw = project_info.get('Project', 'Unknown')
            project_name = self.clean_project_name(project_name_raw)  # LÀM SẠCH TÊN
            project_url = project_info.get('project_url', '')
            fund_raising_raw = project_info.get('Fund_raising', '')
            fund_raising = self.clean_fund_raising(fund_raising_raw)  # LÀM SẠCH FUND
            
            print(f"🔍 Thread {threading.get_ident()}: Đang xử lý {project_name}")
            print(f"    🌐 Đang truy cập: {project_url}")
            
            if not project_url:
                print(f"    ❌ Không có URL để crawl")
                return None
            
            # Lấy website thật
            website = self.extract_real_website(driver, project_url)
            
            # Lấy Twitter thật (từ cùng trang)
            twitter = self.extract_twitter(driver)
            
            # Tạo kết quả
            result = {
                'Category': project_info.get('Category', ''),
                'Project': project_name,
                'Fund_raising': fund_raising,
                'Website': website,
                'Twitter': twitter
            }
            
            print(f"    ✅ Thread {threading.get_ident()}: Hoàn thành {project_name}")
            print(f"       📊 Website: {website[:50] if website else 'Không có'}")
            print(f"       🐦 Twitter: {twitter[:50] if twitter else 'Không có'}")
            
            return result
            
        except Exception as e:
            print(f"    ❌ Thread {threading.get_ident()}: Lỗi xử lý {project_info.get('Project', 'Unknown')}: {e}")
            return None
        finally:
            try:
                driver.quit()
            except:
                pass
            print(f"    ⏳ Nghỉ {self.delay} giây...")
            time.sleep(self.delay)
    
    def crawl_page_projects(self, driver, source_url):
        """Lấy danh sách projects từ 1 trang"""
        projects = []
        
        try:
            # Đợi bảng load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//table//tbody//tr"))
            )
            
            rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
            print(f"  📋 Tìm thấy {len(rows)} rows")
            
            for row in rows:
                try:
                    if 'drophunting' in source_url:
                        # Cấu trúc drophunting
                        name_elem = row.find_element(By.XPATH, ".//td[2]//a")
                        project_name_raw = name_elem.text.strip()
                        project_name = self.clean_project_name(project_name_raw)  # LÀM SẠCH TÊN
                        project_url = name_elem.get_attribute('href')
                        
                        # Fund raising (cột 6)
                        try:
                            fund_elem = row.find_element(By.XPATH, ".//td[6]")
                            fund_raising_raw = fund_elem.text.strip()
                            fund_raising = self.clean_fund_raising(fund_raising_raw)  # LÀM SẠCH FUND
                        except:
                            fund_raising = ""
                    
                    else:  # funding-rounds
                        # Cấu trúc funding-rounds dựa trên HTML thực tế - CẢI TIẾN
                        try:
                            # NHIỀU CÁCH TÌM PROJECT NAME VÀ URL
                            project_url = ""
                            project_name_raw = ""
                            
                            # Cách 1: Tìm từ cột 1 với /ico/
                            try:
                                name_elem = row.find_element(By.XPATH, ".//td[1]//a[contains(@href, '/ico/')]")
                                project_url = name_elem.get_attribute('href')
                                
                                # Thử nhiều cách lấy tên
                                selectors_to_try = [
                                    ".//span[contains(@class, 'getORt')]",
                                    ".//span[contains(@class, 'name')]", 
                                    ".//span[@class]",
                                    ".//div[contains(@class, 'name')]",
                                    ".//p[contains(@class, 'name')]"
                                ]
                                
                                for selector in selectors_to_try:
                                    try:
                                        elem = name_elem.find_element(By.XPATH, selector)
                                        text = elem.text.strip()
                                        if text and len(text) > 1:
                                            project_name_raw = text
                                            print(f"      📝 Lấy name từ {selector}: '{project_name_raw}'")
                                            break
                                    except:
                                        continue
                                
                                # Nếu vẫn không có, lấy từ title/text/alt
                                if not project_name_raw:
                                    project_name_raw = (name_elem.get_attribute('title') or 
                                                       name_elem.text.strip())
                                    if project_name_raw:
                                        print(f"      📝 Lấy name từ title/text: '{project_name_raw}'")
                                
                                # Lấy từ img alt
                                if not project_name_raw:
                                    try:
                                        img_elem = name_elem.find_element(By.XPATH, ".//img")
                                        alt_text = img_elem.get_attribute('alt')
                                        if alt_text:
                                            project_name_raw = alt_text.replace(' icon', '').replace(' logo', '').strip()
                                            print(f"      📝 Lấy name từ img alt: '{project_name_raw}'")
                                    except:
                                        pass
                                        
                            except:
                                # Cách 2: Tìm bất kỳ link /ico/ nào trong row
                                try:
                                    all_ico_links = row.find_elements(By.XPATH, ".//a[contains(@href, '/ico/')]")
                                    if all_ico_links:
                                        name_elem = all_ico_links[0]
                                        project_url = name_elem.get_attribute('href')
                                        project_name_raw = name_elem.text.strip()
                                        print(f"      🔄 Backup method 1: '{project_name_raw}'")
                                except:
                                    pass
                            
                            # Cách 3: Tìm từ bất kỳ link nào có text
                            if not project_name_raw or not project_url:
                                try:
                                    all_links = row.find_elements(By.XPATH, ".//a[@href]")
                                    for link in all_links:
                                        href = link.get_attribute('href')
                                        text = link.text.strip()
                                        if href and '/ico/' in href and text and len(text) > 1:
                                            project_url = href
                                            project_name_raw = text
                                            print(f"      🔄 Backup method 2: '{project_name_raw}'")
                                            break
                                except:
                                    pass
                            
                            # Cuối cùng, lấy từ URL nếu vẫn không có tên
                            if not project_name_raw and project_url:
                                try:
                                    # Lấy từ URL: /ico/project-name -> project-name
                                    url_parts = project_url.split('/ico/')
                                    if len(url_parts) > 1:
                                        project_name_raw = url_parts[1].split('#')[0].split('?')[0]
                                        project_name_raw = project_name_raw.replace('-', ' ').replace('_', ' ').title()
                                        print(f"      📝 Lấy name từ URL: '{project_name_raw}'")
                                except:
                                    pass
                            
                            # LÀM SẠCH TÊN PROJECT
                            project_name = self.clean_project_name(project_name_raw) if project_name_raw else ""
                                    
                        except Exception as e:
                            print(f"      ❌ Không tìm được project name/URL: {e}")
                            # Thử cách khác - tìm bất kỳ link nào có /ico/
                            try:
                                all_links = row.find_elements(By.XPATH, ".//a[contains(@href, '/ico/')]")
                                if all_links:
                                    name_elem = all_links[0]
                                    project_url = name_elem.get_attribute('href')
                                    project_name = name_elem.text.strip() or "Unknown Project"
                                    print(f"      🔄 Backup method: '{project_name}' | {project_url}")
                                else:
                                    continue
                            except:
                                continue
                        
                        # Fund raising từ cột 2 (theo HTML thực tế)
                        fund_raising = ""
                        try:
                            # Tìm fund raising trong cột 2
                            fund_elem = row.find_element(By.XPATH, ".//td[2]//p[contains(@class, 'jgeqml')]")
                            fund_raising_raw = fund_elem.text.strip()
                            fund_raising = self.clean_fund_raising(fund_raising_raw)  # LÀM SẠCH FUND
                        except:
                            try:
                                # Backup: tìm bất kỳ element nào có $ và M
                                all_tds = row.find_elements(By.XPATH, ".//td")
                                for td in all_tds:
                                    td_text = td.text.strip()
                                    if '$' in td_text and ('M' in td_text or 'K' in td_text):
                                        fund_raising = self.clean_fund_raising(td_text)  # LÀM SẠCH FUND
                                        break
                            except:
                                fund_raising = ""
                        
                        # Đảm bảo URL đầy đủ
                        if project_url and not project_url.startswith('http'):
                            project_url = 'https://cryptorank.io' + project_url
                    
                    if project_name and project_url:
                        projects.append({
                            'Project': project_name,
                            'project_url': project_url,
                            'Category': source_url,  # URL nguồn làm category
                            'Fund_raising': fund_raising
                        })
                        print(f"    ✓ {project_name} | {fund_raising} | {project_url}")
                    else:
                        print(f"    ⚠️ Skip row: name='{project_name}' url='{project_url}'")
                
                except Exception as e:
                    print(f"    ❌ Lỗi crawl row: {e}")
                    continue
            
        except Exception as e:
            print(f"  ❌ Lỗi khi crawl trang: {e}")
        
        return projects
    
    def crawl_all_pages(self, source_url, max_pages):
        """Crawl tất cả các trang từ 1 nguồn"""
        driver = self.setup_driver()
        all_projects = []
        
        try:
            print(f"\n🎯 Bắt đầu crawl: {source_url}")
            driver.get(source_url)
            time.sleep(5)  # Tăng thời gian chờ
            
            print("⏳ Chờ bạn setup filter thủ công...")
            input("👆 Nhấn ENTER khi đã setup filter xong...")
            
            page = 1
            while page <= max_pages:
                print(f"\n📄 Đang crawl trang {page}/{max_pages}")
                
                # Crawl projects từ trang hiện tại
                projects = self.crawl_page_projects(driver, source_url)
                all_projects.extend(projects)
                
                print(f"  ✅ Lấy được {len(projects)} projects từ trang {page}")
                
                if len(projects) == 0:
                    print("  ⚠️ Không có projects nào, có thể đã hết trang")
                    break
                
                # Kiểm tra test mode
                if self.test_mode and len(all_projects) >= 20:
                    print(f"  🧪 TEST MODE: Đã đủ 20 projects, dừng crawl")
                    all_projects = all_projects[:20]  # Lấy đúng 20 projects đầu
                    break
                
                # Chuyển trang tiếp theo
                try:
                    if 'drophunting' in source_url:
                        next_btn = driver.find_element(By.XPATH, "//button[contains(@class,'styles_right__svmkV') and not(@disabled)]")
                    else:  # funding-rounds
                        # Thử nhiều selector cho nút Next
                        next_selectors = [
                            "//button[@aria-label='Next page' and not(@disabled)]",
                            "//button[contains(@class, 'next') and not(@disabled)]",
                            "//button[contains(text(), 'Next') and not(@disabled)]",
                            "//button[contains(@class, 'pagination') and not(@disabled)]//following-sibling::button[1]"
                        ]
                        next_btn = None
                        for selector in next_selectors:
                            try:
                                next_btn = driver.find_element(By.XPATH, selector)
                                break
                            except:
                                continue
                    
                    if next_btn:
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(5)  # Tăng thời gian chờ
                        page += 1
                    else:
                        print("  ✅ Đã crawl hết tất cả trang")
                        break
                except Exception as e:
                    print(f"  ✅ Đã crawl hết tất cả trang (lỗi: {e})")
                    break
        
        except Exception as e:
            print(f"❌ Lỗi khi crawl {source_url}: {e}")
        
        finally:
            driver.quit()
        
        return all_projects
    
    def save_results(self):
        """Lưu kết quả ra file CSV với tên file unique"""
        if not self.results:
            print("❌ Không có dữ liệu để lưu!")
            return
            
        # Tạo DataFrame và sắp xếp theo category
        df = pd.DataFrame(self.results)
        
        # Đổi tên cột cho đúng format yêu cầu
        column_mapping = {
            'Category': 'Category',
            'Project': 'Project', 
            'Fund_raising': 'Fund raising',  # Space thay vì underscore
            'Website': 'Website',
            'Twitter': 'Twitter'
        }
        
        # Đảm bảo có đủ cột
        for old_col, new_col in column_mapping.items():
            if old_col not in df.columns:
                df[old_col] = ''
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Sắp xếp cột theo thứ tự yêu cầu
        df = df[['Category', 'Project', 'Fund raising', 'Website', 'Twitter']]
        
        # Làm sạch dữ liệu
        df = df.drop_duplicates(subset=['Project'])
        df = df.fillna('')
        df = df.sort_values(['Category', 'Project'])
        
        print(f"\n📊 Tổng kết dữ liệu:")
        print(f"   - Tổng cộng: {len(df)} projects")
        
        # Đếm theo category - dùng URL thay vì text
        drophunting_count = len(df[df['Category'].str.contains('drophunting', na=False)])
        funding_rounds_count = len(df[df['Category'].str.contains('funding-rounds', na=False)])
        
        print(f"   - Drophunting: {drophunting_count} projects")
        print(f"   - Funding-rounds: {funding_rounds_count} projects")
        
        if funding_rounds_count == 0:
            print("⚠️  WARNING: Không có dữ liệu funding-rounds!")
        
        # Tạo tên file với timestamp để tránh lỗi permission
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "_test" if self.test_mode else "_full"
        output_file = f'cryptorank_projects{mode_suffix}_{timestamp}.csv'
        
        try:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ Đã lưu file: {output_file}")
            
            # Hiển thị sample dữ liệu
            if not df.empty:
                print(f"\n📋 Sample dữ liệu (5 records đầu):")
                for idx, row in df.head().iterrows():
                    print(f"   {idx+1}. [{row['Category']}] {row['Project']} - {row['Fund raising']}")
                    
        except Exception as e:
            print(f"❌ Lỗi khi lưu file: {e}")
            print("🔄 Thử lưu với tên file khác...")
            backup_file = f'cryptorank_backup_{timestamp}.csv'
            try:
                df.to_csv(backup_file, index=False, encoding='utf-8-sig')
                print(f"✅ Đã lưu file backup: {backup_file}")
            except Exception as backup_error:
                print(f"❌ Lỗi backup: {backup_error}")

def main():
    print("🚀 CryptoRank Crawler - Version 2.1")
    print("=" * 50)
    
    # Thiết lập
    parser = argparse.ArgumentParser(description='Crawl CryptoRank projects')
    parser.add_argument('--test', action='store_true', help='Chạy test mode (20 projects)')
    parser.add_argument('--incognito', action='store_true', help='Chạy ở chế độ ẩn danh')
    parser.add_argument('--workers', type=int, default=10, help='Số luồng crawl (mặc định: 10)')
    args = parser.parse_args()
    
    # Khởi tạo crawler với số luồng tùy chọn
    crawler = CryptoRankCrawler(max_workers=args.workers, test_mode=args.test)
    
    print(f"🧪 Chế độ: {'TEST (20 projects)' if args.test else 'FULL (~1000+ projects)'}")
    print(f"🕶️  Incognito: {'BẬT' if args.incognito else 'TẮT'}")
    print(f"⚡ Số luồng: {args.workers} luồng song song")
    
    # Thiết lập sources để crawl
    sources = [
        {
            'url': 'https://cryptorank.io/drophunting',
            'name': 'Drophunting',
            'max_pages': 3 if args.test else 30  # Test: 3 trang, Full: 30 trang
        },
        {
            'url': 'https://cryptorank.io/funding-rounds',
            'name': 'Funding Rounds', 
            'max_pages': 3 if args.test else 25  # Test: 3 trang, Full: 25 trang
        }
    ]
    
    print(f"\n📋 Kế hoạch crawl:")
    for i, source in enumerate(sources, 1):
        print(f"   {i}. {source['name']}: {source['max_pages']} trang đầu")
    
    # Bắt đầu crawl
    print(f"\n🎯 BẮT ĐẦU CRAWL...")
    
    all_basic_projects = []  # Lưu thông tin cơ bản trước
    
    for i, source in enumerate(sources, 1):
        print(f"\n{'='*20} CRAWL {source['name'].upper()} {'='*20}")
        
        # Crawl từng source
        projects = crawler.crawl_all_pages(source['url'], source['max_pages'])
        print(f"✅ Hoàn thành {source['name']}: {len(projects)} projects")
        
        # Thêm vào danh sách cơ bản
        for project in projects:
            project['Category'] = source['url']  # Set category là URL nguồn  
        all_basic_projects.extend(projects)
        
        # Debug info
        print(f"📊 Tổng projects hiện tại: {len(all_basic_projects)}")
        
        # Delay giữa các source
        if i < len(sources):
            print(f"⏳ Nghỉ 10 giây trước khi crawl source tiếp theo...")
            time.sleep(10)
    
    print(f"\n{'='*50}")
    print(f"🎉 HOÀN THÀNH CRAWL DANH SÁCH!")
    print(f"📊 Tổng cộng: {len(all_basic_projects)} projects")
    
    # Debug theo category
    drophunting_projects = [p for p in all_basic_projects if 'drophunting' in p.get('Category', '')]
    funding_projects = [p for p in all_basic_projects if 'funding-rounds' in p.get('Category', '')]
    
    print(f"   - Drophunting: {len(drophunting_projects)} projects")
    print(f"   - Funding-rounds: {len(funding_projects)} projects")
    
    if len(funding_projects) == 0:
        print("⚠️  WARNING: Không có dữ liệu từ funding-rounds!")
        print("💡 Có thể do:")
        print("   - Website thay đổi cấu trúc")
        print("   - Cần setup filter khác")
        print("   - Cloudflare block")
    
    # Bước 2: Crawl chi tiết Website & Twitter với MULTI-THREADING
    if all_basic_projects:
        print(f"\n🔧 Bắt đầu crawl chi tiết Website & Twitter...")
        print(f"📊 Cần crawl chi tiết cho {len(all_basic_projects)} projects")
        print(f"⚡ Sử dụng {crawler.max_workers} luồng song song")
        
        # SỬ DỤNG THREADPOOLEXECUTOR ĐỂ CRAWL SONG SONG
        with ThreadPoolExecutor(max_workers=crawler.max_workers) as executor:
            # Submit tất cả tasks
            future_to_project = {
                executor.submit(crawler.process_project_details, project): project 
                for project in all_basic_projects
            }
            
            completed = 0
            total = len(all_basic_projects)
            
            # Xử lý kết quả khi hoàn thành
            for future in as_completed(future_to_project):
                completed += 1
                project = future_to_project[future]
                
                print(f"\n📈 Progress: {completed}/{total} ({completed/total*100:.1f}%)")
                
                try:
                    result = future.result()
                    if result:
                        with crawler.lock:
                            crawler.results.append(result)
                        print(f"    ✅ Hoàn thành: {result.get('Project', 'Unknown')}")
                    else:
                        print(f"    ❌ Không có kết quả: {project.get('Project', 'Unknown')}")
                        
                except Exception as e:
                    print(f"    ❌ Lỗi xử lý {project.get('Project', 'Unknown')}: {e}")
        
        print(f"\n🎉 Hoàn thành crawl chi tiết với {crawler.max_workers} luồng!")
        print(f"📊 Kết quả: {len(crawler.results)}/{total} projects thành công ({len(crawler.results)/total*100:.1f}%)")
    
    # Lưu file cuối cùng  
    if crawler.results:
        print(f"\n💾 Đang lưu dữ liệu...")
        crawler.save_results()
    else:
        print(f"\n❌ Không có dữ liệu để lưu!")

if __name__ == "__main__":
    main()