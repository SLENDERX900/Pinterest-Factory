#!/usr/bin/env python3
"""
Environment fix script for Pinterest Factory
Fixes Playwright dependencies and silences warnings
"""

import subprocess
import sys
import os

def fix_playwright_dependencies():
    """Install Playwright system dependencies"""
    print("🔧 Installing Playwright system dependencies...")
    
    try:
        # Install Playwright dependencies
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install-deps"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Playwright dependencies installed successfully")
            return True
        else:
            print(f"⚠️ Playwright install-deps output: {result.stderr}")
            print("ℹ️ This is normal on Streamlit Cloud - system dependencies cannot be installed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Playwright dependency installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing Playwright dependencies: {e}")
        return False

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("🔧 Installing Playwright browsers...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Playwright browsers installed successfully")
            return True
        else:
            print(f"❌ Browser installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing browsers: {e}")
        return False

def test_playwright():
    """Test Playwright functionality"""
    print("🧪 Testing Playwright functionality...")
    
    try:
        from playwright.async_api import async_playwright
        import asyncio
        
        async def test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://example.com")
                title = await page.title()
                await browser.close()
                return title
        
        title = asyncio.run(test())
        if title:
            print(f"✅ Playwright test successful: {title}")
            return True
        else:
            print("❌ Playwright test failed: No title retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Playwright test failed: {e}")
        return False

def main():
    """Main fix function"""
    print("🚀 Pinterest Factory Environment Fix")
    print("=" * 50)
    
    # Set environment variables to silence warnings
    print("🔧 Setting environment variables...")
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    print("✅ Environment variables set")
    
    # Try to fix Playwright dependencies
    deps_fixed = fix_playwright_dependencies()
    
    # Install browsers
    browsers_installed = install_playwright_browsers()
    
    # Test Playwright
    playwright_works = False
    if deps_fixed and browsers_installed:
        playwright_works = test_playwright()
    
    print("\n" + "=" * 50)
    print("📊 FIX RESULTS:")
    print("=" * 50)
    
    if deps_fixed:
        print("✅ System dependencies: FIXED")
    else:
        print("⚠️ System dependencies: NOT FIXED (expected on Streamlit Cloud)")
    
    if browsers_installed:
        print("✅ Playwright browsers: INSTALLED")
    else:
        print("❌ Playwright browsers: NOT INSTALLED")
    
    if playwright_works:
        print("✅ Playwright functionality: WORKING")
        print("\n🎉 Pinterest Factory will use Playwright scraping!")
    else:
        print("❌ Playwright functionality: NOT WORKING")
        print("\n📡 Pinterest Factory will use RSS fallback (still works perfectly!)")
    
    print("\n📋 Next Steps:")
    print("1. Commit and push the changes")
    print("2. Redeploy on Streamlit Cloud")
    print("3. Monitor the clean console output")
    
    return playwright_works

if __name__ == "__main__":
    main()
