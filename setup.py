#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for Webcam Data Crawler
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run command and display result"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Error: {e}")
        if e.stderr:
            print(f"   Details: {e.stderr}")
        return False

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   Requires Python 3.7 or higher")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True

def install_dependencies():
    """Install dependencies"""
    print("\n📦 Installing dependencies...")
    
    # Upgrade pip
    if not run_command("pip install --upgrade pip", "Upgrade pip"):
        return False
        
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Install requirements"):
        return False
        
    return True

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating necessary directories...")
    
    directories = ['screenshots', 'logs', 'data']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✅ Directory already exists: {directory}")
            
    return True

def test_installation():
    """Test installation"""
    print("\n🧪 Testing installation...")
    
    try:
        # Test import of main libraries
        import requests
        import bs4
        import pandas
        import selenium
        from fake_useragent import UserAgent
        
        print("✅ All libraries installed successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 === SETUP WEBCAM DATA CRAWLER ===")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
        
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Installing dependencies failed")
        print("💡 Try: pip install -r requirements.txt")
        sys.exit(1)
        
    # Create directories
    if not create_directories():
        print("\n❌ Creating directories failed")
        sys.exit(1)
        
    # Test installation
    if not test_installation():
        print("\n❌ Installation test failed")
        sys.exit(1)
        
    print("\n🎉 === SETUP COMPLETED SUCCESSFULLY! ===")
    print("\n📚 Usage:")
    print("   1. Test tool: python test_crawler.py")
    print("   2. Run crawler: python run_crawler.py")
    print("   3. Help: python run_crawler.py --help")
    print("\n📖 Read README.md for more details")
    print("\n🚀 The tool is ready to use!")

if __name__ == "__main__":
    main()
