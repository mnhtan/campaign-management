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
        """Thu thập dữ liệu từ CSV file mới nhất được tạo bởi final_gold_silver_table_with_real_data.py"""
        print(f"📊 Đang thu thập dữ liệu từ CSV file mới nhất...")
        
        try:
            # Tìm file CSV mới nhất với pattern trong thư mục data
            import glob
            csv_pattern = "../data/gold_silver_completely_real_data_*.csv"
            csv_files = glob.glob(csv_pattern)
            
            # Nếu không tìm thấy trong data, thử tìm trong thư mục code hiện tại
            if not csv_files:
                csv_pattern = "gold_silver_completely_real_data_*.csv"
                csv_files = glob.glob(csv_pattern)
            
            # Thử tìm trong thư mục cha
            if not csv_files:
                csv_pattern = "../gold_silver_completely_real_data_*.csv"
                csv_files = glob.glob(csv_pattern)
            
            if not csv_files:
                print(f"❌ Không tìm thấy file CSV trong data/, code/ hoặc thư mục cha")
                print("💡 Hãy chạy final_gold_silver_table_with_real_data.py trước để tạo dữ liệu")
                return False
            
            # Lấy file mới nhất
            latest_csv = max(csv_files, key=os.path.getctime)
            print(f"📄 Đang đọc dữ liệu từ: {latest_csv}")
            
            # Đọc CSV file
            final_data = pd.read_csv(latest_csv)
            final_data['Date'] = pd.to_datetime(final_data['Date'])
            
            print(f"✅ Đọc thành công {len(final_data)} dòng dữ liệu từ CSV")
            print(f"📅 Thời gian: {final_data['Date'].min().strftime('%Y-%m-%d')} đến {final_data['Date'].max().strftime('%Y-%m-%d')}")
            
            # Kiểm tra columns có trong CSV
            expected_columns = ['Date', 'Gold Price VN', 'Silver Price VN', 'Silver Price International', 'RSI Index', 'Correlation Value']
            missing_columns = [col for col in expected_columns if col not in final_data.columns]
            
            if missing_columns:
                print(f"⚠️ Thiếu columns: {missing_columns}")
                print(f"📋 Columns hiện có: {list(final_data.columns)}")
            
            # Tính các chỉ số bổ sung cần thiết cho charts (từ dữ liệu CSV)
            final_data = self._calculate_additional_indicators(final_data)
            
            # Giới hạn số ngày nếu cần
            if len(final_data) > days:
                final_data = final_data.tail(days).reset_index(drop=True)
                print(f"📝 Giới hạn dữ liệu xuống {days} ngày gần nhất")
            
            self.data = final_data
            return True
                
        except Exception as e:
            print(f"❌ Lỗi khi đọc dữ liệu từ CSV: {e}")
            print("💡 Hãy chạy final_gold_silver_table_with_real_data.py để tạo dữ liệu mới")
            
        return False
    
    def _calculate_additional_indicators(self, df):
        """Tính các chỉ số bổ sung từ dữ liệu CSV"""
        # Moving averages (7 ngày) - sử dụng column names mới từ CSV
        df['Gold_MA7'] = df['Gold Price VN'].rolling(window=7).mean()
        df['Silver_VN_MA7'] = df['Silver Price VN'].rolling(window=7).mean()
        df['Silver_Intl_MA7'] = df['Silver Price International'].rolling(window=7).mean()
        
        # Volatility (rolling standard deviation)
        df['Gold_Volatility'] = df['Gold Price VN'].rolling(window=7).std()
        df['Silver_VN_Volatility'] = df['Silver Price VN'].rolling(window=7).std()
        
        # Price ratio
        df['Price_Ratio'] = df['Gold Price VN'] / df['Silver Price VN']
        
        # Sử dụng RSI từ CSV (RSI Index) cho vàng và tính RSI cho bạc
        if 'RSI Index' in df.columns:
            df['Gold_RSI'] = df['RSI Index']
        else:
            df['Gold_RSI'] = self._calculate_rsi(df['Gold Price VN'], period=14)
            
        # Tính RSI cho bạc (Silver)
        df['Silver_RSI'] = self._calculate_rsi(df['Silver Price VN'], period=14)
        
        # Tính Difference 
        df['Difference'] = df['Gold Price VN'] - df['Silver Price VN']
        
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """Tính RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def create_price_ratio_chart(self):
        """Tạo biểu đồ tỷ lệ giá vàng/bạc Việt Nam """
        if self.data is None or self.data.empty:
            return None
        
        # Thiết lập font cho charts
        self._setup_matplotlib_font()
        
        # Tạo figure lớn ngang bằng chữ với tỷ lệ cân đối
        fig, ax = plt.subplots(1, 1, figsize=(16, 9))
        
        # Vẽ đường tỷ lệ giá vàng/bạc - màu xanh lá 
        ax.plot(self.data['Date'], self.data['Price_Ratio'], 
                linewidth=3, color='#2E8B57', alpha=0.9, label='Tỷ lệ Giá Vàng/Bạc VN')
        
        # Tính và vẽ đường trung bình ngang - màu đỏ đứt nét 
        average_ratio = self.data['Price_Ratio'].mean()
        ax.axhline(y=average_ratio, color='red', linestyle='--', linewidth=2.5, 
                   alpha=0.8, label=f'Trung bình: {average_ratio:.1f}')
        
        # Thiết lập tiêu đề
        ax.set_title('Thời gian\nTỷ lệ Giá Vàng/Bạc Việt Nam', 
                     fontsize=24, fontweight='bold', pad=30, loc='center')
        ax.set_xlabel('Thời gian', fontsize=16, fontweight='bold')
        ax.set_ylabel('Tỷ lệ', fontsize=16)
        
        # Format trục x 
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax.tick_params(axis='x', rotation=0, labelsize=14)  # Không xoay label x
        ax.tick_params(axis='y', labelsize=14)
        
        # Thiết lập giới hạn 
        ax.set_ylim(8.0, 9.6)
        
        # Thiết lập grid nhẹ
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Legend 
        ax.legend(loc='upper right', fontsize=14, frameon=True, 
                 fancybox=True, shadow=True, framealpha=0.9)
        
        # Điều chỉnh layout 
        plt.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.12)
        
        # Lưu chart
        chart_file = os.path.join(self.charts_dir, 'price_ratio_chart.png')
        plt.savefig(chart_file, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        
        return chart_file
    
    def create_time_series_charts(self):
        """Tạo các time series charts chi tiết"""
        if self.data is None or self.data.empty:
            return []

        # Thiết lập font cho charts
        self._setup_matplotlib_font()

        chart_files = []

        # Chart 1a: Giá vàng và bạc VN
        fig1, ax1 = plt.subplots(1, 1, figsize=(16, 8))
        
        ax1.plot(self.data['Date'], self.data['Gold Price VN'], 
                label='Giá Vàng VN', linewidth=3, color='gold', alpha=0.8)
        ax1.plot(self.data['Date'], self.data['Gold_MA7'], 
                label='MA7 Vàng', linewidth=2, color='orange', linestyle='--', alpha=0.7)

        ax1_twin = ax1.twinx()
        ax1_twin.plot(self.data['Date'], self.data['Silver Price VN'], 
                     label='Giá Bạc VN', linewidth=3, color='silver', alpha=0.8)
        ax1_twin.plot(self.data['Date'], self.data['Silver_VN_MA7'], 
                     label='MA7 Bạc VN', linewidth=2, color='gray', linestyle='--', alpha=0.7)

        ax1.set_title('Biểu đồ Time Series - Giá Vàng và Bạc Việt Nam', 
                     fontsize=20, fontweight='bold', pad=25)
        ax1.set_xlabel('Thời gian', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Giá Vàng (VND/lượng)', fontsize=14, color='darkgoldenrod')
        ax1_twin.set_ylabel('Giá Bạc (VND/lượng)', fontsize=14, color='dimgray')

        # Format axes
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax1.tick_params(axis='x', rotation=45, labelsize=12)
        ax1.tick_params(axis='y', labelsize=12)
        ax1_twin.tick_params(axis='y', labelsize=12)

        # Format y-axis
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
        ax1_twin.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))

        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=12)
        ax1_twin.legend(loc='upper right', fontsize=12)

        plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.15)

        chart_file1a = os.path.join(self.charts_dir, 'gold_silver_vn.png')
        plt.savefig(chart_file1a, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file1a)

        # Chart 1b: Giá bạc quốc tế và chênh lệch
        fig2, ax2 = plt.subplots(1, 1, figsize=(16, 8))
        
        ax2.plot(self.data['Date'], self.data['Silver Price International'], 
                label='Giá Bạc Quốc Tế (USD/oz)', linewidth=3, color='blue', alpha=0.8)
        ax2.plot(self.data['Date'], self.data['Silver_Intl_MA7'], 
                label='MA7 Bạc Quốc Tế', linewidth=2, color='navy', linestyle='--', alpha=0.7)

        ax2_twin = ax2.twinx()
        ax2_twin.plot(self.data['Date'], self.data['Difference'], 
                     label='Chênh lệch Vàng-Bạc VN', linewidth=2.5, color='red', alpha=0.8)

        ax2.set_title('Giá Bạc Quốc Tế và Chênh Lệch Giá Trong Nước', 
                     fontsize=20, fontweight='bold', pad=25)
        ax2.set_xlabel('Thời gian', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Giá Bạc Quốc Tế (USD/oz)', fontsize=14, color='blue')
        ax2_twin.set_ylabel('Chênh lệch (VND)', fontsize=14, color='red')

        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax2.tick_params(axis='x', rotation=45, labelsize=12)
        ax2.tick_params(axis='y', labelsize=12)
        ax2_twin.tick_params(axis='y', labelsize=12)
        ax2_twin.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))

        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left', fontsize=12)
        ax2_twin.legend(loc='upper right', fontsize=12)

        plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.15)

        chart_file1b = os.path.join(self.charts_dir, 'silver_intl_difference.png')
        plt.savefig(chart_file1b, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file1b)

        # Chart 1c: Price Ratio Chart - Tỷ lệ giá vàng/bạc VN
        fig3, ax3 = plt.subplots(1, 1, figsize=(16, 8))
        
        ax3.plot(self.data['Date'], self.data['Price_Ratio'], 
                linewidth=3, color='#2E8B57', alpha=0.9, label='Tỷ lệ Giá Vàng/Bạc VN')

        average_ratio = self.data['Price_Ratio'].mean()
        ax3.axhline(y=average_ratio, color='red', linestyle='--', linewidth=2.5, 
                   alpha=0.8, label=f'Trung bình: {average_ratio:.1f}')

        ax3.set_title('Tỷ lệ Giá Vàng/Bạc Việt Nam', 
                     fontsize=20, fontweight='bold', pad=25)
        ax3.set_xlabel('Thời gian', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Tỷ lệ', fontsize=14)

        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax3.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax3.tick_params(axis='x', rotation=45, labelsize=12)
        ax3.tick_params(axis='y', labelsize=12)

        ax3.set_ylim(8.0, 9.6)
        ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax3.legend(loc='upper right', fontsize=12, frameon=True, 
                 fancybox=True, shadow=True, framealpha=0.9)

        plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.15)

        chart_file1c = os.path.join(self.charts_dir, 'price_ratio.png')
        plt.savefig(chart_file1c, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file1c)

        # Chart 2: RSI Time Series Comparison
        # Kích thước lớn ngang bằng chữ với tỷ lệ cân đối
        fig, ax = plt.subplots(1, 1, figsize=(16, 9))
        
        # Plot RSI lines
        ax.plot(self.data['Date'], self.data['Gold_RSI'], 
                label='RSI Vàng VN', linewidth=3, color='gold', alpha=0.9)
        ax.plot(self.data['Date'], self.data['Silver_RSI'], 
                label='RSI Bạc VN', linewidth=3, color='silver', alpha=0.9)
        
        # Thêm các đường mức quan trọng
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label='Mua quá mức (70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='Bán quá mức (30)')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.5, linewidth=1, label='Trung tính (50)')
        
        # Tô màu các vùng
        ax.fill_between(self.data['Date'], 70, 100, alpha=0.15, color='red', label='Vùng mua quá mức')
        ax.fill_between(self.data['Date'], 0, 30, alpha=0.15, color='green', label='Vùng bán quá mức')
        ax.fill_between(self.data['Date'], 30, 70, alpha=0.08, color='gray', label='Vùng trung tính')
        
        ax.set_title(' So Sánh Chỉ Số RSI - Vàng và Bạc Việt Nam (14 ngày)', 
                     fontsize=22, fontweight='bold', pad=25)
        ax.set_xlabel('Thời gian', fontsize=16, fontweight='bold')
        ax.set_ylabel('RSI', fontsize=16, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=14)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        ax.tick_params(axis='x', rotation=45, labelsize=14)
        ax.tick_params(axis='y', labelsize=14)
        
        # Thêm text box với thống kê hiện tại
        current_gold_rsi = self.data['Gold_RSI'].iloc[-1]
        current_silver_rsi = self.data['Silver_RSI'].iloc[-1]
        rsi_diff = abs(current_gold_rsi - current_silver_rsi)
        
        # Margins tối ưu cho layout 2 biểu đồ/trang
        plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15)
        
        chart_file2 = os.path.join(self.charts_dir, 'rsi_time_series.png')
        plt.savefig(chart_file2, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file2)
        
        # Chart 3 & 4: Phân Phối và Tương Quan - 2 subplot cạnh nhau
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Chart 3: Phân Phối Giá Bạc VN (bên trái)
        n, bins, patches = ax1.hist(self.data['Silver Price VN'], bins=20, alpha=0.75, 
                                   color='silver', edgecolor='black', linewidth=1.2)
        
        # Đường trung bình và trung vị
        mean_val = self.data['Silver Price VN'].mean()
        median_val = self.data['Silver Price VN'].median()
        
        ax1.axvline(mean_val, color='red', linestyle='--', linewidth=2.5,
                   label=f'TB: {mean_val:,.0f}', alpha=0.9)
        ax1.axvline(median_val, color='orange', linestyle=':', linewidth=2.5,
                   label=f'Trung vị: {median_val:,.0f}', alpha=0.9)
        
        # Styling cho chart 3
        ax1.set_title('Phân Phối Giá Bạc VN', fontsize=18, fontweight='bold', pad=20)
        ax1.set_xlabel('Giá (VND/lượng)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Tần suất', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=12, loc='upper left', frameon=True, fancybox=True, shadow=True)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='x', labelsize=11)
        ax1.tick_params(axis='y', labelsize=11)
        
        # Chart 4: Tương Quan Bạc VN vs Vàng VN (bên phải)
        scatter = ax2.scatter(self.data['Silver Price VN'], self.data['Gold Price VN'], 
                   alpha=0.65, color='blue', s=40, edgecolors='navy', linewidth=0.8)
        
        # Highlight điểm mới nhất
        latest_silver = self.data['Silver Price VN'].iloc[-1]
        latest_gold = self.data['Gold Price VN'].iloc[-1]
        ax2.scatter(latest_silver, latest_gold, color='red', s=180, alpha=0.95, 
                   edgecolors='darkred', linewidth=3, label='Ngày mới nhất', zorder=10,
                   marker='o')
        
        # Đường trend
        z = np.polyfit(self.data['Silver Price VN'], self.data['Gold Price VN'], 1)
        p = np.poly1d(z)
        ax2.plot(self.data['Silver Price VN'], p(self.data['Silver Price VN']), 
                "r--", alpha=0.85, linewidth=2.5, label='Đường xu hướng')
        
        # Styling cho chart 4
        corr = self.data['Silver Price VN'].corr(self.data['Gold Price VN'])
        ax2.set_title(f'Tương Quan Bạc VN vs Vàng VN\n(r = {corr:.3f})', 
                     fontsize=18, fontweight='bold', pad=20)
        ax2.set_xlabel('Giá Bạc VN (VND/lượng)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Giá Vàng VN (VND/lượng)', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=12, loc='upper left', frameon=True, fancybox=True, shadow=True)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='x', labelsize=11)
        ax2.tick_params(axis='y', labelsize=11)
        
        # Thêm thống kê tóm tắt
        min_val = self.data['Silver Price VN'].min()
        max_val = self.data['Silver Price VN'].max()
        std_val = self.data['Silver Price VN'].std()
        
        # Text box thống kê cho chart 3
        stats_text = f'Min: {min_val:,.0f}\nMax: {max_val:,.0f}\nStd: {std_val:,.0f}'
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Text box thống kê cho chart 4
        corr_strength = "Rất mạnh" if abs(corr) > 0.8 else "Mạnh" if abs(corr) > 0.6 else "Trung bình" if abs(corr) > 0.4 else "Yếu"
        corr_direction = "Thuận chiều" if corr > 0 else "Nghịch chiều"
        corr_text = f'Mức độ: {corr_strength}\nHướng: {corr_direction}'
        ax2.text(0.02, 0.98, corr_text, transform=ax2.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # Điều chỉnh spacing giữa 2 subplots
        plt.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.12, wspace=0.25)
        
        chart_file_combined = os.path.join(self.charts_dir, 'distribution_correlation_combined.png')
        plt.savefig(chart_file_combined, dpi=300, pad_inches=0.1, facecolor='white')
        plt.close()
        chart_files.append(chart_file_combined)

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
        
        # Tạo PDF với encoding UTF-8 và margins gọn gàng
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                              leftMargin=1.5*cm, rightMargin=1.5*cm,
                              topMargin=1.5*cm, bottomMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles with UTF-8 support
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName=self.vietnamese_font
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=8,
            spaceBefore=10,
            textColor=colors.darkgreen,
            fontName=self.vietnamese_font
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=5,
            spaceBefore=8,
            textColor=colors.darkblue,
            fontName=self.vietnamese_font
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=3,
            alignment=TA_JUSTIFY,
            fontName=self.vietnamese_font
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=3,
            leftIndent=20,
            bulletIndent=10,
            fontName=self.vietnamese_font
        )
        
        # Title page
        story.append(Paragraph("BÁO CÁO PHÂN TÍCH GIÁ VÀNG VÀ BẠC", title_style))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("• TÓM TẮT ĐIỀU HÀNH", heading_style))
        story.append(Paragraph(f"Báo cáo này phân tích dữ liệu giá vàng và bạc trong khoảng thời gian "
                              f"{stats['total_days']} ngày từ {stats['period']}. "
                              f"Dữ liệu được thu thập từ các nguồn uy tín bao gồm TradingView, "
                              f"phuquygroup.vn và giabac.vn với tần suất cập nhật hàng ngày.", body_style))
        
        story.append(Spacer(1, 8))
        
        # Key metrics table
        summary_data = [
            ['Chỉ số', 'Giá trị hiện tại', 'Thay đổi (%)', 'Đơn vị'],
            ['Giá vàng VN', f"{stats['gold_vn_current']:,.0f}", 
             f"{stats['gold_vn_change_pct']:+.2f}%", 'VND/lượng'],
            ['Giá bạc VN', f"{stats['silver_vn_current']:,.0f}", 
             f"{stats['silver_vn_change_pct']:+.2f}%", 'VND/lượng'],
            ['Giá bạc quốc tế', f"${stats['silver_intl_current']:.2f}", 
             f"{stats['silver_intl_change_pct']:+.2f}%", 'USD/oz'],
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
        story.append(Spacer(1, 10))
        
        # Trang 1: 3 chart tách riêng (1a, 1b, 1c), Trang 2: RSI + Chart gộp (phân phối + tương quan)
        for i, chart_file in enumerate(chart_files):
            if os.path.exists(chart_file):
                # PageBreak sau 3 charts đầu tiên (3 chart tách riêng)
                if i == 3:
                    story.append(PageBreak())
                
                # Space trước chart
                if i == 0 or i == 3:  # Chart đầu tiên trong mỗi trang
                    story.append(Spacer(1, 5))
                else:  # Các charts khác
                    story.append(Spacer(1, 3))
                
                # Kích thước điều chỉnh theo layout trang
                if i < 3:  # 3 charts đầu (1a, 1b, 1c) - cách đều trong 1 trang
                    img = Image(chart_file, width=17*cm, height=6.5*cm)
                elif i == 3:  # Chart 4: RSI (chữ nhật)
                    img = Image(chart_file, width=17*cm, height=8*cm)
                else:  # Chart 5: Phân phối + tương quan gộp (chữ nhật rộng)
                    img = Image(chart_file, width=18*cm, height=9*cm)
                story.append(img)
                
                # Space sau chart
                if i < 2:  # 2 charts đầu trong nhóm 3
                    story.append(Spacer(1, 3))  # Space nhỏ giữa 3 charts
                elif i == 2:  # Chart thứ 3 cuối trang 1
                    story.append(Spacer(1, 2))  # Space cuối trang 1
                elif i == 3:  # Chart RSI trang 2
                    story.append(Spacer(1, 4))  # Space sau chart RSI
                else:  # Chart gộp cuối cùng
                    story.append(Spacer(1, 2))
        
        story.append(PageBreak())
        
        
        # Raw Data Table
        story.append(Paragraph(" • DỮ LIỆU THÔ (RAW DATA)", heading_style))
        story.append(Paragraph("Bảng dữ liệu chi tiết 3 tháng gần nhất (90 ngày):", body_style))
        
        recent_data = self.data.tail(90)  # 3 tháng = 90 ngày
        table_data = [['Ngày', 'Vàng VN\n(VND/lượng)', 'Bạc VN\n(VND/lượng)', 
                      'Bạc Quốc tế\n(USD/oz)', 'RSI\nVàng', 'Correlation\nValue', 'Tỷ lệ\nVàng/Bạc']]
        
        for _, row in recent_data.iterrows():
            table_data.append([
                row['Date'].strftime('%d/%m/%Y'),
                f"{row['Gold Price VN']:,.0f}",
                f"{row['Silver Price VN']:,.0f}",
                f"${row['Silver Price International']:.2f}",
                f"{row.get('Gold_RSI', 0):.1f}" if pd.notna(row.get('Gold_RSI', 0)) else "N/A",
                f"{row.get('Correlation Value', 0):.3f}" if pd.notna(row.get('Correlation Value', 0)) else "N/A",
                f"{row['Price_Ratio']:.1f}"
            ])
        
        data_table = Table(table_data, colWidths=[2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 1.8*cm, 2*cm, 1.8*cm])
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
        story.append(Spacer(1, 15))
        
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
    try:
        pdf_file = generator.create_pdf_report()
        
        if pdf_file:
            print(f"🎉 Báo cáo PDF chuyên nghiệp đã được tạo: {pdf_file}")
            file_size = os.path.getsize(pdf_file) / 1024  # KB
            print(f"📊 Kích thước file: {file_size:.1f} KB")
        else:
            print("❌ Không thể tạo báo cáo PDF")
    except Exception as e:
        print(f"❌ Lỗi khi tạo báo cáo PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 