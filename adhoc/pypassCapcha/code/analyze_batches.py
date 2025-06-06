#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔍 BATCH ANALYSIS TOOL
Phân tích kết quả crawl từ các batch files để monitor performance và detect blocking patterns
Expected: 9 batches per day (every hour from 10 AM to 6 PM)
"""

import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import glob
from collections import defaultdict
import json
from typing import List, Dict, Any

def analyze_batch_files(batches_dir="../batches"):
    """
    Phân tích tất cả batch files trong thư mục
    
    Args:
        batches_dir: Thư mục chứa batch files
    """
    
    if not os.path.exists(batches_dir):
        print(f"❌ Thư mục {batches_dir} không tồn tại!")
        return
    
    # Tìm tất cả file CSV trong thư mục batches
    batch_files = glob.glob(os.path.join(batches_dir, "batch_*.csv"))
    
    if not batch_files:
        print(f"❌ Không tìm thấy batch files trong {batches_dir}")
        return
    
    print(f"🔍 ANALYZING {len(batch_files)} BATCH FILES")
    print("=" * 60)
    
    all_data = []
    batch_stats = []
    
    # Đọc từng batch file
    for batch_file in sorted(batch_files):
        print(f"📖 Reading {os.path.basename(batch_file)}...")
        
        try:
            df = pd.read_csv(batch_file, encoding='utf-8-sig')
            
            if not df.empty:
                # Extract batch info
                batch_id = df['batch_id'].iloc[0] if 'batch_id' in df.columns else os.path.basename(batch_file).replace('.csv', '')
                
                # Parse timestamp từ batch_id hoặc filename
                if 'batch_' in batch_id:
                    timestamp_str = batch_id.replace('batch_', '')
                    try:
                        batch_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    except:
                        batch_time = datetime.now()
                else:
                    batch_time = datetime.now()
                
                # Thống kê batch
                stats = {
                    'batch_id': batch_id,
                    'batch_time': batch_time,
                    'total_articles': len(df),
                    'unique_keywords': df['keyword'].nunique() if 'keyword' in df.columns else 0,
                    'unique_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
                    'avg_articles_per_keyword': len(df) / df['keyword'].nunique() if 'keyword' in df.columns and df['keyword'].nunique() > 0 else 0,
                    'file_path': batch_file
                }
                
                batch_stats.append(stats)
                all_data.append(df)
                
        except Exception as e:
            print(f"⚠️ Error reading {batch_file}: {e}")
            continue
    
    if not batch_stats:
        print("❌ Không có dữ liệu hợp lệ để phân tích!")
        return
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    
    # Tạo DataFrame thống kê
    stats_df = pd.DataFrame(batch_stats)
    
    # In tổng quan
    print_overview(stats_df, combined_df)
    
    # Phân tích timeline
    analyze_timeline(stats_df)
    
    # Phân tích keywords
    analyze_keywords(combined_df)
    
    # Phân tích domains
    analyze_domains(combined_df)
    
    # Detect potential blocking patterns
    detect_blocking_patterns(stats_df)
    
    # Export detailed report
    export_analysis_report(stats_df, combined_df)

def print_overview(stats_df, combined_df):
    """In tổng quan thống kê"""
    print("\n📊 OVERVIEW STATISTICS")
    print("=" * 50)
    
    total_batches = len(stats_df)
    total_articles = stats_df['total_articles'].sum()
    avg_articles_per_batch = stats_df['total_articles'].mean()
    
    print(f"📁 Total Batches: {total_batches}")
    print(f"📰 Total Articles: {total_articles:,}")
    print(f"📊 Avg Articles/Batch: {avg_articles_per_batch:.1f}")
    
    if not combined_df.empty and 'keyword' in combined_df.columns:
        total_keywords = combined_df['keyword'].nunique()
        print(f"🔍 Total Unique Keywords: {total_keywords}")
        
        if 'domain' in combined_df.columns:
            total_domains = combined_df['domain'].nunique()
            print(f"🌐 Total Unique Domains: {total_domains}")
    
    # Thời gian crawl
    if len(stats_df) > 1:
        first_batch = stats_df['batch_time'].min()
        last_batch = stats_df['batch_time'].max()
        duration = last_batch - first_batch
        
        print(f"⏰ First Batch: {first_batch.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ Last Batch: {last_batch.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ Total Duration: {str(duration).split('.')[0]}")

def analyze_timeline(stats_df):
    """Phân tích timeline performance"""
    print("\n📈 TIMELINE ANALYSIS")
    print("=" * 50)
    
    # Performance over time
    print("📊 Articles per batch over time:")
    for _, row in stats_df.iterrows():
        batch_time = row['batch_time'].strftime('%m-%d %H:%M')
        articles = row['total_articles']
        keywords = row['unique_keywords']
        avg_per_keyword = row['avg_articles_per_keyword']
        
        print(f"   {batch_time}: {articles:4d} articles ({keywords:2d} keywords, {avg_per_keyword:.1f} avg)")
    
    # Detect trends
    if len(stats_df) >= 3:
        recent_batches = stats_df.tail(3)['total_articles'].mean()
        early_batches = stats_df.head(3)['total_articles'].mean()
        
        trend = "📈 INCREASING" if recent_batches > early_batches else "📉 DECREASING" if recent_batches < early_batches else "➡️ STABLE"
        print(f"\n🎯 Performance Trend: {trend}")
        print(f"   Early batches avg: {early_batches:.1f}")
        print(f"   Recent batches avg: {recent_batches:.1f}")

def analyze_keywords(combined_df):
    """Phân tích keywords performance"""
    print("\n🔍 KEYWORD ANALYSIS")
    print("=" * 50)
    
    if combined_df.empty or 'keyword' not in combined_df.columns:
        print("❌ No keyword data available")
        return
    
    # Top keywords by article count
    keyword_counts = combined_df['keyword'].value_counts()
    print("📊 Top 10 keywords by article count:")
    for i, (keyword, count) in enumerate(keyword_counts.head(10).items(), 1):
        print(f"   {i:2d}. {keyword:<30} {count:4d} articles")
    
    # Keywords with consistently low results (potential blocking)
    keyword_avg = combined_df.groupby('keyword').size()
    low_performance_keywords = keyword_avg[keyword_avg < 5].index.tolist()
    
    if low_performance_keywords:
        print(f"\n⚠️ Keywords with low performance (<5 articles avg):")
        for kw in low_performance_keywords[:10]:
            count = keyword_avg[kw]
            print(f"   • {kw:<30} {count} articles")

def analyze_domains(combined_df):
    """Phân tích domains"""
    print("\n🌐 DOMAIN ANALYSIS")
    print("=" * 50)
    
    if combined_df.empty or 'domain' not in combined_df.columns:
        print("❌ No domain data available")
        return
    
    # Top domains
    domain_counts = combined_df['domain'].value_counts()
    print("📊 Top 10 domains:")
    for i, (domain, count) in enumerate(domain_counts.head(10).items(), 1):
        print(f"   {i:2d}. {domain:<40} {count:4d} articles")
    
    # Domain diversity
    total_articles = len(combined_df)
    unique_domains = combined_df['domain'].nunique()
    diversity_score = unique_domains / total_articles * 100
    
    print(f"\n📈 Domain Diversity: {diversity_score:.2f}% ({unique_domains} unique domains in {total_articles} articles)")

def detect_blocking_patterns(stats_df):
    """Detect potential blocking patterns"""
    print("\n🚨 BLOCKING PATTERN DETECTION")
    print("=" * 50)
    
    if len(stats_df) < 3:
        print("⚠️ Need at least 3 batches to detect patterns")
        return
    
    # Check for sudden drops
    article_counts = stats_df['total_articles'].tolist()
    avg_articles = stats_df['total_articles'].mean()
    std_articles = stats_df['total_articles'].std()
    
    anomalies = []
    for i, (_, row) in enumerate(stats_df.iterrows()):
        articles = row['total_articles']
        if articles < (avg_articles - 2 * std_articles):  # 2 standard deviations below mean
            anomalies.append({
                'batch_id': row['batch_id'],
                'batch_time': row['batch_time'],
                'articles': articles,
                'expected': avg_articles
            })
    
    if anomalies:
        print("🚨 POTENTIAL BLOCKING DETECTED:")
        for anomaly in anomalies:
            time_str = anomaly['batch_time'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"   • {time_str}: Only {anomaly['articles']} articles (expected ~{anomaly['expected']:.0f})")
    else:
        print("✅ No obvious blocking patterns detected")
    
    # Check success rate consistency
    success_rates = []
    for _, row in stats_df.iterrows():
        expected_keywords = 60  # Assuming 60 keywords
        actual_keywords = row['unique_keywords']
        success_rate = (actual_keywords / expected_keywords) * 100 if expected_keywords > 0 else 0
        success_rates.append(success_rate)
    
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    print(f"\n📈 Average Success Rate: {avg_success_rate:.1f}%")
    
    if avg_success_rate < 80:
        print("⚠️ Low success rate detected - possible blocking or rate limiting")
    elif avg_success_rate > 95:
        print("✅ Excellent success rate - no blocking detected")

def export_analysis_report(stats_df, combined_df):
    """Export detailed analysis report"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"../reports/batch_analysis_report_{timestamp}.json"
    
    # Tạo report data
    report = {
        'analysis_timestamp': datetime.now().isoformat(),
        'summary': {
            'total_batches': len(stats_df),
            'total_articles': int(stats_df['total_articles'].sum()),
            'avg_articles_per_batch': float(stats_df['total_articles'].mean()),
            'unique_keywords': int(combined_df['keyword'].nunique()) if not combined_df.empty and 'keyword' in combined_df.columns else 0,
            'unique_domains': int(combined_df['domain'].nunique()) if not combined_df.empty and 'domain' in combined_df.columns else 0
        },
        'batch_details': stats_df.to_dict('records'),
        'performance_trend': 'stable'  # Could be enhanced with actual trend calculation
    }
    
    # Convert datetime objects to strings for JSON serialization
    for batch in report['batch_details']:
        if 'batch_time' in batch:
            batch['batch_time'] = batch['batch_time'].isoformat()
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Analysis report exported to: {report_file}")

def main():
    """Main function"""
    print("🔍 GOOGLE NEWS BATCH ANALYZER")
    print("=" * 50)
    
    # Kiểm tra xem có batch files không
    if not os.path.exists("../batches"):
        print("❌ Thư mục 'batches' không tồn tại!")
        print("💡 Chạy crawler trước để tạo batch data")
        return
    
    batch_files = glob.glob("../batches/batch_*.csv")
    if not batch_files:
        print("❌ Không tìm thấy batch files!")
        print("💡 Chạy crawler trước để tạo batch data")
        return
    
    print(f"📁 Found {len(batch_files)} batch files")
    print("🚀 Starting analysis...\n")
    
    analyze_batch_files()
    
    print("\n🎉 Analysis completed!")
    print("💡 Check the generated report file for detailed results")

if __name__ == "__main__":
    main()