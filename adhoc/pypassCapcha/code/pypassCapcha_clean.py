import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import quote
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import List

# Setup logging for simple output
import logging
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

def generate_keyword_variations(base_keyword: str, max_pages: int = 10) -> List[str]:
    """
    Tạo các variation của keyword để mô phỏng search nhiều trang
    
    Args:
        base_keyword: Keyword gốc
        max_pages: Số "trang" muốn search
    
    Returns:
        List các keyword variations
    """
    variations = [base_keyword]  # Keyword gốc
    
    # Thêm các variation để lấy nhiều bài hơn
    suffixes = [
        "news", "latest", "updates", "trends", "developments", 
        "breakthrough", "innovation", "research", "market", "industry"
    ]
    
    time_suffixes = [
        "2024", "2025", "recent", "today", "this week", "latest news"
    ]
    
    # Thêm suffixes
    for suffix in suffixes[:max_pages-1]:
        if len(variations) >= max_pages:
            break
        variations.append(f"{base_keyword} {suffix}")
    
    # Nếu vẫn chưa đủ, thêm time suffixes
    for time_suffix in time_suffixes:
        if len(variations) >= max_pages:
            break
        variations.append(f"{base_keyword} {time_suffix}")
    
    return variations[:max_pages]

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

def crawl_single_keyword_for_multi(keyword: str, target_articles: int, stats: CrawlStats) -> List[NewsArticle]:
    """
    Crawl 1 keyword sâu cho multi-keyword crawl
    
    Args:
        keyword: Keyword muốn crawl
        target_articles: Số bài mục tiêu
        stats: Object thống kê chung
    
    Returns:
        List các bài báo
    """
    
    all_articles = []
    seen_links = set()  # Để tránh duplicate
    
    # Tính số trang cần crawl (mỗi trang ~20 bài)
    articles_per_page = 20
    estimated_pages = (target_articles // articles_per_page) + 2  # +2 để đảm bảo đủ
    
    print(f"🔍 Crawling up to {estimated_pages} variations of '{keyword}'...")
    
    # Tạo các variation của keyword
    keyword_variations = generate_keyword_variations(keyword, estimated_pages)
    
    for page_num, variation in enumerate(keyword_variations, 1):
        if len(all_articles) >= target_articles:
            print(f"🎯 Reached target of {target_articles} articles, stopping...")
            break
            
        print(f"   📄 Page {page_num}: {variation}")
        
        # Delay giữa các trang
        if page_num > 1:
            delay = random.uniform(2, 4)
            print(f"   ⏳ Delay: {delay:.1f}s...")
            time.sleep(delay)
        
        # Crawl từng variation
        page_articles = simple_crawl_rss(variation, articles_per_page, stats)
        
        # Lọc bỏ duplicate dựa trên link
        new_articles = []
        for article in page_articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                new_articles.append(article)
        
        # Thêm vào danh sách tổng
        all_articles.extend(new_articles)
        
        print(f"   ✅ Page {page_num}: +{len(new_articles)} new articles (total: {len(all_articles)})")
        
        # Progress bar cho keyword này
        progress = min(len(all_articles) / target_articles * 100, 100)
        print(f"   📊 Progress: {progress:.1f}% ({len(all_articles)}/{target_articles})")
    
    print(f"🎯 Total articles for '{keyword}': {len(all_articles)}")
    return all_articles

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

def main():
    """Hàm chính để crawl keywords từ file Keywords.csv"""
    
    print("🔥 GOOGLE NEWS KEYWORD CRAWLER (CLEANED VERSION)")
    print("=" * 60)
    
    # =================================================================
    # 📝 ĐỌC KEYWORDS TỪ FILE CSV:
    # =================================================================
    csv_file_path = "keyword_csvs/Keywords.csv"  # Đường dẫn file CSV
    
    print(f"📖 Reading keywords from: {csv_file_path}")
    
    # Đọc keywords từ CSV
    keywords = read_keywords_from_csv(csv_file_path, keyword_column="Keywords")
    
    if not keywords:
        print("❌ No keywords loaded from CSV. Please check your file.")
        return
    
    # =================================================================
    # ⚙️ CẤU HÌNH CRAWL:
    # =================================================================
    target_articles_per_keyword = 200   # Số bài mỗi keyword
    
    print("\n⚙️ CRAWL CONFIGURATION:")
    print(f"   📝 Number of keywords: {len(keywords)}")
    print(f"   📊 Target articles per keyword: {target_articles_per_keyword}")
    print(f"   🎯 Total target articles: {len(keywords) * target_articles_per_keyword}")
    print()
    
    # Hiển thị một số keywords đầu tiên
    print("📋 FIRST 10 KEYWORDS TO CRAWL:")
    for i, keyword in enumerate(keywords[:10], 1):
        print(f"   {i}. {keyword}")
    
    if len(keywords) > 10:
        print(f"   ... and {len(keywords) - 10} more keywords")
    print()
    
    # Bắt đầu crawl
    print("🚀 Starting crawl...")
    csv_file = crawl_multiple_keywords_deep(
        keywords=keywords,
        target_articles_per_keyword=target_articles_per_keyword
    )
    
    print(f"\n📁 Data exported to: {csv_file}")
    print(f"🔍 You now have data for {len(keywords)} keywords!")
    print("💡 Open the CSV file in Excel to view your data!")

if __name__ == "__main__":
    main() 