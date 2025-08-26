#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script cho Webcam Data Crawler
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Chạy command và hiển thị kết quả"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Thành công")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Lỗi: {e}")
        if e.stderr:
            print(f"   Chi tiết: {e.stderr}")
        return False

def check_python_version():
    """Kiểm tra phiên bản Python"""
    print("🐍 Kiểm tra phiên bản Python...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python {version.major}.{version.minor} không được hỗ trợ")
        print("   Yêu cầu Python 3.7 trở lên")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True

def install_dependencies():
    """Cài đặt dependencies"""
    print("\n📦 Cài đặt dependencies...")
    
    # Upgrade pip
    if not run_command("pip install --upgrade pip", "Upgrade pip"):
        return False
        
    # Cài đặt requirements
    if not run_command("pip install -r requirements.txt", "Cài đặt requirements"):
        return False
        
    return True

def create_directories():
    """Tạo các thư mục cần thiết"""
    print("\n📁 Tạo thư mục cần thiết...")
    
    directories = ['screenshots', 'logs', 'data']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Đã tạo thư mục: {directory}")
        else:
            print(f"✅ Thư mục đã tồn tại: {directory}")
            
    return True

def test_installation():
    """Test cài đặt"""
    print("\n🧪 Test cài đặt...")
    
    try:
        # Test import các thư viện chính
        import requests
        import bs4
        import pandas
        import selenium
        from fake_useragent import UserAgent
        
        print("✅ Tất cả thư viện đã được cài đặt thành công")
        return True
        
    except ImportError as e:
        print(f"❌ Lỗi import: {e}")
        return False

def main():
    """Hàm chính setup"""
    print("🚀 === SETUP WEBCAM DATA CRAWLER ===")
    
    # Kiểm tra Python version
    if not check_python_version():
        sys.exit(1)
        
    # Cài đặt dependencies
    if not install_dependencies():
        print("\n❌ Cài đặt dependencies thất bại")
        print("💡 Thử chạy: pip install -r requirements.txt")
        sys.exit(1)
        
    # Tạo thư mục
    if not create_directories():
        print("\n❌ Tạo thư mục thất bại")
        sys.exit(1)
        
    # Test cài đặt
    if not test_installation():
        print("\n❌ Test cài đặt thất bại")
        sys.exit(1)
        
    print("\n🎉 === SETUP HOÀN THÀNH THÀNH CÔNG! ===")
    print("\n📚 Hướng dẫn sử dụng:")
    print("   1. Test tool: python test_crawler.py")
    print("   2. Chạy crawler: python run_crawler.py")
    print("   3. Xem help: python run_crawler.py --help")
    print("\n📖 Đọc README.md để biết thêm chi tiết")
    print("\n🚀 Tool đã sẵn sàng sử dụng!")

if __name__ == "__main__":
    main()
