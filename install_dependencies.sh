#!/bin/bash
# Comprehensive dependency installation script for Pinterest Factory
# This script installs all system dependencies needed for Playwright

echo "🚀 Pinterest Factory Dependency Installation"
echo "=========================================="

# Update package lists
echo "📦 Updating package lists..."
apt-get update

# Install system dependencies for Playwright
echo "📦 Installing Playwright system dependencies..."
apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libglib2.0-0 \
    libgtk-3-0 \
    libgconf-2-4 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0

# Install additional dependencies for image processing
echo "📦 Installing image processing dependencies..."
apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1

echo "✅ System dependencies installed successfully!"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "📦 Installing Playwright browsers..."
python -m playwright install chromium

# Verify installation
echo "🧪 Verifying Playwright installation..."
python -c "
from playwright.async_api import async_playwright
import asyncio

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        await browser.close()
        print(f'✅ Playwright test successful: {title}')

asyncio.run(test())
"

echo "🎉 All dependencies installed successfully!"
echo "Pinterest Factory is ready to use Playwright scraping."
