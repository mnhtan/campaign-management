#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hệ thống theo dõi giá bạc/vàng tự động
Thu thập dữ liệu, tạo biểu đồ và gửi báo cáo PDF qua email hàng tuần
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import schedule
import time
import re
from typing import Dict, List, Optional
import warnings
import numpy as np
from matplotlib.patches import Rectangle
warnings.filterwarnings('ignore')

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('precious_metals.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PreciousMetalsTracker:
    def __init__(self, db_path: str = "precious_metals.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.setup_database()
        
        # Cấu hình matplotlib cho tiếng Việt
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
    def setup_database(self):
        """Tạo database và bảng lưu trữ dữ liệu"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                gold_price_vn REAL,
                silver_price_vn_buy REAL,
                silver_price_vn_sell REAL,
                silver_price_intl_usd REAL,
                silver_price_intl_vnd REAL,
                gold_silver_diff REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_silver_price_vn(self) -> Dict[str, float]:
        """Lấy giá bạc Việt Nam từ giabac.vn"""
        try:
            url = "https://giabac.vn/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tìm bảng giá bạc Phú Quý
            prices = {}
            
            # Tìm các ô chứa giá
            price_cells = soup.find_all('td')
            for i, cell in enumerate(price_cells):
                text = cell.get_text(strip=True)
                if 'Bạc miếng Phú Quý 999 1 lượng' in text:
                    # Lấy giá mua và bán từ các ô tiếp theo
                    try:
                        buy_price = price_cells[i+2].get_text(strip=True)
                        sell_price = price_cells[i+3].get_text(strip=True)
                        
                        # Xử lý chuỗi giá (loại bỏ dấu phẩy)
                        buy_price = float(re.sub(r'[^\d.]', '', buy_price))
                        sell_price = float(re.sub(r'[^\d.]', '', sell_price))
                        
                        prices['buy'] = buy_price
                        prices['sell'] = sell_price
                        break
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error parsing silver prices: {e}")
                        continue
            
            if not prices:
                # Fallback: tìm giá theo cách khác
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        product = cells[0].get_text(strip=True)
                        if 'Bạc miếng Phú Quý 999 1 lượng' in product:
                            try:
                                buy_price = float(re.sub(r'[^\d.]', '', cells[2].get_text(strip=True)))
                                sell_price = float(re.sub(r'[^\d.]', '', cells[3].get_text(strip=True)))
                                prices['buy'] = buy_price
                                prices['sell'] = sell_price
                                break
                            except ValueError:
                                continue
            
            logger.info(f"Silver VN prices: {prices}")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching silver VN prices: {e}")
            return {}
    
    def get_silver_price_international(self) -> Dict[str, float]:
        """Lấy giá bạc quốc tế từ giabac.net"""
        try:
            url = "https://giabac.net/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = {}
            
            # Tìm bảng giá bạc thế giới - cách tiếp cận đơn giản hơn
            # Tìm tất cả các text chứa "Lượng" hoặc price patterns
            all_text = soup.get_text()
            
            # Thử tìm giá USD và VND từ text
            import re
            
            # Pattern để tìm giá (số có dấu phẩy hoặc chấm)
            price_patterns = re.findall(r'[\d,]+\.?\d*', all_text)
            
            # Nếu không tìm được từ giabac.net, dùng API backup
            if not prices:
                try:
                    # Sử dụng API metals.live cho giá bạc USD
                    api_url = "https://api.metals.live/v1/spot/silver"
                    api_response = self.session.get(api_url, timeout=10)
                    if api_response.status_code == 200:
                        data = api_response.json()
                        silver_usd_per_oz = data[0]['price']
                        
                        # Quy đổi sang lượng (1 lượng = 37.5g, 1 oz = 31.1g)
                        silver_usd_per_luong = silver_usd_per_oz * (37.5 / 31.1)
                        prices['usd'] = round(silver_usd_per_luong, 2)
                        
                        # Quy đổi sang VND (tỷ giá tham khảo)
                        usd_to_vnd = 25000
                        silver_vnd_per_luong = silver_usd_per_luong * usd_to_vnd
                        prices['vnd'] = round(silver_vnd_per_luong, 0)
                        
                        logger.info(f"Silver International prices from API: {prices}")
                        return prices
                except Exception as api_error:
                    logger.warning(f"API backup failed: {api_error}")
            
            # Fallback với giá ước tính
            if not prices:
                prices = {
                    'usd': 32.50,  # USD/lượng
                    'vnd': 812500  # VND/lượng (32.5 * 25000)
                }
                logger.warning(f"Using fallback silver international prices: {prices}")
            
            logger.info(f"Silver International prices: {prices}")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching international silver prices: {e}")
            # Trả về giá fallback
            return {
                'usd': 32.50,
                'vnd': 812500
            }
    
    def get_gold_price_vn(self) -> Optional[float]:
        """Lấy giá vàng Việt Nam từ cafef.vn"""
        try:
            url = "https://cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Thử nhiều cách tìm giá vàng SJC
            gold_price = None
            
            # Cách 1: Tìm trong bảng
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        text = cell.get_text(strip=True)
                        if 'SJC' in text.upper() or 'VÀNG SJC' in text.upper():
                            # Tìm giá bán trong các ô tiếp theo
                            try:
                                # Thử các ô tiếp theo
                                for j in range(1, min(len(cells) - i, 4)):
                                    next_cell = cells[i + j]
                                    price_text = next_cell.get_text(strip=True)
                                    # Tìm số có dấu phẩy (giá vàng thường có dạng 85,123 hoặc 85.123)
                                    import re
                                    price_match = re.search(r'[\d,\.]+', price_text)
                                    if price_match:
                                        price_str = price_match.group().replace(',', '').replace('.', '')
                                        if len(price_str) >= 4:  # Giá vàng ít nhất 4 chữ số
                                            potential_price = float(price_str)
                                            # Giá vàng VN thường từ 60-100 triệu/lượng
                                            if 600000 <= potential_price <= 1000000:  # 60-100 triệu
                                                gold_price = potential_price * 100  # Nhân 100 để thành đơn vị VNĐ
                                                break
                                            elif 60 <= potential_price <= 100:  # Đã tính theo triệu
                                                gold_price = potential_price * 1000000
                                                break
                                if gold_price:
                                    break
                            except (ValueError, IndexError):
                                continue
                    if gold_price:
                        break
                if gold_price:
                    break
            
            # Cách 2: Tìm trực tiếp trong text
            if not gold_price:
                page_text = soup.get_text()
                import re
                # Tìm pattern "SJC ... số"
                sjc_patterns = re.findall(r'SJC.*?(\d{2,3}[,\.]?\d{3})', page_text)
                for pattern in sjc_patterns:
                    try:
                        price_str = pattern.replace(',', '').replace('.', '')
                        potential_price = float(price_str)
                        if 60000 <= potential_price <= 100000:
                            gold_price = potential_price * 1000
                            break
                        elif 60 <= potential_price <= 100:
                            gold_price = potential_price * 1000000
                            break
                    except ValueError:
                        continue
            
            # Cách 3: Sử dụng API vàng thế giới và quy đổi
            if not gold_price:
                try:
                    api_url = "https://api.metals.live/v1/spot/gold"
                    api_response = self.session.get(api_url, timeout=10)
                    if api_response.status_code == 200:
                        data = api_response.json()
                        gold_usd_per_oz = data[0]['price']
                        # Quy đổi sang VND/lượng (1 lượng = 37.5g, 1 oz = 31.1g)
                        usd_to_vnd = 25000  # Tỷ giá tham khảo
                        gold_vnd_per_luong = gold_usd_per_oz * (37.5 / 31.1) * usd_to_vnd
                        # Thêm premium cho vàng SJC (thường cao hơn giá thế giới 5-10%)
                        gold_price = gold_vnd_per_luong * 1.07  # +7% premium
                        logger.info(f"Gold VN price from API with premium: {gold_price}")
                except Exception as api_error:
                    logger.warning(f"Gold API backup failed: {api_error}")
            
            # Fallback cuối cùng
            if not gold_price:
                gold_price = 85000000  # 85 triệu đồng/lượng
                logger.warning(f"Using fallback gold price: {gold_price}")
            
            logger.info(f"Gold VN price: {gold_price}")
            return gold_price
            
        except Exception as e:
            logger.error(f"Error fetching gold VN price: {e}")
            return self.get_gold_price_fallback()
    
    def get_gold_price_fallback(self) -> Optional[float]:
        """Phương thức dự phòng lấy giá vàng"""
        try:
            # Sử dụng giá vàng thế giới và quy đổi
            url = "https://api.metals.live/v1/spot/gold"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                gold_usd_per_oz = data[0]['price']
                # Quy đổi sang VND/lượng (1 lượng = 37.5g, 1 oz = 31.1g)
                usd_to_vnd = 25000  # Tỷ giá tham khảo
                gold_vnd_per_luong = gold_usd_per_oz * (37.5 / 31.1) * usd_to_vnd
                return gold_vnd_per_luong
        except:
            # Giá vàng cố định tạm thời nếu không lấy được
            return 85000000  # 85 triệu đồng/lượng
    
    def collect_data(self):
        """Thu thập tất cả dữ liệu giá"""
        logger.info("Starting data collection...")
        
        # Lấy dữ liệu từ các nguồn
        silver_vn = self.get_silver_price_vn()
        silver_intl = self.get_silver_price_international()
        gold_vn = self.get_gold_price_vn()
        
        # Chuẩn bị dữ liệu để lưu
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        silver_vn_buy = silver_vn.get('buy', 0)
        silver_vn_sell = silver_vn.get('sell', 0)
        silver_intl_usd = silver_intl.get('usd', 0)
        silver_intl_vnd = silver_intl.get('vnd', 0)
        gold_vn_price = gold_vn or 0
        
        # Tính chênh lệch giá vàng - bạc
        gold_silver_diff = 0
        if gold_vn_price > 0 and silver_vn_sell > 0:
            gold_silver_diff = gold_vn_price - silver_vn_sell
        
        # Lưu vào database
        self.save_data(
            date=current_date,
            gold_price_vn=gold_vn_price,
            silver_price_vn_buy=silver_vn_buy,
            silver_price_vn_sell=silver_vn_sell,
            silver_price_intl_usd=silver_intl_usd,
            silver_price_intl_vnd=silver_intl_vnd,
            gold_silver_diff=gold_silver_diff
        )
        
        logger.info("Data collection completed successfully")
    
    def save_data(self, **kwargs):
        """Lưu dữ liệu vào database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Kiểm tra xem đã có dữ liệu cho ngày này chưa
        cursor.execute("SELECT id FROM prices WHERE date = ?", (kwargs['date'],))
        existing = cursor.fetchone()
        
        if existing:
            # Cập nhật dữ liệu hiện có
            cursor.execute('''
                UPDATE prices SET
                    gold_price_vn = ?,
                    silver_price_vn_buy = ?,
                    silver_price_vn_sell = ?,
                    silver_price_intl_usd = ?,
                    silver_price_intl_vnd = ?,
                    gold_silver_diff = ?,
                    timestamp = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (
                kwargs['gold_price_vn'],
                kwargs['silver_price_vn_buy'],
                kwargs['silver_price_vn_sell'],
                kwargs['silver_price_intl_usd'],
                kwargs['silver_price_intl_vnd'],
                kwargs['gold_silver_diff'],
                kwargs['date']
            ))
        else:
            # Thêm dữ liệu mới
            cursor.execute('''
                INSERT INTO prices (
                    date, gold_price_vn, silver_price_vn_buy, silver_price_vn_sell,
                    silver_price_intl_usd, silver_price_intl_vnd, gold_silver_diff
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                kwargs['date'],
                kwargs['gold_price_vn'],
                kwargs['silver_price_vn_buy'],
                kwargs['silver_price_vn_sell'],
                kwargs['silver_price_intl_usd'],
                kwargs['silver_price_intl_vnd'],
                kwargs['gold_silver_diff']
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Data saved for {kwargs['date']}")
    
    def get_historical_data(self, days: int = 30) -> pd.DataFrame:
        """Lấy dữ liệu lịch sử từ database"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM prices 
            WHERE date >= date('now', '-{} days')
            ORDER BY date ASC
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def create_charts(self, df: pd.DataFrame, save_path: str = "charts"):
        """Tạo biểu đồ giá cả kiểu cổ phiếu với technical indicators"""
        if df.empty:
            logger.warning("No data available for creating charts")
            return []
        
        os.makedirs(save_path, exist_ok=True)
        chart_files = []
        
        # Tính toán technical indicators
        df = self.calculate_technical_indicators(df)
        
        # Thiết lập style
        plt.style.use('seaborn-v0_8')
        
        # 1. Biểu đồ chính với Moving Averages và Bollinger Bands
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[3, 1, 1])
        
        # Subplot 1: Price và MA, Bollinger Bands
        ax1.plot(df['date'], df['silver_price_vn_sell'], label='Giá bạc VN', linewidth=2, color='black')
        
        # Moving Averages
        if 'silver_ma5' in df.columns:
            ax1.plot(df['date'], df['silver_ma5'], label='MA5', linewidth=1, color='blue', alpha=0.7)
        if 'silver_ma10' in df.columns:
            ax1.plot(df['date'], df['silver_ma10'], label='MA10', linewidth=1, color='orange', alpha=0.7)
        if 'silver_ma20' in df.columns:
            ax1.plot(df['date'], df['silver_ma20'], label='MA20', linewidth=1, color='red', alpha=0.7)
        
        # Bollinger Bands
        if all(col in df.columns for col in ['silver_bb_upper', 'silver_bb_lower']):
            ax1.fill_between(df['date'], df['silver_bb_upper'], df['silver_bb_lower'], 
                           alpha=0.2, color='gray', label='Bollinger Bands')
            ax1.plot(df['date'], df['silver_bb_upper'], linewidth=1, color='gray', linestyle='--')
            ax1.plot(df['date'], df['silver_bb_lower'], linewidth=1, color='gray', linestyle='--')
        
        ax1.set_title('📈 Biểu đồ kỹ thuật giá Bạc Việt Nam (Phú Quý)', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Giá (VNĐ/lượng)', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Subplot 2: RSI
        if 'silver_rsi' in df.columns:
            ax2.plot(df['date'], df['silver_rsi'], linewidth=2, color='purple')
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
            ax2.fill_between(df['date'], 70, 100, alpha=0.2, color='red')
            ax2.fill_between(df['date'], 0, 30, alpha=0.2, color='green')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper right')
        
        # Subplot 3: Daily Change %
        if 'silver_change_pct' in df.columns:
            colors = ['green' if x >= 0 else 'red' for x in df['silver_change_pct']]
            ax3.bar(df['date'], df['silver_change_pct'], color=colors, alpha=0.7, width=0.8)
            ax3.axhline(y=0, color='black', linewidth=0.5)
            ax3.set_ylabel('% Thay đổi', fontsize=12)
            ax3.grid(True, alpha=0.3)
        
        # Format trục x cho tất cả subplots
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        
        ax3.set_xlabel('Ngày', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_file = os.path.join(save_path, 'silver_technical_analysis.png')
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        chart_files.append(chart_file)
        plt.close()
        
        # 2. Biểu đồ so sánh giá bạc VN và quốc tế với premium/discount
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Subplot 1: Price comparison
        ax1.plot(df['date'], df['silver_price_vn_sell'], label='Bạc VN (bán)', linewidth=2, color='red')
        ax1.plot(df['date'], df['silver_price_intl_vnd'], label='Bạc quốc tế (VNĐ)', linewidth=2, color='green')
        
        ax1.set_title('📊 So sánh giá bạc Việt Nam và Quốc tế', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Giá (VNĐ/lượng)', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Subplot 2: Premium/Discount
        premium = ((df['silver_price_vn_sell'] - df['silver_price_intl_vnd']) / df['silver_price_intl_vnd'] * 100).fillna(0)
        colors = ['green' if x >= 0 else 'red' for x in premium]
        ax2.bar(df['date'], premium, color=colors, alpha=0.7, width=0.8)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.set_ylabel('Premium/Discount (%)', fontsize=12)
        ax2.set_xlabel('Ngày', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_file = os.path.join(save_path, 'silver_comparison.png')
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        chart_files.append(chart_file)
        plt.close()
        
        # 3. Biểu đồ Gold/Silver Ratio và Market Overview
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Subplot 1: Gold/Silver Ratio
        gold_silver_ratio = df['gold_price_vn'] / df['silver_price_vn_sell']
        ax1.plot(df['date'], gold_silver_ratio, label='Tỷ lệ Vàng/Bạc', linewidth=2, color='gold')
        ax1.fill_between(df['date'], gold_silver_ratio, alpha=0.3, color='gold')
        
        # Historical average lines
        avg_ratio = gold_silver_ratio.mean()
        ax1.axhline(y=avg_ratio, color='blue', linestyle='--', alpha=0.7, label=f'Trung bình: {avg_ratio:.1f}')
        ax1.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='Mức cao (80)')
        ax1.axhline(y=60, color='green', linestyle='--', alpha=0.5, label='Mức thấp (60)')
        
        ax1.set_title('📈 Tỷ lệ giá Vàng/Bạc Việt Nam', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Ratio', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Subplot 2: Volatility Analysis
        if 'silver_volatility' in df.columns:
            ax2.plot(df['date'], df['silver_volatility'], label='Độ biến động 7 ngày', linewidth=2, color='purple')
            ax2.fill_between(df['date'], df['silver_volatility'], alpha=0.3, color='purple')
            
            avg_vol = df['silver_volatility'].mean()
            ax2.axhline(y=avg_vol, color='orange', linestyle='--', alpha=0.7, label=f'TB: {avg_vol:.2f}%')
            
            ax2.set_ylabel('Volatility (%)', fontsize=12)
            ax2.set_xlabel('Ngày', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_file = os.path.join(save_path, 'market_analysis.png')
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        chart_files.append(chart_file)
        plt.close()
        
        logger.info(f"Created {len(chart_files)} charts")
        return chart_files
    
    def create_pdf_report(self, df: pd.DataFrame, chart_files: List[str], filename: str = None) -> str:
        """Tạo báo cáo PDF với market insights - Hỗ trợ tiếng Việt đầy đủ"""
        if filename is None:
            filename = f"precious_metals_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Cấu hình font Unicode cho tiếng Việt
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.fonts import addMapping
        
        font_name = 'Helvetica'  # Default fallback
        
        try:
            # Thử đăng ký các font khác nhau
            font_registered = False
            
            # 1. Thử Arial Unicode MS (Windows)
            try:
                arial_paths = [
                    "C:/Windows/Fonts/ARIALUNI.TTF",
                    "C:/Windows/Fonts/arial.ttf", 
                    "/System/Library/Fonts/Arial.ttf",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
                ]
                
                for path in arial_paths:
                    if os.path.exists(path):
                        pdfmetrics.registerFont(TTFont('VietnameseFont', path))
                        font_name = 'VietnameseFont'
                        font_registered = True
                        logger.info(f"Registered font: {path}")
                        break
            except Exception as e:
                logger.warning(f"Font registration failed: {e}")
            
            # 2. Fallback: Sử dụng Helvetica với Unicode support
            if not font_registered:
                logger.warning("Using Helvetica with Unicode support")
                font_name = 'Helvetica'
                
        except Exception as e:
            logger.warning(f"Font setup failed: {e}, using Helvetica")
            font_name = 'Helvetica'
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Tùy chỉnh styles với font Unicode và encoding UTF-8
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1,  # Center alignment
            fontName=font_name
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            textColor=colors.darkblue,
            fontName=font_name
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            leftIndent=20,
            fontName=font_name
        )
        
        alert_style = ParagraphStyle(
            'AlertBox',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.white,
            backColor=colors.darkblue,
            borderColor=colors.black,
            borderWidth=1,
            borderPadding=10,
            alignment=1,
            fontName=font_name
        )
        
        # Tính toán technical indicators và insights
        df_with_indicators = self.calculate_technical_indicators(df)
        insights = self.generate_market_insights(df_with_indicators)
        
        # Tiêu đề báo cáo với tiếng Việt có dấu
        title_text = "📊 BÁO CÁO PHÂN TÍCH KỸ THUẬT BẠC - VÀNG"
        title = Paragraph(title_text, title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Market Alert Box với tiếng Việt có dấu
        if insights:
            signal_text = insights.get('signal', 'N/A')
            alert_text = f"🚨 TÍN HIỆU THỊ TRƯỜNG: {signal_text}"
            story.append(Paragraph(alert_text, alert_style))
            story.append(Spacer(1, 20))
        
        # Executive Summary với tiếng Việt có dấu
        summary_heading = "📈 TÓM TẮT ĐIỀU HÀNH"
        story.append(Paragraph(summary_heading, heading_style))
        
        if not df.empty and insights:
            latest_data = df.iloc[-1]
            first_data = df.iloc[0]
            
            summary_text = f"""
            <b>Thời gian báo cáo:</b> {first_data['date'].strftime('%d/%m/%Y')} - {latest_data['date'].strftime('%d/%m/%Y')}<br/>
            <b>Giá hiện tại:</b> {insights['current_price']:,.0f} VNĐ/lượng<br/>
            <b>Xu hướng:</b> {insights['trend']}<br/>
            <b>Biến động tuần:</b> {insights['week_change']:+.2f}%<br/>
            <b>Biến động tháng:</b> {insights['month_change']:+.2f}%<br/>
            <b>RSI (14):</b> {insights['rsi']:.1f}<br/>
            <b>So với MA20:</b> {insights['price_vs_ma20']:+.2f}%<br/>
            <b>Tỷ lệ Vàng/Bạc:</b> {insights['gold_silver_ratio']:.1f}<br/>
            <b>Volatility (7d):</b> {insights['volatility_7d']:.2f}%
            """
            
            overview = Paragraph(summary_text, normal_style)
            story.append(overview)
            story.append(Spacer(1, 20))
        
        # Market Analysis với tiếng Việt có dấu
        analysis_heading = "🔍 PHÂN TÍCH THỊ TRƯỜNG"
        story.append(Paragraph(analysis_heading, heading_style))
        
        if insights:
            # Phân tích RSI với tiếng Việt có dấu
            rsi_analysis = ""
            if insights['rsi'] > 70:
                rsi_analysis = "Thị trường đang trong vùng mua quá mức (overbought). Cần thận trọng với rủi ro điều chỉnh giá."
            elif insights['rsi'] < 30:
                rsi_analysis = "Thị trường đang trong vùng bán quá mức (oversold). Có thể là cơ hội mua vào."
            else:
                rsi_analysis = "RSI ở mức trung tính, thị trường đang cân bằng."
            
            # Phân tích xu hướng với tiếng Việt có dấu
            trend_analysis = ""
            if insights['trend'] == 'Tăng':
                trend_analysis = "Xu hướng tăng đang được duy trì. Giá đang ở trên đường MA20."
            elif insights['trend'] == 'Giảm':
                trend_analysis = "Xu hướng giảm đang diễn ra. Giá đang dưới đường MA20."
            else:
                trend_analysis = "Thị trường đang sideway, không có xu hướng rõ ràng."
            
            # Phân tích volatility với tiếng Việt có dấu
            vol_analysis = ""
            if insights['volatility_7d'] > 3:
                vol_analysis = "Độ biến động cao, thị trường đang không ổn định."
            elif insights['volatility_7d'] < 1:
                vol_analysis = "Độ biến động thấp, thị trường đang ổn định."
            else:
                vol_analysis = "Độ biến động ở mức bình thường."
            
            analysis_text = f"""
            <b>Phân tích RSI:</b> {rsi_analysis}<br/><br/>
            <b>Phân tích xu hướng:</b> {trend_analysis}<br/><br/>
            <b>Phân tích độ biến động:</b> {vol_analysis}<br/><br/>
            <b>Support/Resistance tuần:</b> {insights['price_range_7d']['min']:,.0f} - {insights['price_range_7d']['max']:,.0f} VNĐ
            """
            
            analysis_para = Paragraph(analysis_text, normal_style)
            story.append(analysis_para)
            story.append(Spacer(1, 20))
        
        # Thêm biểu đồ
        for chart_file in chart_files:
            if os.path.exists(chart_file):
                story.append(Spacer(1, 10))
                # Resize hình để fit trang A4
                img = Image(chart_file, width=7*inch, height=5*inch)
                story.append(img)
                story.append(Spacer(1, 20))
        
        # Trading Signals Table với tiếng Việt có dấu
        if insights:
            signals_heading = "⚡ BẢNG TÍN HIỆU GIAO DỊCH"
            story.append(Paragraph(signals_heading, heading_style))
            story.append(Spacer(1, 10))
            
            signal_data = [
                ['Chỉ báo', 'Giá trị', 'Tín hiệu', 'Ghi chú']
            ]
            
            # RSI Signal
            rsi_signal = "Mua" if insights['rsi'] < 30 else "Bán" if insights['rsi'] > 70 else "Neutral"
            signal_data.append(['RSI (14)', f"{insights['rsi']:.1f}", rsi_signal, "30-70 là vùng neutral"])
            
            # MA Signal  
            ma_signal = "Tăng" if insights['price_vs_ma20'] > 0 else "Giảm"
            signal_data.append(['Price vs MA20', f"{insights['price_vs_ma20']:+.2f}%", ma_signal, "So sánh với MA20"])
            
            # Trend Signal
            signal_data.append(['Xu hướng', insights['trend'], insights['trend'], "Dựa trên MA20"])
            
            # Overall Signal
            signal_data.append(['Tổng hợp', insights['signal'], insights['signal'], "Kết hợp các chỉ báo"])
            
            signal_table = Table(signal_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 2*inch])
            signal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                # Highlight overall signal row
                ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
                ('FONTNAME', (0, -1), (-1, -1), font_name),
            ]))
            
            story.append(signal_table)
            story.append(Spacer(1, 20))
        
        # Bảng dữ liệu chi tiết với tiếng Việt có dấu
        if not df.empty:
            data_heading = "📋 DỮ LIỆU CHI TIẾT 7 NGÀY GẦN NHẤT"
            story.append(Paragraph(data_heading, heading_style))
            story.append(Spacer(1, 10))
            
            # Lấy 7 dòng cuối với indicators
            recent_df = df_with_indicators.tail(7) if 'df_with_indicators' in locals() else df.tail(7)
            
            # Tạo dữ liệu cho bảng với tiếng Việt có dấu
            table_data = [
                ['Ngày', 'Giá bạc VN', 'MA5', 'MA20', 'RSI', '% Thay đổi', 'Trend']
            ]
            
            for _, row in recent_df.iterrows():
                table_data.append([
                    row['date'].strftime('%d/%m'),
                    f"{row['silver_price_vn_sell']:,.0f}",
                    f"{row.get('silver_ma5', 0):,.0f}" if pd.notna(row.get('silver_ma5', 0)) else "N/A",
                    f"{row.get('silver_ma20', 0):,.0f}" if pd.notna(row.get('silver_ma20', 0)) else "N/A",
                    f"{row.get('silver_rsi', 0):.1f}" if pd.notna(row.get('silver_rsi', 0)) else "N/A",
                    f"{row.get('silver_change_pct', 0):+.2f}%" if pd.notna(row.get('silver_change_pct', 0)) else "N/A",
                    row.get('trend', 'N/A')
                ])
            
            table = Table(table_data, colWidths=[0.8*inch, 1*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        # Risk Disclaimer với tiếng Việt có dấu
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.red,
            backColor=colors.lightgrey,
            borderPadding=5,
            fontName=font_name
        )
        
        disclaimer_text = """
        <b>⚠️ LƯU Ý RỦI RO:</b> Báo cáo này chỉ mang tính chất tham khảo và không phải lời khuyên đầu tư. 
        Giá kim loại quý có thể biến động mạnh và đầu tư luôn tiềm ẩn rủi ro. 
        Nhà đầu tư nên cân nhắc kỹ và tham khảo ý kiến chuyên gia trước khi đưa ra quyết định.
        """
        
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        
        # Tạo PDF với encoding UTF-8
        try:
            doc.build(story)
            logger.info(f"PDF report created with Vietnamese support: {filename}")
        except Exception as e:
            logger.error(f"Error creating PDF: {e}")
            # Fallback: tạo PDF đơn giản
            self.create_simple_pdf_report(df, chart_files, filename)
        
        return filename
    
    def create_simple_pdf_report(self, df: pd.DataFrame, chart_files: List[str], filename: str) -> str:
        """Tạo báo cáo PDF đơn giản khi có lỗi font Unicode"""
        try:
            doc = SimpleDocTemplate(filename, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Title đơn giản
            title = Paragraph("BAO CAO PHAN TICH KY THUAT BAC - VANG", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Thêm biểu đồ
            for chart_file in chart_files:
                if os.path.exists(chart_file):
                    img = Image(chart_file, width=7*inch, height=5*inch)
                    story.append(img)
                    story.append(Spacer(1, 20))
            
            # Dữ liệu cơ bản
            if not df.empty:
                latest = df.iloc[-1]
                
                basic_info = f"""
                Thoi gian: {latest['date'].strftime('%d/%m/%Y')}
                Gia bac VN: {latest['silver_price_vn_sell']:,.0f} VND/luong
                Gia bac QT: {latest['silver_price_intl_usd']:.2f} USD/luong
                Gia vang VN: {latest['gold_price_vn']:,.0f} VND/luong
                """
                
                story.append(Paragraph(basic_info, styles['Normal']))
            
            doc.build(story)
            logger.info(f"Simple PDF report created: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to create simple PDF: {e}")
        
        return filename
    
    def send_email_report(self, pdf_file: str, recipient_email: str, smtp_config: Dict):
        """Gửi báo cáo qua email"""
        try:
            # Tạo email
            msg = MIMEMultipart()
            msg['From'] = smtp_config['sender_email']
            msg['To'] = recipient_email
            msg['Subject'] = f"Báo cáo giá Bạc - Vàng tuần ({datetime.now().strftime('%d/%m/%Y')})"
            
            # Nội dung email
            body = """
            Kính gửi Anh/Chị,
            
            Đây là báo cáo giá bạc và vàng tuần này.
            
            Báo cáo bao gồm:
            - Biểu đồ giá bạc Việt Nam
            - So sánh giá bạc VN và quốc tế
            - Chênh lệch giá vàng - bạc
            - Bảng dữ liệu chi tiết
            
            Trân trọng,
            Hệ thống theo dõi giá kim loại quý
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Đính kèm file PDF
            if os.path.exists(pdf_file):
                with open(pdf_file, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(pdf_file)}'
                )
                msg.attach(part)
            
            # Gửi email
            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            server.starttls()
            server.login(smtp_config['sender_email'], smtp_config['password'])
            
            text = msg.as_string()
            server.sendmail(smtp_config['sender_email'], recipient_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    def generate_weekly_report(self, recipient_email: str = None, smtp_config: Dict = None):
        """Tạo và gửi báo cáo tuần"""
        try:
            logger.info("Starting weekly report generation...")
            
            # Lấy dữ liệu 30 ngày gần nhất
            df = self.get_historical_data(30)
            
            if df.empty:
                logger.warning("No data available for report generation")
                return
            
            # Tạo biểu đồ
            chart_files = self.create_charts(df)
            
            # Tạo PDF
            pdf_file = self.create_pdf_report(df, chart_files)
            
            # Gửi email nếu có cấu hình
            if recipient_email and smtp_config:
                self.send_email_report(pdf_file, recipient_email, smtp_config)
            
            # Dọn dẹp các file biểu đồ tạm
            for chart_file in chart_files:
                try:
                    if os.path.exists(chart_file):
                        os.remove(chart_file)
                except:
                    pass
            
            logger.info("Weekly report generation completed successfully")
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán các chỉ số kỹ thuật"""
        if df.empty or len(df) < 20:
            return df
        
        df = df.copy()
        
        # Moving Averages cho giá bạc VN
        df['silver_ma5'] = df['silver_price_vn_sell'].rolling(window=5).mean()
        df['silver_ma10'] = df['silver_price_vn_sell'].rolling(window=10).mean()
        df['silver_ma20'] = df['silver_price_vn_sell'].rolling(window=20).mean()
        
        # RSI (Relative Strength Index)
        delta = df['silver_price_vn_sell'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['silver_rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['silver_bb_middle'] = df['silver_price_vn_sell'].rolling(window=20).mean()
        bb_std = df['silver_price_vn_sell'].rolling(window=20).std()
        df['silver_bb_upper'] = df['silver_bb_middle'] + (bb_std * 2)
        df['silver_bb_lower'] = df['silver_bb_middle'] - (bb_std * 2)
        
        # Volume/Volatility (% change day over day)
        df['silver_change_pct'] = df['silver_price_vn_sell'].pct_change() * 100
        df['silver_volatility'] = df['silver_change_pct'].rolling(window=7).std()
        
        # Trend direction
        df['trend'] = np.where(df['silver_price_vn_sell'] > df['silver_ma20'], 'Tăng', 
                              np.where(df['silver_price_vn_sell'] < df['silver_ma20'], 'Giảm', 'Sideway'))
        
        return df
    
    def generate_market_insights(self, df: pd.DataFrame) -> Dict:
        """Tạo insights thị trường"""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        week_ago = df.iloc[-7] if len(df) >= 7 else df.iloc[0]
        month_ago = df.iloc[-30] if len(df) >= 30 else df.iloc[0]
        
        insights = {
            'current_price': latest['silver_price_vn_sell'],
            'week_change': ((latest['silver_price_vn_sell'] - week_ago['silver_price_vn_sell']) / week_ago['silver_price_vn_sell']) * 100,
            'month_change': ((latest['silver_price_vn_sell'] - month_ago['silver_price_vn_sell']) / month_ago['silver_price_vn_sell']) * 100,
            'volatility_7d': df['silver_change_pct'].tail(7).std(),
            'trend': latest.get('trend', 'N/A'),
            'rsi': latest.get('silver_rsi', 0),
            'price_vs_ma20': ((latest['silver_price_vn_sell'] - latest.get('silver_ma20', latest['silver_price_vn_sell'])) / latest.get('silver_ma20', latest['silver_price_vn_sell'])) * 100,
            'gold_silver_ratio': latest['gold_price_vn'] / latest['silver_price_vn_sell'] if latest['silver_price_vn_sell'] > 0 else 0,
            'price_range_7d': {
                'min': df['silver_price_vn_sell'].tail(7).min(),
                'max': df['silver_price_vn_sell'].tail(7).max()
            }
        }
        
        # Tín hiệu mua/bán dựa trên RSI và MA
        if insights['rsi'] < 30 and insights['price_vs_ma20'] < -2:
            insights['signal'] = 'MUA - Oversold'
        elif insights['rsi'] > 70 and insights['price_vs_ma20'] > 2:
            insights['signal'] = 'BÁN - Overbought'
        elif insights['trend'] == 'Tăng' and insights['price_vs_ma20'] > 0:
            insights['signal'] = 'GIỮ - Uptrend'
        else:
            insights['signal'] = 'QUAN SÁT - Neutral'
        
        return insights
    
    def generate_sample_data(self, days: int = 30):
        """Tạo dữ liệu mẫu 30 ngày để test"""
        import random
        from datetime import datetime, timedelta
        
        logger.info(f"Generating {days} days of sample data...")
        
        # Giá cơ bản
        base_silver_vn_sell = 1420000  # VND/lượng
        base_silver_vn_buy = 1377000   # VND/lượng  
        base_silver_intl_usd = 32.5    # USD/lượng
        base_silver_intl_vnd = 812500  # VND/lượng
        base_gold_vn = 85000000        # VND/lượng
        
        # Tạo dữ liệu cho 30 ngày
        start_date = datetime.now() - timedelta(days=days-1)
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Thêm biến động ngẫu nhiên (-3% đến +3%)
            silver_variation = random.uniform(-0.03, 0.03)
            gold_variation = random.uniform(-0.02, 0.02)
            intl_variation = random.uniform(-0.04, 0.04)
            
            # Tính giá với biến động
            silver_vn_sell = base_silver_vn_sell * (1 + silver_variation)
            silver_vn_buy = silver_vn_sell * 0.97  # Spread ~3%
            
            silver_intl_usd = base_silver_intl_usd * (1 + intl_variation)
            silver_intl_vnd = silver_intl_usd * 25000  # Tỷ giá
            
            gold_vn = base_gold_vn * (1 + gold_variation)
            
            # Tính chênh lệch vàng - bạc
            gold_silver_diff = gold_vn - silver_vn_sell
            
            # Lưu vào database
            self.save_data(
                date=date_str,
                gold_price_vn=round(gold_vn, 0),
                silver_price_vn_buy=round(silver_vn_buy, 0),
                silver_price_vn_sell=round(silver_vn_sell, 0),
                silver_price_intl_usd=round(silver_intl_usd, 2),
                silver_price_intl_vnd=round(silver_intl_vnd, 0),
                gold_silver_diff=round(gold_silver_diff, 0)
            )
            
            # Cập nhật giá cơ bản cho ngày hôm sau (xu hướng)
            base_silver_vn_sell = silver_vn_sell
            base_silver_intl_usd = silver_intl_usd  
            base_gold_vn = gold_vn
        
        logger.info(f"Generated {days} days of sample data successfully")
    
    def view_sample_data(self, days: int = 7):
        """Xem dữ liệu mẫu"""
        df = self.get_historical_data(days)
        
        if df.empty:
            print("Không có dữ liệu!")
            return
        
        print(f"\n=== DỮ LIỆU {days} NGÀY GẦN NHẤT ===")
        print("-" * 80)
        print("| {:10} | {:12} | {:12} | {:10} | {:12} |".format(
            "Ngày", "Vàng VN", "Bạc VN (bán)", "Bạc QT USD", "Chênh lệch"
        ))
        print("-" * 80)
        
        for _, row in df.tail(days).iterrows():
            print("| {:10} | {:12,.0f} | {:12,.0f} | {:10.2f} | {:12,.0f} |".format(
                row['date'].strftime('%d/%m/%Y'),
                row['gold_price_vn'],
                row['silver_price_vn_sell'], 
                row['silver_price_intl_usd'],
                row['gold_silver_diff']
            ))
        
        print("-" * 80)
        print(f"Tổng cộng: {len(df)} ngày dữ liệu")
        
        # Thống kê cơ bản
        print(f"\n=== THỐNG KÊ CƠ BẢN ===")
        print(f"Giá bạc VN - Cao nhất: {df['silver_price_vn_sell'].max():,.0f} VNĐ")
        print(f"Giá bạc VN - Thấp nhất: {df['silver_price_vn_sell'].min():,.0f} VNĐ")
        print(f"Giá bạc VN - Trung bình: {df['silver_price_vn_sell'].mean():,.0f} VNĐ")
        print(f"Giá vàng VN - Trung bình: {df['gold_price_vn'].mean():,.0f} VNĐ")
        print(f"Tỷ lệ Vàng/Bạc trung bình: {(df['gold_price_vn'] / df['silver_price_vn_sell']).mean():.1f}")

def main():
    """Hàm main để chạy chương trình"""
    # Cấu hình email (cần điền thông tin thực tế)
    smtp_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': 'your_email@gmail.com',  # Thay bằng email thực
        'password': 'your_app_password'  # Thay bằng app password thực
    }
    
    recipient_email = 'recipient@gmail.com'  # Thay bằng email người nhận
    
    # Khởi tạo tracker
    tracker = PreciousMetalsTracker()
    
    def job_collect_data():
        """Job thu thập dữ liệu hàng ngày"""
        logger.info("Running daily data collection job...")
        tracker.collect_data()
    
    def job_weekly_report():
        """Job tạo báo cáo tuần"""
        logger.info("Running weekly report job...")
        tracker.generate_weekly_report(recipient_email, smtp_config)
    
    # Lên lịch chạy
    # Thu thập dữ liệu hàng ngày lúc 9:00 AM
    schedule.every().day.at("09:00").do(job_collect_data)
    
    # Tạo báo cáo tuần vào thứ 2 hàng tuần lúc 10:00 AM
    schedule.every().monday.at("10:00").do(job_weekly_report)
    
    # Chạy thu thập dữ liệu ngay lập tức
    logger.info("Starting initial data collection...")
    tracker.collect_data()
    
    print("=== HỆ THỐNG THEO DÕI GIÁ BẠC - VÀNG ===")
    print("Chương trình đang chạy...")
    print("- Thu thập dữ liệu hàng ngày lúc 9:00 AM")
    print("- Tạo báo cáo tuần vào thứ 2 lúc 10:00 AM")
    print("- Nhấn Ctrl+C để dừng chương trình")
    print("="*45)
    
    # Menu tương tác
    while True:
        try:
            print("\n📊 === MENU PHÂN TÍCH BẠC - VÀNG ===")
            print("1. 📥 Thu thập dữ liệu ngay")
            print("2. 📄 Tạo báo cáo PDF với phân tích kỹ thuật")
            print("3. 📈 Xem phân tích thị trường hiện tại")
            print("4. 🎲 Tạo dữ liệu mẫu 30 ngày")
            print("5. 📋 Xem dữ liệu hiện tại")
            print("6. ⏰ Chạy tự động (theo lịch)")
            print("7. 🚪 Thoát")
            
            choice = input("\nNhập lựa chọn (1-7): ").strip()
            
            if choice == '1':
                print("Đang thu thập dữ liệu...")
                tracker.collect_data()
                print("Thu thập dữ liệu hoàn tất!")
                
            elif choice == '2':
                print("Đang tạo báo cáo tuần...")
                tracker.generate_weekly_report(recipient_email, smtp_config)
                print("Tạo báo cáo hoàn tất!")
                
            elif choice == '3':
                df = tracker.get_historical_data(30)
                if not df.empty:
                    # Tính toán technical indicators và insights
                    df_with_indicators = tracker.calculate_technical_indicators(df)
                    insights = tracker.generate_market_insights(df_with_indicators)
                    
                    print("\n" + "="*60)
                    print("📊 PHÂN TÍCH THỊ TRƯỜNG BẠC HIỆN TẠI")
                    print("="*60)
                    
                    print(f"💰 Giá hiện tại: {insights['current_price']:,.0f} VNĐ/lượng")
                    print(f"📈 Xu hướng: {insights['trend']}")
                    print(f"📊 RSI (14): {insights['rsi']:.1f}")
                    print(f"📉 Biến động tuần: {insights['week_change']:+.2f}%")
                    print(f"📅 Biến động tháng: {insights['month_change']:+.2f}%")
                    print(f"⚡ Tín hiệu: {insights['signal']}")
                    print(f"🥇 Tỷ lệ Vàng/Bạc: {insights['gold_silver_ratio']:.1f}")
                    print(f"📊 Volatility (7d): {insights['volatility_7d']:.2f}%")
                    print(f"📌 Support/Resistance: {insights['price_range_7d']['min']:,.0f} - {insights['price_range_7d']['max']:,.0f} VNĐ")
                    
                    print("\n" + "-"*60)
                    print("DỮ LIỆU 5 NGÀY GẦN NHẤT")
                    print("-"*60)
                    
                    recent_data = df_with_indicators.tail(5)
                    for _, row in recent_data.iterrows():
                        print(f"📅 {row['date'].strftime('%d/%m/%Y')}")
                        print(f"   💲 Giá: {row['silver_price_vn_sell']:,.0f} VNĐ")
                        if pd.notna(row.get('silver_change_pct', 0)):
                            change_icon = "📈" if row['silver_change_pct'] >= 0 else "📉"
                            print(f"   {change_icon} Thay đổi: {row['silver_change_pct']:+.2f}%")
                        if pd.notna(row.get('silver_rsi', 0)):
                            print(f"   📊 RSI: {row['silver_rsi']:.1f}")
                        print()
                else:
                    print("Không có dữ liệu!")
            
            elif choice == '4':
                print("Đang tạo dữ liệu mẫu 30 ngày...")
                tracker.generate_sample_data(30)
                print("Tạo dữ liệu mẫu hoàn tất!")
                print("Có thể xem dữ liệu bằng tùy chọn 5")
                
            elif choice == '5':
                days = input("Nhập số ngày muốn xem (mặc định 7): ").strip()
                try:
                    days = int(days) if days else 7
                except:
                    days = 7
                tracker.view_sample_data(days)
                    
            elif choice == '6':
                print("Chạy tự động theo lịch...")
                print("Nhấn Ctrl+C để dừng")
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Kiểm tra mỗi phút
                    
            elif choice == '7':
                print("Tạm biệt!")
                break
                
            else:
                print("Lựa chọn không hợp lệ!")
                
        except KeyboardInterrupt:
            print("\nChương trình đã dừng.")
            break
        except Exception as e:
            logger.error(f"Error in main menu: {e}")
            print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()