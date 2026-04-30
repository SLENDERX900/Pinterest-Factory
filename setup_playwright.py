#!/usr/bin/env python3
"""
Playwright setup script for Pinterest Factory
Handles browser installation and system dependencies
"""

import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers with proper error handling"""
    print("🔧 Installing Playwright browsers...")
    
    try:
        # Install browsers
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Playwright browsers installed successfully")
            return True
        else:
            print(f"❌ Playwright installation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Playwright installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing Playwright: {e}")
        return False

def install_system_dependencies():
    """Attempt to install system dependencies if possible"""
    print("🔧 Checking system dependencies...")
    
    # Try to install system packages using apt (for Debian/Ubuntu based systems)
    try:
        # Common dependencies needed for Playwright
        packages = [
            "libnss3",
            "libatk-bridge2.0-0", 
            "libdrm2",
            "libxkbcommon0",
            "libxcomposite1",
            "libxdamage1",
            "libxrandr2",
            "libgbm1",
            "libxss1",
            "libasound2"
        ]
        
        # Try installing with apt (may not work in all environments)
        if os.path.exists("/usr/bin/apt"):
            print("📦 Installing system dependencies with apt...")
            cmd = ["sudo", "apt-get", "update"] + ["sudo", "apt-get", "install", "-y"] + packages
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ System dependencies installed")
                return True
            else:
                print(f"⚠️ System dependency installation failed: {result.stderr}")
                return False
        else:
            print("ℹ️ apt not available, skipping system dependency installation")
            return True
            
    except Exception as e:
        print(f"⚠️ Could not install system dependencies: {e}")
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
    """Main setup function"""
    print("🚀 Pinterest Factory Playwright Setup")
    print("=" * 50)
    
    success = True
    
    # Install system dependencies
    if not install_system_dependencies():
        print("⚠️ System dependencies may be missing, continuing...")
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        print("❌ Failed to install Playwright browsers")
        success = False
    
    # Test Playwright
    if success:
        if not test_playwright():
            print("❌ Playwright test failed")
            success = False
    
    if success:
        print("\n🎉 Playwright setup completed successfully!")
        print("Pinterest Factory is ready to use Playwright scraping.")
    else:
        print("\n❌ Playwright setup failed")
        print("The app will fall back to RSS scraping.")
    
    return success

if __name__ == "__main__":
    main()
