import requests
import time
import random
from bs4 import BeautifulSoup
import json
from urllib.parse import urlencode, quote
from fake_useragent import UserAgent
import itertools
from dataclasses import dataclass
from typing import List, Dict, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import csv
from datetime import datetime, time as dt_time
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    headline: str
    link: str
    date: str
    source: str = ""

@dataclass
class CrawlStats:
    total_keywords: int = 0
    total_articles: int = 0
    captcha_skipped: int = 0
    errors: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

class GoogleNewsScraper:
    def __init__(self, proxy_list: List[str] = None):
        """
        Initialize scraper with anti-CAPTCHA measures
        
        Args:
            proxy_list: List of proxy servers in format 'ip:port' or 'username:password@ip:port'
        """
        self.ua = UserAgent()
        self.proxy_list = proxy_list or []
        self.proxy_cycle = itertools.cycle(self.proxy_list) if self.proxy_list else None
        self.session_pool = {}
        self.request_count = 0
        self.last_request_time = 0
        
        # Rate limiting settings
        self.min_delay = 2  # Minimum delay between requests
        self.max_delay = 5  # Maximum delay between requests
        self.requests_per_session = 10  # Switch session after N requests
        
    def get_rotating_session(self) -> requests.Session:
        """Get a session with rotating proxy and headers"""
        session_id = self.request_count // self.requests_per_session
        
        if session_id not in self.session_pool:
            session = requests.Session()
            
            # Set rotating proxy
            if self.proxy_cycle:
                proxy = next(self.proxy_cycle)
                if '@' in proxy:
                    # Authenticated proxy
                    auth, server = proxy.split('@')
                    username, password = auth.split(':')
                    session.auth = (username, password)
                    session.proxies = {
                        'http': f'http://{server}',
                        'https': f'https://{server}'
                    }
                else:
                    # Simple proxy
                    session.proxies = {
                        'http': f'http://{proxy}',
                        'https': f'https://{proxy}'
                    }
            
            # Set realistic headers
            session.headers.update(self._get_realistic_headers())
            
            self.session_pool[session_id] = session
            
        return self.session_pool[session_id]
    
    def _get_realistic_headers(self) -> Dict[str, str]:
        """Generate realistic browser headers"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def _smart_delay(self):
        """Implement smart delay to avoid rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # Base delay + random jitter
        delay = random.uniform(self.min_delay, self.max_delay)
        
        # Add extra delay if requests are too frequent
        if elapsed < 1:
            delay += random.uniform(2, 4)
        
        # Occasional longer pause to appear more human-like
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(10, 20)
            
        logger.info(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)
        self.last_request_time = time.time()
    
    def _crawl_via_crawlbase(self, url: str) -> str:
        """Crawl trang web sử dụng Crawlbase API với normal token"""
        try:
            # Sử dụng normal token
            normal_token = "xKfElFt5FvM613yeR4Pz8A"
            api_url = f"https://api.crawlbase.com/?token={normal_token}&url={url}"
            
            # Thêm headers cần thiết
            headers = {
                'Accept-Encoding': 'gzip',
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            logger.info(f"Calling Crawlbase API for URL: {url}")
            response = requests.get(api_url, headers=headers, timeout=90)
            
            # Log response status và headers
            logger.info(f"Crawlbase API Response Status: {response.status_code}")
            logger.info("Crawlbase Response Headers:")
            for key, value in response.headers.items():
                logger.info(f"{key}: {value}")
            
            response.raise_for_status()
            
            # Xử lý response content
            if 'gzip' in response.headers.get('Content-Encoding', '').lower():
                import gzip
                content = gzip.decompress(response.content)
                html = content.decode('utf-8')
            else:
                html = response.text
            
            # In ra 500 ký tự đầu của HTML để kiểm tra
            logger.info("First 500 characters of response:")
            logger.info(html[:500])
            
            return html
            
        except Exception as e:
            logger.error(f"Crawlbase API error: {str(e)}")
            return ""

    def search_google_news(self, keyword: str, max_results: int = 20) -> List[NewsArticle]:
        """
        Search Google News for a specific keyword
        
        Args:
            keyword: Search term
            max_results: Maximum number of results to return
            
        Returns:
            List of NewsArticle objects
        """
        articles = []
        
        try:
            # Build search URL
            params = {
                'q': keyword,
                'tbm': 'nws',  # News search
                'num': min(max_results, 100),  # Google limits to 100 per page
                'hl': 'en',
                'gl': 'us'
            }
            
            url = f"https://www.google.com/search?{urlencode(params)}"
            
            # Apply smart delay
            self._smart_delay()
            
            # Get session with rotation
            session = self.get_rotating_session()
            
            logger.info(f"Searching for: {keyword}")
            logger.info(f"Request #{self.request_count + 1}")
            
            # Make request
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            self.request_count += 1
            
            # Check for CAPTCHA
            if self._is_captcha_page(response.text):
                logger.warning("CAPTCHA detected! Switching to Crawlbase API...")
                html = self._crawl_via_crawlbase(url)
                if html:
                    articles = self._parse_google_news_results(html)
                else:
                    logger.warning("Crawlbase API failed, falling back to RSS...")
                    return self._handle_captcha_fallback(keyword, max_results)
            else:
                # Parse results
                articles = self._parse_google_news_results(response.text)
            
            logger.info(f"Found {len(articles)} articles for '{keyword}'")
            
        except Exception as e:
            logger.error(f"Error searching for '{keyword}': {str(e)}")
            
        return articles[:max_results]
    
    def _is_captcha_page(self, html: str) -> bool:
        """Check if the response contains a CAPTCHA"""
        captcha_indicators = [
            'captcha',
            'unusual traffic',
            'automated queries',
            'recaptcha',
            'verify you are human'
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)
    
    def _handle_captcha_fallback(self, keyword: str, max_results: int) -> List[NewsArticle]:
        """Fallback strategy when CAPTCHA is encountered"""
        logger.info("Implementing CAPTCHA fallback strategy...")
        
        # Strategy 1: Switch to a different proxy/session
        if self.proxy_list:
            logger.info("Switching to next proxy...")
            # Force new session
            session_id = self.request_count // self.requests_per_session
            if session_id in self.session_pool:
                del self.session_pool[session_id]
        
        # Strategy 2: Extended delay
        delay = random.uniform(60, 120)  # 1-2 minutes
        logger.info(f"Extended delay: {delay:.2f} seconds")
        time.sleep(delay)
        
        # Strategy 3: Try alternative approach (RSS feeds)
        return self._search_via_rss(keyword, max_results)
    
    def _search_via_rss(self, keyword: str, max_results: int) -> List[NewsArticle]:
        """Alternative search using Google News RSS"""
        try:
            # Google News RSS URL
            rss_url = f"https://news.google.com/rss/search?q={urlencode({'': keyword})[1:]}&hl=en&gl=us"
            
            session = self.get_rotating_session()
            response = session.get(rss_url, timeout=30)
            response.raise_for_status()
            
            # In ra 500 ký tự đầu của RSS response để debug
            logger.warning("In ra 500 ký tự đầu của RSS response để kiểm tra...")
            print("\n===== RSS RESPONSE (500 ký tự đầu) =====\n")
            print(response.text[:500])
            print("\n========================================\n")
            
            # Parse RSS feed
            soup = BeautifulSoup(response.content, 'xml')
            articles = []
            
            for item in soup.find_all('item')[:max_results]:
                try:
                    article = NewsArticle(
                        headline=item.title.text if item.title else "N/A",
                        link=item.link.text if item.link else "N/A",
                        date=item.pubDate.text if item.pubDate else "N/A",
                        source=item.source.text if item.source else "N/A"
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing RSS item: {e}")
                    continue
                    
            logger.info(f"RSS fallback found {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"RSS fallback failed: {e}")
            return []
    
    def _parse_google_news_results(self, html: str) -> List[NewsArticle]:
        """Parse Google News search results"""
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # Google News result selectors (these may need updates)
        selectors = [
            'div[data-ved] a[href*="/url?"]',  # Standard news results
            'div.g a h3',  # Alternative selector
            'div.SoaBEf a',  # Another common selector
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                break
        else:
            # Nếu không tìm thấy elements nào, in ra một phần nội dung HTML để debug
            logger.warning("Không tìm thấy elements phù hợp! In ra 500 ký tự đầu của HTML để kiểm tra...")
            print("\n===== HTML RESPONSE (500 ký tự đầu) =====\n")
            print(html[:500])
            print("\n========================================\n")
            return []
        
        for element in elements:
            try:
                # Extract headline
                headline_elem = element.find('h3') or element
                headline = headline_elem.get_text(strip=True) if headline_elem else "N/A"
                
                # Extract link
                link = element.get('href', '')
                if link.startswith('/url?q='):
                    # Decode Google redirect URL
                    link = link.split('/url?q=')[1].split('&')[0]
                
                # Extract date (this is tricky with Google's structure)
                date_elem = element.find_parent().find(text=lambda x: x and any(
                    term in x.lower() for term in ['ago', 'hours', 'days', 'minutes']
                ))
                date = date_elem.strip() if date_elem else "N/A"
                
                if headline != "N/A" and link:
                    article = NewsArticle(
                        headline=headline,
                        link=link,
                        date=date
                    )
                    articles.append(article)
                    
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
                
        return articles
    
    def scrape_multiple_keywords(self, keywords: List[str], max_results_per_keyword: int = 20) -> Dict[str, List[NewsArticle]]:
        """
        Scrape Google News for multiple keywords
        
        Args:
            keywords: List of search terms
            max_results_per_keyword: Maximum results per keyword
            
        Returns:
            Dictionary mapping keywords to their articles
        """
        results = {}
        
        logger.info(f"Starting scraping for {len(keywords)} keywords...")
        
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"Processing keyword {i}/{len(keywords)}: {keyword}")
            
            articles = self.search_google_news(keyword, max_results_per_keyword)
            results[keyword] = articles
            
            # Progress update
            if i % 10 == 0:
                logger.info(f"Completed {i}/{len(keywords)} keywords")
        
        logger.info("Scraping completed!")
        return results
    
    def export_results(self, results: Dict[str, List[NewsArticle]], filename: str = "google_news_results.json"):
        """Export results to JSON file"""
        export_data = {}
        
        for keyword, articles in results.items():
            export_data[keyword] = [
                {
                    'headline': article.headline,
                    'link': article.link,
                    'date': article.date,
                    'source': article.source
                }
                for article in articles
            ]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results exported to {filename}")

def generate_keyword_variations(base_keyword: str, max_pages: int = 10) -> List[str]:
    """
    Trả về keyword gốc - không tạo variations, chỉ lấy bài mới nhất
    
    Args:
        base_keyword: Keyword gốc
        max_pages: Không sử dụng, chỉ giữ để compatibility
    
    Returns:
        List chỉ chứa keyword gốc
    """
    # Chỉ trả về keyword gốc, không tạo variations
    return [base_keyword]

def crawl_keyword_multiple_pages(keyword: str, pages_per_keyword: int = 10, articles_per_page: int = 20, stats: CrawlStats = None) -> List[NewsArticle]:
    """
    Crawl một keyword - chỉ lấy bài mới nhất không dùng variations
    
    Args:
        keyword: Keyword gốc
        pages_per_keyword: Không sử dụng, chỉ giữ để compatibility
        articles_per_page: Số bài muốn lấy
        stats: Object thống kê
    
    Returns:
        List bài báo mới nhất cho keyword
    """
    if stats is None:
        stats = CrawlStats()
    
    print(f"🔍 Crawling latest articles for keyword: {keyword}")
    
    # Chỉ crawl keyword gốc, lấy nhiều bài hơn để đảm bảo có đủ bài mới nhất
    articles = simple_crawl_rss(keyword, articles_per_page, stats)
    
    print(f"🎯 Found {len(articles)} articles for '{keyword}'")
    return articles

def simple_crawl_rss(keyword: str, max_results: int = 20, stats: CrawlStats = None) -> List[NewsArticle]:
    """Crawl Google News RSS đơn giản - ít bị chặn"""
    if stats is None:
        stats = CrawlStats()
    
    try:
        # Google News RSS URL với keyword
        encoded_keyword = quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=en&gl=us&ceid=US:en"
        
        # Headers đơn giản
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Gọi RSS
        response = requests.get(rss_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse RSS với lxml hoặc html.parser làm fallback
        try:
            soup = BeautifulSoup(response.content, 'xml')
        except:
            try:
                soup = BeautifulSoup(response.content, 'lxml-xml')
            except:
                soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        
        # Tìm tất cả các item trong RSS
        items = soup.find_all('item')
        
        for i, item in enumerate(items[:max_results]):
            try:
                title = item.title.text if item.title else "N/A"
                link = item.link.text if item.link else "N/A"
                pub_date = item.pubDate.text if item.pubDate else "N/A"
                
                # Lấy source từ description hoặc source tag
                source = "N/A"
                if item.source:
                    source = item.source.text
                elif item.description:
                    desc = item.description.text
                    # Extract source từ description nếu có
                    import re
                    source_match = re.search(r'<a[^>]*>([^<]+)</a>', desc)
                    if source_match:
                        source = source_match.group(1)
                
                article = NewsArticle(
                    headline=title,
                    link=link,
                    date=pub_date,
                    source=source
                )
                articles.append(article)
                
            except Exception as e:
                stats.errors += 1
                continue
        
        stats.successful_requests += 1
        return articles
        
    except Exception as e:
        stats.failed_requests += 1
        stats.errors += 1
        return []

def extract_domain(url: str) -> str:
    """Trích xuất domain từ URL"""
    try:
        if not url or url == 'N/A':
            return 'N/A'
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Loại bỏ 'www.' nếu có
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except:
        return 'N/A'

def bulk_crawl_to_csv(keywords: List[str], pages_per_keyword: int = 10, articles_per_page: int = 20, csv_filename: str = None) -> str:
    """
    Crawl nhiều keyword với nhiều trang mỗi keyword và xuất ra CSV
    
    Args:
        keywords: Danh sách từ khóa
        pages_per_keyword: Số trang mỗi keyword
        articles_per_page: Số bài mỗi trang
        csv_filename: Tên file CSV output
    
    Returns:
        Tên file CSV đã tạo
    """
    
    # Tạo tên file CSV với timestamp
    if csv_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"crawl_results_{timestamp}.csv"
    
    # Khởi tạo stats
    stats = CrawlStats()
    stats.total_keywords = len(keywords)
    
    estimated_articles = len(keywords) * pages_per_keyword * articles_per_page
    
    print(f"🔥 GOOGLE NEWS BULK CRAWLER - MULTI-PAGE MODE")
    print("=" * 70)
    print(f"📝 Keywords to crawl: {len(keywords)}")
    print(f"📄 Pages per keyword: {pages_per_keyword}")
    print(f"📊 Articles per page: {articles_per_page}")
    print(f"🎯 Estimated total articles: {estimated_articles}")
    print(f"📁 Output file: {csv_filename}")
    print("=" * 70)
    
    # Tạo và mở file CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'keyword', 'article_number', 'headline', 'link', 
            'date', 'source', 'domain', 'crawl_timestamp'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Crawl từng keyword
        for i, keyword in enumerate(keywords, 1):
            print(f"\n📋 Processing keyword {i}/{len(keywords)}: {keyword}")
            
            # Delay ngẫu nhiên giữa các keyword
            if i > 1:
                delay = random.uniform(5, 10)
                print(f"⏳ Waiting {delay:.1f} seconds between keywords...")
                time.sleep(delay)
            
            # Crawl nhiều trang cho keyword này
            all_articles = crawl_keyword_multiple_pages(
                keyword, 
                pages_per_keyword, 
                articles_per_page, 
                stats
            )
            
            # Ghi từng bài báo vào CSV
            for j, article in enumerate(all_articles, 1):
                row = {
                    'keyword': keyword,
                    'article_number': j,
                    'headline': article.headline,
                    'link': article.link,
                    'date': article.date,
                    'source': article.source,
                    'domain': extract_domain(article.link),
                    'crawl_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                writer.writerow(row)
            
            stats.total_articles += len(all_articles)
            
            # Progress update
            print(f"📊 Completed {i}/{len(keywords)} keywords. Total articles so far: {stats.total_articles}")
    
    # In thống kê cuối cùng
    print_final_stats(stats, csv_filename)
    
    return csv_filename

def print_final_stats(stats: CrawlStats, csv_filename: str):
    """In thống kê cuối cùng"""
    print("\n" + "=" * 60)
    print("🎯 CRAWL STATISTICS")
    print("=" * 60)
    print(f"📋 Total Keywords: {stats.total_keywords}")
    print(f"📰 Total Articles: {stats.total_articles}")
    print(f"✅ Successful Requests: {stats.successful_requests}")
    print(f"❌ Failed Requests: {stats.failed_requests}")
    print(f"⚠️ Total Errors: {stats.errors}")
    print(f"🚫 Captcha Skipped: {stats.captcha_skipped}")
    print(f"📁 Output File: {csv_filename}")
    
    if stats.total_keywords > 0:
        success_rate = (stats.successful_requests / stats.total_keywords) * 100
        avg_articles = stats.total_articles / stats.total_keywords if stats.total_keywords > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"📊 Average Articles per Keyword: {avg_articles:.1f}")
    
    print("=" * 60)
    print("🎉 Crawl completed successfully!")

def crawl_single_keyword_deep(keyword: str, target_articles: int = 200, csv_filename: str = None) -> str:
    """
    Crawl 1 keyword để lấy bài mới nhất (không dùng variations)
    
    Args:
        keyword: Keyword muốn crawl
        target_articles: Số bài mục tiêu
        csv_filename: Tên file CSV output
    
    Returns:
        Tên file CSV đã tạo
    """
    
    # Tạo tên file CSV với keyword và timestamp
    if csv_filename is None:
        safe_keyword = keyword.replace(' ', '_').replace('/', '_').replace('\\', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"{safe_keyword}_{timestamp}.csv"
    
    # Khởi tạo stats
    stats = CrawlStats()
    stats.total_keywords = 1
    
    print(f"🔥 CRAWL LATEST ARTICLES FOR SINGLE KEYWORD")
    print("=" * 60)
    print(f"🎯 Keyword: {keyword}")
    print(f"📊 Target articles: {target_articles}")
    print(f"📁 Output file: {csv_filename}")
    print("=" * 60)
    
    print(f"🔍 Crawling latest articles for '{keyword}'...")
    
    # Chỉ crawl keyword gốc để lấy bài mới nhất
    articles = simple_crawl_rss(keyword, target_articles, stats)
    
    # Tạo và mở file CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'article_number', 'headline', 'link', 
            'date', 'source', 'domain', 'crawl_timestamp'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Ghi từng bài báo vào CSV
        for i, article in enumerate(articles, 1):
            row = {
                'article_number': i,
                'headline': article.headline,
                'link': article.link,
                'date': article.date,
                'source': article.source,
                'domain': extract_domain(article.link),
                'crawl_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            writer.writerow(row)
    
    stats.total_articles = len(articles)
    
    # In thống kê cuối cùng
    print_single_keyword_stats(stats, csv_filename, keyword, len(articles), target_articles)
    
    return csv_filename

def print_single_keyword_stats(stats: CrawlStats, csv_filename: str, keyword: str, actual_articles: int, target_articles: int):
    """In thống kê cho single keyword crawl"""
    print("\n" + "=" * 60)
    print("🎯 CRAWL RESULTS")
    print("=" * 60)
    print(f"🔍 Keyword: {keyword}")
    print(f"📰 Articles Found: {actual_articles}")
    print(f"🎯 Target Articles: {target_articles}")
    print(f"✅ Successful Requests: {stats.successful_requests}")
    print(f"❌ Failed Requests: {stats.failed_requests}")
    print(f"⚠️ Total Errors: {stats.errors}")
    print(f"🚫 Captcha Skipped: {stats.captcha_skipped}")
    print(f"📁 Output File: {csv_filename}")
    
    # Progress percentage
    progress = min(actual_articles / target_articles * 100, 100) if target_articles > 0 else 0
    print(f"📈 Target Achievement: {progress:.1f}%")
    
    if actual_articles >= target_articles:
        print("🎉 Target achieved successfully!")
    else:
        print(f"ℹ️ Found {actual_articles} articles (target was {target_articles})")
    
    print("=" * 60)

def crawl_multiple_keywords_deep(keywords: List[str], target_articles_per_keyword: int = 200, csv_filename: str = None) -> str:
    """
    Crawl nhiều keywords, mỗi keyword lấy ~200 bài
    
    Args:
        keywords: Danh sách keywords
        target_articles_per_keyword: Số bài mục tiêu cho mỗi keyword
        csv_filename: Tên file CSV output
    
    Returns:
        Tên file CSV đã tạo
    """
    
    # Tạo tên file CSV với timestamp
    if csv_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"multi_keywords_crawl_{timestamp}.csv"
    
    # Khởi tạo stats tổng
    total_stats = CrawlStats()
    total_stats.total_keywords = len(keywords)
    
    print(f"🔥 MULTI-KEYWORDS DEEP CRAWLER")
    print("=" * 70)
    print(f"📝 Keywords: {len(keywords)}")
    print(f"📊 Target articles per keyword: {target_articles_per_keyword}")
    print(f"🎯 Total target articles: {len(keywords) * target_articles_per_keyword}")
    print(f"📁 Output file: {csv_filename}")
    print("=" * 70)
    
    # Hiển thị keywords sẽ crawl
    print("📋 KEYWORDS TO CRAWL:")
    for i, keyword in enumerate(keywords, 1):
        print(f"   {i}. {keyword}")
    print()
    
    all_articles = []
    
    # Tạo và mở file CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'keyword', 'article_number', 'headline', 'link', 
            'date', 'source', 'domain', 'crawl_timestamp'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Crawl từng keyword
        for keyword_index, keyword in enumerate(keywords, 1):
            print(f"\n🔍 PROCESSING KEYWORD {keyword_index}/{len(keywords)}: {keyword}")
            print("-" * 50)
            
            # Delay giữa các keywords
            if keyword_index > 1:
                delay = random.uniform(8, 15)
                print(f"⏳ Waiting {delay:.1f} seconds between keywords...")
                time.sleep(delay)
            
            # Crawl keyword này
            keyword_articles = crawl_single_keyword_for_multi(
                keyword, 
                target_articles_per_keyword, 
                total_stats
            )
            
            # Ghi tất cả bài báo của keyword này vào CSV
            for i, article in enumerate(keyword_articles, 1):
                row = {
                    'keyword': keyword,
                    'article_number': i,
                    'headline': article.headline,
                    'link': article.link,
                    'date': article.date,
                    'source': article.source,
                    'domain': extract_domain(article.link),
                    'crawl_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                writer.writerow(row)
            
            all_articles.extend(keyword_articles)
            
            # Progress update
            print(f"✅ Completed {keyword}: {len(keyword_articles)} articles")
            print(f"📊 Overall progress: {keyword_index}/{len(keywords)} keywords, {len(all_articles)} total articles")
    
    total_stats.total_articles = len(all_articles)
    
    # In thống kê cuối cùng
    print_multi_keywords_stats(total_stats, csv_filename, keywords, target_articles_per_keyword, len(all_articles))
    
    return csv_filename

def crawl_single_keyword_for_multi(keyword: str, target_articles: int, stats: CrawlStats) -> List[NewsArticle]:
    """
    Crawl 1 keyword cho multi-keyword crawl - chỉ lấy bài mới nhất
    
    Args:
        keyword: Keyword muốn crawl
        target_articles: Số bài mục tiêu
        stats: Object thống kê chung
    
    Returns:
        List các bài báo mới nhất
    """
    
    print(f"🔍 Crawling latest articles for '{keyword}'...")
    
    # Chỉ crawl keyword gốc với số bài được yêu cầu
    articles = simple_crawl_rss(keyword, target_articles, stats)
    
    print(f"🎯 Found {len(articles)} articles for '{keyword}'")
    return articles

def print_multi_keywords_stats(stats: CrawlStats, csv_filename: str, keywords: List[str], target_per_keyword: int, total_articles: int):
    """In thống kê cho multi-keywords crawl"""
    print("\n" + "=" * 70)
    print("🎯 MULTI-KEYWORDS CRAWL RESULTS")
    print("=" * 70)
    print(f"📝 Total Keywords: {len(keywords)}")
    print(f"📰 Total Articles Found: {total_articles}")
    print(f"🎯 Target Articles: {len(keywords) * target_per_keyword}")
    print(f"📊 Average Articles per Keyword: {total_articles / len(keywords):.1f}")
    print(f"✅ Successful Requests: {stats.successful_requests}")
    print(f"❌ Failed Requests: {stats.failed_requests}")
    print(f"⚠️ Total Errors: {stats.errors}")
    print(f"🚫 Captcha Skipped: {stats.captcha_skipped}")
    print(f"📁 Output File: {csv_filename}")
    
    # Progress percentage
    target_total = len(keywords) * target_per_keyword
    progress = min(total_articles / target_total * 100, 100) if target_total > 0 else 0
    print(f"📈 Overall Achievement: {progress:.1f}%")
    
    if total_articles >= target_total:
        print("🎉 All targets achieved successfully!")
    else:
        print(f"ℹ️ Found {total_articles} articles (target was {target_total})")
    
    print("=" * 70)
    print("🎉 Multi-keywords crawl completed!")

def read_keywords_from_csv(csv_file_path: str, keyword_column: str = None, skip_header: bool = True) -> List[str]:
    """
    Đọc keywords từ file CSV
    
    Args:
        csv_file_path: Đường dẫn đến file CSV chứa keywords
        keyword_column: Tên cột chứa keywords (nếu None sẽ lấy cột đầu tiên)
        skip_header: Có bỏ qua header row không
    
    Returns:
        List các keywords từ CSV
    """
    keywords = []
    
    try:
        print(f"📖 Reading keywords from CSV file: {csv_file_path}")
        
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            delimiter = ','
            if ';' in sample and sample.count(';') > sample.count(','):
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            
            print(f"📊 Detected CSV delimiter: '{delimiter}'")
            
            reader = csv.reader(csvfile, delimiter=delimiter)
            
            # Skip header if needed
            if skip_header:
                try:
                    header = next(reader)
                    print(f"📋 CSV Header: {header}")
                    
                    # Tự động detect keyword column nếu không được chỉ định
                    if keyword_column is None:
                        keyword_column = header[0]  # Lấy cột đầu tiên
                        keyword_col_index = 0
                    else:
                        # Tìm index của keyword column
                        keyword_col_index = None
                        for i, col in enumerate(header):
                            if col.lower().strip() == keyword_column.lower().strip():
                                keyword_col_index = i
                                break
                        
                        if keyword_col_index is None:
                            print(f"⚠️ Column '{keyword_column}' not found. Using first column.")
                            keyword_col_index = 0
                    
                    print(f"🎯 Using column '{header[keyword_col_index]}' (index: {keyword_col_index}) for keywords")
                    
                except StopIteration:
                    print("⚠️ CSV file is empty")
                    return []
            else:
                keyword_col_index = 0
            
            # Đọc keywords
            for row_num, row in enumerate(reader, start=2 if skip_header else 1):
                if row and len(row) > keyword_col_index:
                    keyword = row[keyword_col_index].strip()
                    if keyword:  # Bỏ qua dòng trống
                        keywords.append(keyword)
                        print(f"   ✅ Row {row_num}: '{keyword}'")
                else:
                    print(f"   ⚠️ Row {row_num}: Empty or invalid row")
        
        print(f"📊 Total keywords loaded: {len(keywords)}")
        return keywords
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {str(e)}")
        return []

def is_within_working_hours() -> bool:
    """
    Kiểm tra xem hiện tại có trong giờ làm việc không (10h - 18h)
    
    Returns:
        True nếu trong giờ làm việc, False nếu không
    """
    now = datetime.now()
    current_time = now.time()
    
    # Giờ làm việc: 10:00 - 18:00
    start_time = dt_time(10, 0)  # 10:00 AM
    end_time = dt_time(18, 0)    # 6:00 PM
    
    return start_time <= current_time <= end_time

def batch_crawl_keywords(keywords: List[str], articles_per_keyword: int = 10, batch_id: str = None) -> str:
    """
    Crawl keywords theo batch với số lượng bài ít để test tần suất cao
    
    Args:
        keywords: Danh sách keywords
        articles_per_keyword: Số bài mỗi keyword (mặc định 10)
        batch_id: ID của batch (nếu None sẽ tự tạo từ timestamp)
    
    Returns:
        Tên file CSV đã tạo
    """
    
    # Tạo batch ID và tên file
    if batch_id is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_id = f"batch_{timestamp}"
    
    csv_filename = f"../batches/{batch_id}.csv"
    
    # Tạo thư mục batches nếu chưa có
    os.makedirs("../batches", exist_ok=True)
    
    # Khởi tạo stats
    stats = CrawlStats()
    stats.total_keywords = len(keywords)
    
    batch_start_time = datetime.now()
    
    print(f"🔥 BATCH CRAWL - HIGH FREQUENCY TEST")
    print("=" * 60)
    print(f"🆔 Batch ID: {batch_id}")
    print(f"⏰ Start Time: {batch_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 Keywords: {len(keywords)}")
    print(f"📊 Articles per keyword: {articles_per_keyword}")
    print(f"🎯 Expected total articles: {len(keywords) * articles_per_keyword}")
    print(f"📁 Output file: {csv_filename}")
    print("=" * 60)
    
    all_articles = []
    
    # Tạo và mở file CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'batch_id', 'keyword', 'article_number', 'headline', 'link', 
            'date', 'source', 'domain', 'crawl_timestamp', 'keyword_index'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Crawl từng keyword
        for keyword_index, keyword in enumerate(keywords, 1):
            print(f"\n🔍 [{keyword_index}/{len(keywords)}] Processing: {keyword}")
            
            # Delay ngắn giữa các keyword (1-3 giây)
            if keyword_index > 1:
                delay = random.uniform(1, 3)
                print(f"⏳ Short delay: {delay:.1f}s...")
                time.sleep(delay)
            
            # Crawl keyword với số lượng bài ít
            keyword_articles = simple_crawl_rss(keyword, articles_per_keyword, stats)
            
            # Ghi từng bài báo vào CSV
            for i, article in enumerate(keyword_articles, 1):
                row = {
                    'batch_id': batch_id,
                    'keyword': keyword,
                    'article_number': i,
                    'headline': article.headline,
                    'link': article.link,
                    'date': article.date,
                    'source': article.source,
                    'domain': extract_domain(article.link),
                    'crawl_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'keyword_index': keyword_index
                }
                writer.writerow(row)
            
            all_articles.extend(keyword_articles)
            
            print(f"✅ Found {len(keyword_articles)} articles for '{keyword}'")
            
            # Progress update
            progress = (keyword_index / len(keywords)) * 100
            print(f"📊 Progress: {progress:.1f}% | Total articles: {len(all_articles)}")
    
    batch_end_time = datetime.now()
    batch_duration = batch_end_time - batch_start_time
    
    stats.total_articles = len(all_articles)
    
    # In thống kê batch
    print_batch_stats(stats, csv_filename, batch_id, batch_start_time, batch_end_time, batch_duration)
    
    return csv_filename

def print_batch_stats(stats: CrawlStats, csv_filename: str, batch_id: str, start_time: datetime, end_time: datetime, duration):
    """In thống kê cho batch crawl"""
    print("\n" + "=" * 60)
    print("🎯 BATCH CRAWL RESULTS")
    print("=" * 60)
    print(f"🆔 Batch ID: {batch_id}")
    print(f"⏰ Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏁 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Duration: {str(duration).split('.')[0]}")
    print(f"📋 Keywords Processed: {stats.total_keywords}")
    print(f"📰 Total Articles: {stats.total_articles}")
    print(f"✅ Successful Requests: {stats.successful_requests}")
    print(f"❌ Failed Requests: {stats.failed_requests}")
    print(f"⚠️ Total Errors: {stats.errors}")
    print(f"🚫 Captcha Skipped: {stats.captcha_skipped}")
    print(f"📁 Output File: {csv_filename}")
    
    if stats.total_keywords > 0:
        success_rate = (stats.successful_requests / stats.total_keywords) * 100
        avg_articles = stats.total_articles / stats.total_keywords
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"📊 Avg Articles/Keyword: {avg_articles:.1f}")
        
        # Tính tốc độ crawl
        total_minutes = duration.total_seconds() / 60
        keywords_per_minute = stats.total_keywords / total_minutes if total_minutes > 0 else 0
        articles_per_minute = stats.total_articles / total_minutes if total_minutes > 0 else 0
        
        print(f"⚡ Crawl Speed: {keywords_per_minute:.1f} keywords/min, {articles_per_minute:.1f} articles/min")
    
    print("=" * 60)
    print("🎉 Batch completed successfully!")

def scheduled_crawler():
    """
    Hàm chính để chạy theo schedule - được gọi bởi task scheduler
    Chạy mỗi tiếng 1 lần từ lúc kích hoạt đến khi dừng
    """
    
    print(f"🚀 SCHEDULED CRAWLER STARTED")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Đọc keywords từ file CSV
    csv_file_path = "keyword_csvs/Keywords.csv"
    keywords = read_keywords_from_csv(csv_file_path, keyword_column="Keywords")
    
    if not keywords:
        print("❌ No keywords loaded from CSV. Exiting...")
        return
    
    # Chạy batch crawl với 10 bài mỗi keyword
    batch_file = batch_crawl_keywords(
        keywords=keywords,
        articles_per_keyword=10
    )
    
    print(f"\n📁 Batch file created: {batch_file}")
    print("✅ Scheduled crawl completed!")

def create_batch_schedule_script():
    """
    Tạo file .bat để chạy với Windows Task Scheduler
    """
    
    # Lấy đường dẫn hiện tại
    current_dir = os.getcwd()
    python_script = os.path.join(current_dir, "pypassCapcha.py")
    
    bat_content = f'''@echo off
cd /d "{current_dir}"
python "{python_script}" --scheduled
pause
'''
    
    bat_filename = "run_scheduled_crawler.bat"
    
    with open(bat_filename, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    print(f"📁 Created batch file: {bat_filename}")
    print("\n🔧 TASK SCHEDULER SETUP INSTRUCTIONS:")
    print("=" * 50)
    print("1. Open Windows Task Scheduler")
    print("2. Create Basic Task...")
    print("3. Name: 'Google News Crawler'")
    print("4. Trigger: Daily")
    print("5. Start time: [Choose your preferred start time]")
    print("6. Repeat task every: 1 hour")
    print("7. For a duration of: Indefinitely (or choose your duration)")
    print(f"8. Action: Start a program")
    print(f"9. Program/script: {os.path.abspath(bat_filename)}")
    print("10. Click Finish")
    print("=" * 50)
    print("\n💡 The crawler will run every 1 hour from when you activate it")
    print("💡 Each batch will crawl ~600 articles (60 keywords x 10 articles)")
    print("💡 To stop: Disable or delete the task in Task Scheduler")

def run_manual_test():
    """
    Chạy test thủ công để kiểm tra
    """
    print("🧪 MANUAL TEST MODE")
    print("=" * 40)
    
    # Đọc keywords
    csv_file_path = "keyword_csvs/Keywords.csv"
    keywords = read_keywords_from_csv(csv_file_path, keyword_column="Keywords")
    
    if not keywords:
        print("❌ No keywords loaded. Exiting...")
        return
    
    # Lấy 5 keywords đầu tiên để test nhanh
    test_keywords = keywords[:5]
    print(f"🧪 Testing with {len(test_keywords)} keywords:")
    for i, kw in enumerate(test_keywords, 1):
        print(f"   {i}. {kw}")
    print()
    
    # Chạy batch test
    batch_file = batch_crawl_keywords(
        keywords=test_keywords,
        articles_per_keyword=10,
        batch_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"\n📁 Test batch file: {batch_file}")
    print("✅ Manual test completed!")

def main():
    """Hàm chính được cập nhật để hỗ trợ các mode khác nhau"""
    
    import sys
    
    # Kiểm tra command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scheduled':
            # Mode chạy theo schedule
            scheduled_crawler()
            return
        elif sys.argv[1] == '--test':
            # Mode test thủ công
            run_manual_test()
            return
        elif sys.argv[1] == '--setup':
            # Mode setup task scheduler
            create_batch_schedule_script()
            return
    
    # Mode mặc định - hỏi user
    print("🔥 GOOGLE NEWS BATCH CRAWLER")
    print("=" * 50)
    print("Select mode:")
    print("1. Manual test (5 keywords x 10 articles)")
    print("2. Create scheduler setup")
    print("3. Run scheduled crawl (if within working hours)")
    print("4. Full crawl (original mode)")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        run_manual_test()
    elif choice == '2':
        create_batch_schedule_script()
    elif choice == '3':
        scheduled_crawler()
    elif choice == '4':
        # Mode crawl đầy đủ như cũ
        csv_file_path = "keyword_csvs/Keywords.csv"
        keywords = read_keywords_from_csv(csv_file_path, keyword_column="Keywords")
        
        if not keywords:
            print("❌ No keywords loaded from CSV. Please check your file.")
            return
        
        target_articles_per_keyword = 200
        csv_file = crawl_multiple_keywords_deep(
            keywords=keywords,
            target_articles_per_keyword=target_articles_per_keyword
        )
        
        print(f"\n📁 Data exported to: {csv_file}")
    else:
        print("❌ Invalid choice. Exiting...")

if __name__ == "__main__":
    main()