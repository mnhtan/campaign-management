#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module tạo báo cáo PDF tự động cho giá vàng và bạc
Tạo báo cáo chuyên nghiệp với time series charts, insights và raw data
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timedelta
import seaborn as sns
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import io
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import function từ script chính
try:
    from final_gold_silver_table_with_real_data import (
        get_international_silver_prices,
        get_vietnam_silver_prices, 
        get_sjc_gold_price,
        create_gold_prices_from_sjc
    )
    print("✅ Import functions từ script chính thành công")
except ImportError:
    print("⚠️ Không thể import từ script chính, sẽ sử dụng sample data")

# Set Vietnamese font và style cho matplotlib
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Arial', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.facecolor'] = 'white'
matplotlib.rcParams['axes.facecolor'] = 'white'
# Force matplotlib to use UTF-8 encoding
matplotlib.rcParams['svg.fonttype'] = 'none'
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
sns.set_style("whitegrid")
sns.set_palette("Set2")

class GoldSilverReportGenerator:
    def __init__(self):
        self.data = None
        self.report_date = datetime.now()
        self.charts_dir = "temp_charts"
        
        # Tạo thư mục temp cho charts
        if not os.path.exists(self.charts_dir):
            os.makedirs(self.charts_dir)
        
        # Setup font encoding cho tiếng Việt
        self._setup_fonts()
    
    def _setup_fonts(self):
        """Setup fonts hỗ trợ tiếng Việt cho PDF và charts"""
        self.vietnamese_font = 'Helvetica'  # Default fallback
        
        try:
            # Thử đăng ký các font khác nhau hỗ trợ tiếng Việt
            font_registered = False
            
            # Danh sách các đường dẫn font có thể có (theo thứ tự ưu tiên)
            font_paths = [
                "C:/Windows/Fonts/ARIAL.TTF",     # Windows Arial (standard)
                "C:/Windows/Fonts/ARIALUNI.TTF",  # Windows Arial Unicode (best)
                "C:/Windows/Fonts/times.ttf",     # Windows Times New Roman
                "C:/Windows/Fonts/calibri.ttf",   # Windows Calibri  
                "C:/Windows/Fonts/tahoma.ttf",    # Windows Tahoma
                "C:/Windows/Fonts/trebuc.ttf",    # Windows Trebuchet MS
                "/System/Library/Fonts/Arial.ttf", # macOS Arial
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux DejaVu
                "/usr/share/fonts/TTF/DejaVuSans.ttf", # Linux DejaVu alternative
                "DejaVuSans.ttf"  # Local file
            ]
            
            for i, path in enumerate(font_paths):
                try:
                    if os.path.exists(path):
                        font_name = f'VietnameseFont{i}'
                        pdfmetrics.registerFont(TTFont(font_name, path))
                        self.vietnamese_font = font_name
                        font_registered = True
                        print(f"✅ Đã đăng ký font tiếng Việt: {path} -> {font_name}")
                        break
                except Exception as e:
                    print(f"⚠️ Không thể đăng ký font {path}: {e}")
                    continue
            
            if not font_registered:
                print("⚠️ Không tìm thấy font tiếng Việt, sử dụng Helvetica")
                self.vietnamese_font = 'Helvetica'
                
        except Exception as e:
            print(f"❌ Lỗi setup font: {e}, sử dụng Helvetica")
            self.vietnamese_font = 'Helvetica'
    
    def _setup_matplotlib_font(self):
        """Thiết lập font cho matplotlib charts để hỗ trợ tiếng Việt"""
        try:
            # Import font manager
            from matplotlib import font_manager
            import matplotlib
            
            # Cấu hình cơ bản cho Unicode
            matplotlib.rcParams['axes.unicode_minus'] = False
            matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Arial', 'sans-serif']
            
            # Thiết lập encoding
            import locale
            try:
                locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
            except:
                try:
                    locale.setlocale(locale.LC_ALL, 'Vietnamese_Vietnam.1258')
                except:
                    pass  # Keep default locale
            
            # Tìm font family hỗ trợ tiếng Việt
            available_fonts = [f.name for f in font_manager.fontManager.ttflist]
            
            vietnamese_fonts = []
            preferred_fonts = [
                'Arial Unicode MS',  # Best for Vietnamese
                'Arial', 
                'Times New Roman', 
                'Calibri', 
                'Tahoma',
                'Segoe UI',
                'DejaVu Sans',
                'Liberation Sans'
            ]
            
            for font_name in preferred_fonts:
                if font_name in available_fonts:
                    vietnamese_fonts.append(font_name)
            
            if vietnamese_fonts:
                matplotlib.rcParams['font.family'] = vietnamese_fonts
                matplotlib.rcParams['font.sans-serif'] = vietnamese_fonts
                plt.rcParams['font.family'] = vietnamese_fonts
                plt.rcParams['font.sans-serif'] = vietnamese_fonts
                print(f"✅ Matplotlib font setup: {vietnamese_fonts[0]}")
            else:
                # Fallback to system default với unicode support
                matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
                plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
                print("⚠️ Sử dụng font mặc định với hỗ trợ Unicode")
                
        except Exception as e:
            print(f"❌ Lỗi setup font: {e}")
            # Basic fallback
            plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
    
    def collect_latest_data(self, days=60):
        """Thu thập dữ liệu mới nhất từ các API với nhiều ngày hơn cho time series"""
        print(f"📊 Đang thu thập dữ liệu {days} ngày gần nhất...")
        
        try:
            # Lấy dữ liệu từ các nguồn
            silver_international = get_international_silver_prices(days)
            vietnam_silver = get_vietnam_silver_prices(days)
            sjc_price = get_sjc_gold_price()
            
            if silver_international is not None and vietnam_silver is not None:
                # Xử lý merge data như script chính
                if len(vietnam_silver) >= len(silver_international):
                    base_dates = vietnam_silver['Date'].tolist()
                else:
                    base_dates = silver_international['Date'].tolist()
                
                # Tạo dữ liệu vàng VN
                if sjc_price:
                    vietnam_gold = create_gold_prices_from_sjc(base_dates, sjc_price)
                else:
                    vietnam_gold = create_gold_prices_from_sjc(base_dates, 12000000)
                
                # Merge data
                final_data = vietnam_gold.copy()
                final_data = pd.merge(final_data, vietnam_silver, on='Date', how='left')
                final_data = pd.merge(final_data, silver_international, on='Date', how='left')
                
                # Fill missing values với interpolation
                final_data['Silver_Price_VN'] = final_data['Silver_Price_VN'].interpolate(method='linear')
                final_data['Silver_Price_International'] = final_data['Silver_Price_International'].interpolate(method='linear')
                
                # Tính chênh lệch
                final_data['Difference'] = final_data['Gold_Price_VN'] - final_data['Silver_Price_VN']
                
                # Tính các chỉ số bổ sung
                final_data = self._calculate_technical_indicators(final_data)
                
                # Rename columns
                final_data.columns = ['Date', 'Gold Price VN', 'Silver Price VN', 'Silver Price International', 
                                    'Difference', 'Gold_MA7', 'Silver_VN_MA7', 'Silver_Intl_MA7', 
                                    'Gold_Volatility', 'Silver_VN_Volatility', 'Price_Ratio', 'Gold_RSI', 'Silver_RSI']
                
                final_data = final_data.sort_values('Date').dropna().reset_index(drop=True)
                
                print(f"✅ Thu thập thành công {len(final_data)} ngày dữ liệu")
                self.data = final_data
                return True
                
        except Exception as e:
            print(f"❌ Lỗi khi thu thập dữ liệu: {e}")
            
        return False
    
    def _calculate_technical_indicators(self, df):
        """Tính các chỉ số kỹ thuật bổ sung"""
        # Moving averages (7 ngày)
        df['Gold_MA7'] = df['Gold_Price_VN'].rolling(window=7).mean()
        df['Silver_VN_MA7'] = df['Silver_Price_VN'].rolling(window=7).mean()
        df['Silver_Intl_MA7'] = df['Silver_Price_International'].rolling(window=7).mean()
        
        # Volatility (rolling standard deviation)
        df['Gold_Volatility'] = df['Gold_Price_VN'].rolling(window=7).std()
        df['Silver_VN_Volatility'] = df['Silver_Price_VN'].rolling(window=7).std()
        
        # Price ratio
        df['Price_Ratio'] = df['Gold_Price_VN'] / df['Silver_Price_VN']
        
        # RSI calculation for both Gold and Silver
        df['Gold_RSI'] = self._calculate_rsi(df['Gold_Price_VN'], period=14)
        df['Silver_RSI'] = self._calculate_rsi(df['Silver_Price_VN'], period=14)
        
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """Tính RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def create_time_series_charts(self):
        """Tạo các time series charts chi tiết"""
        if self.data is None or self.data.empty:
            return []
        
        # Thiết lập font cho charts
        self._setup_matplotlib_font()
        
        chart_files = []
        
        # Chart 1: Main Time Series - Giá vàng và bạc VN
        # Kích thước tối ưu cho layout 2 biểu đồ/trang (14cm x 8.5cm display)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.3))
        
        # Subplot 1: Giá vàng và bạc VN
        ax1.plot(self.data['Date'], self.data['Gold Price VN'], 
                label='Giá Vàng VN', linewidth=2.5, color='gold', alpha=0.8)
        ax1.plot(self.data['Date'], self.data['Gold_MA7'], 
                label='MA7 Vàng', linewidth=1.5, color='orange', linestyle='--', alpha=0.7)
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(self.data['Date'], self.data['Silver Price VN'], 
                     label='Giá Bạc VN', linewidth=2.5, color='silver', alpha=0.8)
        ax1_twin.plot(self.data['Date'], self.data['Silver_VN_MA7'], 
                     label='MA7 Bạc VN', linewidth=1.5, color='gray', linestyle='--', alpha=0.7)
        
        ax1.set_title('Biểu đồ Time Series - Giá Vàng và Bạc Việt Nam', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel('Thời gian', fontsize=12)
        ax1.set_ylabel('Giá Vàng (VND/lượng)', fontsize=12, color='darkgoldenrod')
        ax1_twin.set_ylabel('Giá Bạc (VND/lượng)', fontsize=12, color='dimgray')
        
        # Format axes
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax1.tick_params(axis='x', rotation=45)
        
        # Format y-axis
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
        ax1_twin.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
        
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        ax1_twin.legend(loc='upper right')
        
        # Subplot 2: Giá bạc quốc tế và chênh lệch
        ax2.plot(self.data['Date'], self.data['Silver Price International'], 
                label='Giá Bạc Quốc Tế (USD/oz)', linewidth=2.5, color='blue', alpha=0.8)
        ax2.plot(self.data['Date'], self.data['Silver_Intl_MA7'], 
                label='MA7 Bạc Quốc Tế', linewidth=1.5, color='navy', linestyle='--', alpha=0.7)
        
        ax2_twin = ax2.twinx()
        ax2_twin.plot(self.data['Date'], self.data['Difference'], 
                     label='Chênh lệch Vàng-Bạc VN', linewidth=2, color='red', alpha=0.8)
        
        ax2.set_title('Giá Bạc Quốc Tế và Chênh Lệch Giá Trong Nước', 
                     fontsize=14, fontweight='bold', pad=15)
        ax2.set_xlabel('Thời gian', fontsize=12)
        ax2.set_ylabel('Giá Bạc Quốc Tế (USD/oz)', fontsize=12, color='blue')
        ax2_twin.set_ylabel('Chênh lệch (VND)', fontsize=12, color='red')
        
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax2.tick_params(axis='x', rotation=45)
        ax2_twin.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
        
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        ax2_twin.legend(loc='upper right')
        
        # Spacing tối ưu cho layout 2 biểu đồ/trang
        plt.subplots_adjust(hspace=0.5, left=0.08, right=0.92, top=0.92, bottom=0.12)
        
        chart_file1 = os.path.join(self.charts_dir, 'time_series_main.png')
       

        # Sử dụng pad_inches thay vì bbox_inches='tight' để giữ tỷ lệ ổn định
        plt.savefig(chart_file1, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file1)
        
        # Chart 2: RSI Time Series Comparison
        # Kích thước phù hợp cho layout 2 biểu đồ/trang
        fig, ax = plt.subplots(1, 1, figsize=(12, 7.3))
        
        # Plot RSI lines
        ax.plot(self.data['Date'], self.data['Gold_RSI'], 
                label='RSI Vàng VN', linewidth=2.5, color='gold', alpha=0.9)
        ax.plot(self.data['Date'], self.data['Silver_RSI'], 
                label='RSI Bạc VN', linewidth=2.5, color='silver', alpha=0.9)
        
        # Thêm các đường mức quan trọng
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label='Mua quá mức (70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='Bán quá mức (30)')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.5, linewidth=1, label='Trung tính (50)')
        
        # Tô màu các vùng
        ax.fill_between(self.data['Date'], 70, 100, alpha=0.15, color='red', label='Vùng mua quá mức')
        ax.fill_between(self.data['Date'], 0, 30, alpha=0.15, color='green', label='Vùng bán quá mức')
        ax.fill_between(self.data['Date'], 30, 70, alpha=0.08, color='gray', label='Vùng trung tính')
        
        ax.set_title('📊 So Sánh Chỉ Số RSI - Vàng và Bạc Việt Nam (14 ngày)', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Thời gian', fontsize=12)
        ax.set_ylabel('RSI', fontsize=13, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=10)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        ax.tick_params(axis='x', rotation=45)
        
        # Thêm text box với thống kê hiện tại
        current_gold_rsi = self.data['Gold_RSI'].iloc[-1]
        current_silver_rsi = self.data['Silver_RSI'].iloc[-1]
        rsi_diff = abs(current_gold_rsi - current_silver_rsi)
        
        stats_text = f"""Hiện tại:
• RSI Vàng: {current_gold_rsi:.1f}
• RSI Bạc: {current_silver_rsi:.1f}
• Chênh lệch: {rsi_diff:.1f}"""
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        # Margins tối ưu cho layout 2 biểu đồ/trang
        plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15)
        
        chart_file2 = os.path.join(self.charts_dir, 'rsi_time_series.png')
        plt.savefig(chart_file2, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file2)
        
        # Chart 3: RSI Histogram Distribution
        fig, ax = plt.subplots(1, 1, figsize=(12, 7.3))
        
        # Tạo histogram cho RSI
        ax.hist(self.data['Gold_RSI'].dropna(), bins=20, alpha=0.6, color='gold', 
                label='Phân phối RSI Vàng', edgecolor='darkgoldenrod', density=True)
        ax.hist(self.data['Silver_RSI'].dropna(), bins=20, alpha=0.6, color='silver', 
                label='Phân phối RSI Bạc', edgecolor='dimgray', density=True)
        
        # Thống kê mô tả
        gold_rsi_mean = self.data['Gold_RSI'].mean()
        silver_rsi_mean = self.data['Silver_RSI'].mean()
        
        ax.axvline(gold_rsi_mean, color='darkgoldenrod', linestyle='--', linewidth=2,
                   label=f'TB RSI Vàng: {gold_rsi_mean:.1f}')
        ax.axvline(silver_rsi_mean, color='dimgray', linestyle='--', linewidth=2,
                   label=f'TB RSI Bạc: {silver_rsi_mean:.1f}')
        
        # Đường phân vùng
        ax.axvline(30, color='green', linestyle=':', alpha=0.7, linewidth=2, label='Ngưỡng 30')
        ax.axvline(70, color='red', linestyle=':', alpha=0.7, linewidth=2, label='Ngưỡng 70')
        ax.axvline(50, color='gray', linestyle='-', alpha=0.5, linewidth=1, label='Trung tính 50')
        
        # Tô màu các vùng nền
        y_max = ax.get_ylim()[1]
        ax.fill_betweenx([0, y_max], 0, 30, alpha=0.1, color='green', label='Vùng bán quá mức')
        ax.fill_betweenx([0, y_max], 70, 100, alpha=0.1, color='red', label='Vùng mua quá mức')
        ax.fill_betweenx([0, y_max], 30, 70, alpha=0.05, color='gray', label='Vùng trung tính')
        
        ax.set_title(' Phân Phối RSI - So Sánh Tần Suất', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('RSI Value', fontsize=13, fontweight='bold')
        ax.set_ylabel('Mật độ', fontsize=13, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.legend(fontsize=10, loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Thêm text box với thống kê chi tiết
        current_gold_rsi = self.data['Gold_RSI'].iloc[-1]
        current_silver_rsi = self.data['Silver_RSI'].iloc[-1]
        
        # Tính phần trăm thời gian trong các vùng
        gold_overbought_pct = (self.data['Gold_RSI'] > 70).sum() / len(self.data) * 100
        gold_oversold_pct = (self.data['Gold_RSI'] < 30).sum() / len(self.data) * 100
        silver_overbought_pct = (self.data['Silver_RSI'] > 70).sum() / len(self.data) * 100
        silver_oversold_pct = (self.data['Silver_RSI'] < 30).sum() / len(self.data) * 100
        
        stats_text = f"""Thống kê:
• RSI Vàng: TB={gold_rsi_mean:.1f} | OB={gold_overbought_pct:.0f}% | OS={gold_oversold_pct:.0f}%
• RSI Bạc: TB={silver_rsi_mean:.1f} | OB={silver_overbought_pct:.0f}% | OS={silver_oversold_pct:.0f}%
• Hiện tại: Vàng={current_gold_rsi:.1f} | Bạc={current_silver_rsi:.1f}"""
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.12)
        
        chart_file3 = os.path.join(self.charts_dir, 'rsi_distribution.png')
        plt.savefig(chart_file3, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file3)
        
        # Chart 4: Correlation và Price Distribution
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 7.3))
        
        # Histogram phân phối giá bạc VN (ax1 - left) 
        ax1.hist(self.data['Silver Price VN'], bins=20, alpha=0.7, color='silver', edgecolor='black')
        ax1.axvline(self.data['Silver Price VN'].mean(), color='red', linestyle='--',
                   label=f'TB: {self.data["Silver Price VN"].mean():,.0f}')
        ax1.set_title('Phân Phối Giá Bạc VN', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Giá (VND/lượng)')
        ax1.set_ylabel('Tần suất')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Scatter plot correlation - Bạc VN vs Vàng VN (ax2 - right)
        scatter = ax2.scatter(self.data['Silver Price VN'], self.data['Gold Price VN'], 
                   alpha=0.6, color='blue', s=20)
        
        # Highlight điểm mới nhất màu đỏ
        latest_silver = self.data['Silver Price VN'].iloc[-1]
        latest_gold = self.data['Gold Price VN'].iloc[-1]
        ax2.scatter(latest_silver, latest_gold, color='red', s=100, alpha=0.9, 
                   edgecolors='darkred', linewidth=2, label='Ngày mới nhất')
        
        # Đường trend
        z = np.polyfit(self.data['Silver Price VN'], self.data['Gold Price VN'], 1)
        p = np.poly1d(z)
        ax2.plot(self.data['Silver Price VN'], p(self.data['Silver Price VN']), 
                "r--", alpha=0.8, label='Đường xu hướng')
        
        corr = self.data['Silver Price VN'].corr(self.data['Gold Price VN'])
        ax2.set_title(f'Tương Quan Bạc VN vs Vàng VN\n(r = {corr:.3f})', 
                     fontsize=12, fontweight='bold')
        ax2.set_xlabel('Giá Bạc VN (VND/lượng)')
        ax2.set_ylabel('Giá Vàng VN (VND/lượng)')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.12, wspace=0.25)
        
        chart_file4 = os.path.join(self.charts_dir, 'correlation_distribution.png')
        plt.savefig(chart_file4, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file4)

        print(f"✅ Đã tạo {len(chart_files)} charts time series")
        return chart_files
    
    def create_rsi_comparison_chart(self):
        """Tạo biểu đồ so sánh RSI của vàng và bạc"""
        if self.data is None or self.data.empty:
            return None
        
        # Thiết lập font cho charts
        self._setup_matplotlib_font()
        
        # Tạo figure với 2 subplots - kích thước cho layout 2 biểu đồ/trang
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.3))
        
        # Chart 1: RSI Time Series Comparison
        ax1.plot(self.data['Date'], self.data['Gold_RSI'], 
                label='RSI Vàng VN', linewidth=2.5, color='gold', alpha=0.9)
        ax1.plot(self.data['Date'], self.data['Silver_RSI'], 
                label='RSI Bạc VN', linewidth=2.5, color='silver', alpha=0.9)
        
        # Thêm các đường mức quan trọng
        ax1.axhline(y=70, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label='Mua quá mức (70)')
        ax1.axhline(y=30, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='Bán quá mức (30)')
        ax1.axhline(y=50, color='gray', linestyle='-', alpha=0.5, linewidth=1, label='Trung tính (50)')
        
        # Tô màu các vùng
        ax1.fill_between(self.data['Date'], 70, 100, alpha=0.15, color='red', label='Vùng mua quá mức')
        ax1.fill_between(self.data['Date'], 0, 30, alpha=0.15, color='green', label='Vùng bán quá mức')
        ax1.fill_between(self.data['Date'], 30, 70, alpha=0.08, color='gray', label='Vùng trung tính')
        
        ax1.set_title(' So Sánh Chỉ Số RSI - Vàng và Bạc Việt Nam (14 ngày)', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('RSI', fontsize=13, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        ax1.tick_params(axis='x', rotation=45)
        
        # Chart 2: RSI Histogram Distribution
        ax2.hist(self.data['Gold_RSI'].dropna(), bins=20, alpha=0.6, color='gold', 
                label='Phân phối RSI Vàng', edgecolor='darkgoldenrod', density=True)
        ax2.hist(self.data['Silver_RSI'].dropna(), bins=20, alpha=0.6, color='silver', 
                label='Phân phối RSI Bạc', edgecolor='dimgray', density=True)
        
        # Thống kê mô tả
        gold_rsi_mean = self.data['Gold_RSI'].mean()
        silver_rsi_mean = self.data['Silver_RSI'].mean()
        
        ax2.axvline(gold_rsi_mean, color='darkgoldenrod', linestyle='--', linewidth=2,
                   label=f'TB RSI Vàng: {gold_rsi_mean:.1f}')
        ax2.axvline(silver_rsi_mean, color='dimgray', linestyle='--', linewidth=2,
                   label=f'TB RSI Bạc: {silver_rsi_mean:.1f}')
        
        # Đường phân vùng
        ax2.axvline(30, color='green', linestyle=':', alpha=0.7, label='Ngưỡng 30')
        ax2.axvline(70, color='red', linestyle=':', alpha=0.7, label='Ngưỡng 70')
        
        ax2.set_title('📈 Phân Phối RSI - So Sánh Tần Suất', fontsize=14, fontweight='bold')
        ax2.set_xlabel('RSI Value', fontsize=12)
        ax2.set_ylabel('Mật độ', fontsize=12)
        ax2.set_xlim(0, 100)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        # Thêm text box với thống kê
        current_gold_rsi = self.data['Gold_RSI'].iloc[-1]
        current_silver_rsi = self.data['Silver_RSI'].iloc[-1]
        
        stats_text = f"""Hiện tại:
• RSI Vàng: {current_gold_rsi:.1f}
• RSI Bạc: {current_silver_rsi:.1f}
• Chênh lệch: {abs(current_gold_rsi - current_silver_rsi):.1f}"""
        
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.subplots_adjust(hspace=0.4, left=0.08, right=0.95, top=0.92, bottom=0.12)
        
        # Lưu chart
        chart_file = os.path.join(self.charts_dir, 'rsi_comparison.png')
        plt.savefig(chart_file, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        
        print(f"✅ Đã tạo biểu đồ so sánh RSI: {chart_file}")
        return chart_file
    
    def calculate_advanced_statistics(self):
        """Tính toán thống kê nâng cao và insights"""
        if self.data is None or self.data.empty:
            return {}
        
        # Basic statistics
        stats = {
            'period': f"{self.data['Date'].min().strftime('%d/%m/%Y')} - {self.data['Date'].max().strftime('%d/%m/%Y')}",
            'total_days': len(self.data),
            
            # Current values
            'gold_vn_current': self.data['Gold Price VN'].iloc[-1],
            'silver_vn_current': self.data['Silver Price VN'].iloc[-1],
            'silver_intl_current': self.data['Silver Price International'].iloc[-1],
            'difference_current': self.data['Difference'].iloc[-1],
            'price_ratio_current': self.data['Price_Ratio'].iloc[-1],
            
            # Gold statistics
            'gold_vn_min': self.data['Gold Price VN'].min(),
            'gold_vn_max': self.data['Gold Price VN'].max(),
            'gold_vn_avg': self.data['Gold Price VN'].mean(),
            'gold_vn_std': self.data['Gold Price VN'].std(),
            'gold_vn_change': self.data['Gold Price VN'].iloc[-1] - self.data['Gold Price VN'].iloc[0],
            'gold_vn_change_pct': ((self.data['Gold Price VN'].iloc[-1] / self.data['Gold Price VN'].iloc[0]) - 1) * 100,
            
            # Silver VN statistics
            'silver_vn_min': self.data['Silver Price VN'].min(),
            'silver_vn_max': self.data['Silver Price VN'].max(),
            'silver_vn_avg': self.data['Silver Price VN'].mean(),
            'silver_vn_std': self.data['Silver Price VN'].std(),
            'silver_vn_change': self.data['Silver Price VN'].iloc[-1] - self.data['Silver Price VN'].iloc[0],
            'silver_vn_change_pct': ((self.data['Silver Price VN'].iloc[-1] / self.data['Silver Price VN'].iloc[0]) - 1) * 100,
            
            # Silver International statistics
            'silver_intl_min': self.data['Silver Price International'].min(),
            'silver_intl_max': self.data['Silver Price International'].max(),
            'silver_intl_avg': self.data['Silver Price International'].mean(),
            'silver_intl_std': self.data['Silver Price International'].std(),
            'silver_intl_change': self.data['Silver Price International'].iloc[-1] - self.data['Silver Price International'].iloc[0],
            'silver_intl_change_pct': ((self.data['Silver Price International'].iloc[-1] / self.data['Silver Price International'].iloc[0]) - 1) * 100,
            
            # Advanced metrics
            'price_ratio_avg': self.data['Price_Ratio'].mean(),
            'price_ratio_min': self.data['Price_Ratio'].min(),
            'price_ratio_max': self.data['Price_Ratio'].max(),
            'correlation_silver_intl': self.data['Silver Price International'].corr(self.data['Silver Price VN']),
            'correlation_silver_gold': self.data['Silver Price VN'].corr(self.data['Gold Price VN']),
            
            # Volatility
            'gold_volatility_avg': self.data['Gold_Volatility'].mean() if 'Gold_Volatility' in self.data.columns else 0,
            'silver_volatility_avg': self.data['Silver_VN_Volatility'].mean() if 'Silver_VN_Volatility' in self.data.columns else 0,
            
            # RSI
            'rsi_gold_current': self.data['Gold_RSI'].iloc[-1] if 'Gold_RSI' in self.data.columns else 50,
            'rsi_gold_avg': self.data['Gold_RSI'].mean() if 'Gold_RSI' in self.data.columns else 50,
            'rsi_silver_current': self.data['Silver_RSI'].iloc[-1] if 'Silver_RSI' in self.data.columns else 50,
            'rsi_silver_avg': self.data['Silver_RSI'].mean() if 'Silver_RSI' in self.data.columns else 50,
        }
        
        return stats
    
    def generate_insights(self, stats):
        """Tạo insights từ dữ liệu"""
        insights = []
        
        # Trend analysis
        if stats['gold_vn_change_pct'] > 2:
            insights.append("• Giá vàng VN có xu hướng tăng mạnh trong kỳ báo cáo")
        elif stats['gold_vn_change_pct'] < -2:
            insights.append("• Giá vàng VN có xu hướng giảm trong kỳ báo cáo")
        else:
            insights.append("• Giá vàng VN tương đối ổn định trong kỳ báo cáo")
        
        if stats['silver_vn_change_pct'] > 5:
            insights.append("• Giá bạc VN biến động tăng mạnh so với đầu kỳ")
        elif stats['silver_vn_change_pct'] < -5:
            insights.append("• Giá bạc VN có xu hướng giảm đáng kể")
            
        # Correlation analysis
        if stats['correlation_silver_intl'] > 0.8:
            insights.append("• Giá bạc VN có tương quan mạnh với giá bạc quốc tế")
        elif stats['correlation_silver_intl'] > 0.5:
            insights.append("• Giá bạc VN có tương quan trung bình với thị trường quốc tế")
        else:
            insights.append("• Giá bạc VN ít bị ảnh hưởng bởi giá quốc tế")
            
        # Gold-Silver correlation analysis
        if stats['correlation_silver_gold'] > 0.8:
            insights.append("• Giá vàng và bạc VN có tương quan mạnh với nhau")
        elif stats['correlation_silver_gold'] > 0.5:
            insights.append("• Giá vàng và bạc VN có tương quan trung bình")
        else:
            insights.append("• Giá vàng và bạc VN có tương quan thấp")
            
        # Volatility analysis
        if stats.get('gold_volatility_avg', 0) > 50000:
            insights.append("• Thị trường vàng VN có độ biến động cao")
        else:
            insights.append("• Thị trường vàng VN tương đối ổn định")
            
        # Price ratio insights
        if stats['price_ratio_current'] > stats['price_ratio_avg'] * 1.1:
            insights.append("• Tỷ lệ giá vàng/bạc hiện tại cao hơn mức trung bình")
        elif stats['price_ratio_current'] < stats['price_ratio_avg'] * 0.9:
            insights.append("• Tỷ lệ giá vàng/bạc hiện tại thấp hơn mức trung bình")
            
        # RSI insights for Gold and Silver
        current_gold_rsi = stats.get('rsi_gold_current', 50)
        current_silver_rsi = stats.get('rsi_silver_current', 50)
        
        # Gold RSI analysis
        if current_gold_rsi > 70:
            insights.append("• RSI vàng VN hiện tại > 70, thị trường có thể đang mua quá mức")
        elif current_gold_rsi < 30:
            insights.append("• RSI vàng VN hiện tại < 30, thị trường có thể đang bán quá mức")
        elif current_gold_rsi > 50:
            insights.append("• RSI vàng VN cho thấy momentum tích cực")
        else:
            insights.append("• RSI vàng VN cho thấy momentum tiêu cực")
            
        # Silver RSI analysis
        if current_silver_rsi > 70:
            insights.append("• RSI bạc VN hiện tại > 70, thị trường có thể đang mua quá mức")
        elif current_silver_rsi < 30:
            insights.append("• RSI bạc VN hiện tại < 30, thị trường có thể đang bán quá mức")
        elif current_silver_rsi > 50:
            insights.append("• RSI bạc VN cho thấy momentum tích cực")
        else:
            insights.append("• RSI bạc VN cho thấy momentum tiêu cực")
            
        # RSI comparison insight
        rsi_diff = abs(current_gold_rsi - current_silver_rsi)
        if rsi_diff > 20:
            if current_gold_rsi > current_silver_rsi:
                insights.append(f"• RSI vàng cao hơn bạc {rsi_diff:.1f} điểm - vàng có momentum mạnh hơn")
            else:
                insights.append(f"• RSI bạc cao hơn vàng {rsi_diff:.1f} điểm - bạc có momentum mạnh hơn")
        else:
            insights.append(f"• RSI vàng và bạc gần tương đương (chênh {rsi_diff:.1f} điểm)")
            
        return insights
    
    def create_pdf_report(self, filename=None):
        """Tạo báo cáo PDF chuyên nghiệp với UTF-8"""
        if filename is None:
            filename = f"Bao_Cao_Gia_Vang_Bac_{self.report_date.strftime('%Y%m%d')}.pdf"
        
        print(f"📄 Đang tạo báo cáo PDF chuyên nghiệp: {filename}")
        
        # Thu thập dữ liệu
        if not self.collect_latest_data():
            print("❌ Không thể thu thập dữ liệu")
            return None
        
        # Tạo charts
        chart_files = self.create_time_series_charts()
        

        
        # Tính thống kê nâng cao
        stats = self.calculate_advanced_statistics()
        insights = self.generate_insights(stats)
        
        # Tạo PDF với encoding UTF-8
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                              leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles with UTF-8 support
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName=self.vietnamese_font
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.darkgreen,
            fontName=self.vietnamese_font
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.darkblue,
            fontName=self.vietnamese_font
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName=self.vietnamese_font
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leftIndent=20,
            bulletIndent=10,
            fontName=self.vietnamese_font
        )
        
        # Title page
        story.append(Paragraph("BÁO CÁO PHÂN TÍCH GIÁ VÀNG VÀ BẠC", title_style))
        story.append(Spacer(1, 40))
        
        # Executive Summary
        story.append(Paragraph("• TÓM TẮT ĐIỀU HÀNH", heading_style))
        story.append(Paragraph(f"Báo cáo này phân tích dữ liệu giá vàng và bạc trong khoảng thời gian "
                              f"{stats['total_days']} ngày từ {stats['period']}. "
                              f"Dữ liệu được thu thập từ các nguồn uy tín bao gồm TradingView, "
                              f"phuquygroup.vn và giabac.vn với tần suất cập nhật hàng ngày.", body_style))
        
        story.append(Spacer(1, 15))
        
        # Key metrics table
        summary_data = [
            ['Chỉ số', 'Giá trị hiện tại', 'Thay đổi (%)', 'Đơn vị'],
            ['Giá vàng VN', f"{stats['gold_vn_current']:,.0f}", 
             f"{stats['gold_vn_change_pct']:+.2f}%", 'VND/lượng'],
            ['Giá bạc VN', f"{stats['silver_vn_current']:,.0f}", 
             f"{stats['silver_vn_change_pct']:+.2f}%", 'VND/lượng'],
            ['Giá bạc quốc tế', f"${stats['silver_intl_current']:.2f}", 
             f"{stats['silver_intl_change_pct']:+.2f}%", 'USD/oz'],
            ['Chênh lệch vàng-bạc', f"{stats['difference_current']:,.0f}", 
             f"N/A", 'VND'],
            ['Tỷ lệ vàng/bạc', f"{stats['price_ratio_current']:.1f}", 
             f"N/A", 'lần'],
        ]
        
        summary_table = Table(summary_data, colWidths=[4*cm, 3.5*cm, 2.5*cm, 2.5*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.vietnamese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.darkblue),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(summary_table)
        story.append(PageBreak())
        
        # Time Series Charts - Bố trí 2 biểu đồ trên mỗi trang
        story.append(Paragraph("• PHÂN TÍCH TIME SERIES", heading_style))
        story.append(Paragraph("Các biểu đồ dưới đây hiển thị diễn biến giá theo thời gian với "
                              "đường moving average 7 ngày để làm mịn xu hướng và giảm nhiễu.", body_style))
        
        # Bố trí 2 biểu đồ trên mỗi trang
        for i, chart_file in enumerate(chart_files):
            if os.path.exists(chart_file):
                # PageBreak chỉ sau mỗi 2 biểu đồ (trừ biểu đồ đầu tiên)
                if i > 0 and i % 2 == 0:
                    story.append(PageBreak())
                
                # Space phù hợp cho layout 2 biểu đồ/trang
                if i % 2 == 0:  # Biểu đồ đầu tiên trong trang
                    story.append(Spacer(1, 15))
                else:  # Biểu đồ thứ hai trong trang
                    story.append(Spacer(1, 10))
                
                # Kích thước tối ưu cho 2 biểu đồ/trang: nhỏ hơn để vừa vặn
                img = Image(chart_file, width=14*cm, height=8.5*cm)
                story.append(img)
                
                # Space giữa 2 biểu đồ trong cùng trang
                if i % 2 == 0 and i < len(chart_files) - 1:  # Không phải biểu đồ cuối
                    story.append(Spacer(1, 8))
                else:
                    story.append(Spacer(1, 5))
        
        story.append(PageBreak())
        
        # Insights và Analysis
        story.append(Paragraph("• PHÂN TÍCH VÀ NHẬN XÉT", heading_style))
        
        story.append(Paragraph("Xu hướng và Biến động:", subheading_style))
        for insight in insights:
            story.append(Paragraph(insight, bullet_style))
        
        story.append(Spacer(1, 20))
        
        # Statistical Analysis
        story.append(Paragraph("Phân tích Thống kê Chi tiết:", subheading_style))
        
        stats_data = [
            ['Loại giá', 'Thấp nhất', 'Cao nhất', 'Trung bình', 'Độ lệch chuẩn'],
            ['Vàng VN (VND/lượng)', 
             f"{stats['gold_vn_min']:,.0f}", 
             f"{stats['gold_vn_max']:,.0f}", 
             f"{stats['gold_vn_avg']:,.0f}",
             f"{stats['gold_vn_std']:,.0f}"],
            ['Bạc VN (VND/lượng)', 
             f"{stats['silver_vn_min']:,.0f}", 
             f"{stats['silver_vn_max']:,.0f}", 
             f"{stats['silver_vn_avg']:,.0f}",
             f"{stats['silver_vn_std']:,.0f}"],
            ['Bạc Quốc tế (USD/oz)', 
             f"${stats['silver_intl_min']:.2f}", 
             f"${stats['silver_intl_max']:.2f}", 
             f"${stats['silver_intl_avg']:.2f}",
             f"${stats['silver_intl_std']:.2f}"],
        ]
        
        stats_table = Table(stats_data, colWidths=[3.2*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.vietnamese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Correlation analysis
        story.append(Paragraph("Phân tích Tương quan và RSI:", subheading_style))
        story.append(Paragraph(f"• Hệ số tương quan giữa giá bạc quốc tế và giá bạc VN: "
                              f"<b>{stats['correlation_silver_intl']:.3f}</b>", bullet_style))
        story.append(Paragraph(f"• Hệ số tương quan giữa giá bạc VN và giá vàng VN: "
                              f"<b>{stats['correlation_silver_gold']:.3f}</b>", bullet_style))
        story.append(Paragraph(f"• Tỷ lệ giá vàng/bạc VN trung bình: "
                              f"<b>{stats['price_ratio_avg']:.1f}</b> lần", bullet_style))
        story.append(Paragraph(f"• RSI vàng VN hiện tại: "
                              f"<b>{stats['rsi_gold_current']:.1f}</b> (Trung bình: {stats['rsi_gold_avg']:.1f})", bullet_style))
        story.append(Paragraph(f"• RSI bạc VN hiện tại: "
                              f"<b>{stats['rsi_silver_current']:.1f}</b> (Trung bình: {stats['rsi_silver_avg']:.1f})", bullet_style))
        
        
        
        story.append(PageBreak())
        
        # Raw Data Table
        story.append(Paragraph(" • DỮ LIỆU THÔ (RAW DATA)", heading_style))
        story.append(Paragraph("Bảng dữ liệu chi tiết 3 tháng gần nhất (90 ngày):", body_style))
        
        recent_data = self.data.tail(90)  # 3 tháng = 90 ngày
        table_data = [['Ngày', 'Vàng VN\n(VND/lượng)', 'Bạc VN\n(VND/lượng)', 
                      'Bạc Quốc tế\n(USD/oz)', 'Chênh lệch\n(VND)', 'Tỷ lệ\nVàng/Bạc']]
        
        for _, row in recent_data.iterrows():
            table_data.append([
                row['Date'].strftime('%d/%m/%Y'),
                f"{row['Gold Price VN']:,.0f}",
                f"{row['Silver Price VN']:,.0f}",
                f"${row['Silver Price International']:.2f}",
                f"{row['Difference']:,.0f}",
                f"{row['Price_Ratio']:.1f}"
            ])
        
        data_table = Table(table_data, colWidths=[2.2*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2*cm])
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.vietnamese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(data_table)
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(Paragraph(" Ghi chú:", subheading_style))
        story.append(Paragraph("• Dữ liệu được thu thập từ TradingView, phuquygroup.vn và giabac.vn", bullet_style))
        story.append(Paragraph("• Giá vàng và bạc VN tính theo VND/lượng (1 lượng = 37.5g)", bullet_style))
        story.append(Paragraph("• Báo cáo này chỉ mang tính chất tham khảo", bullet_style))
        story.append(Paragraph("• Các chỉ số kỹ thuật được tính toán dựa trên dữ liệu lịch sử", bullet_style))
        story.append(Paragraph("• Báo cáo được tạo tự động bởi hệ thống phân tích định lượng", bullet_style))
        story.append(Paragraph(f"• Thời gian tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", bullet_style))
        
        # Build PDF
        try:
            doc.build(story)
            print(f"✅ Đã tạo báo cáo PDF chuyên nghiệp: {filename}")
        except Exception as e:
            print(f"❌ Lỗi tạo PDF: {e}")
            return None
        
        # Cleanup temp charts
        for chart_file in chart_files:
            if os.path.exists(chart_file):
                os.remove(chart_file)
        
        return filename

# Main function để test
def main():
    """Test function"""
    generator = GoldSilverReportGenerator()
    pdf_file = generator.create_pdf_report()
    
    if pdf_file:
        print(f"🎉 Báo cáo PDF chuyên nghiệp đã được tạo: {pdf_file}")
        file_size = os.path.getsize(pdf_file) / 1024  # KB
        print(f"📊 Kích thước file: {file_size:.1f} KB")
    else:
        print("❌ Không thể tạo báo cáo PDF")

if __name__ == "__main__":
    main() 