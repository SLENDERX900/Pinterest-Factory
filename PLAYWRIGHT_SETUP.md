# Playwright Setup for Pinterest Factory

This document provides comprehensive instructions for setting up Playwright to work properly with Pinterest Factory.

## Quick Setup

### For Local Development

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   python -m playwright install chromium
   ```

3. **Run the setup script:**
   ```bash
   python setup_playwright.py
   ```

### For Streamlit Cloud Deployment

Streamlit Cloud has limited system access, so we need to handle dependencies differently:

1. **Update requirements.txt** (already done):
   ```
   playwright>=1.52.0
   playwright[all]>=1.52.0
   ```

2. **The app will automatically attempt to install Playwright browsers** when first used

3. **If system dependencies are missing**, the app will fall back to RSS scraping

## System Dependencies

Playwright requires these system libraries:

### Core Dependencies
- `libnss3` - Network Security Services
- `libatk-bridge2.0-0` - Accessibility Toolkit Bridge
- `libdrm2` - Direct Rendering Manager
- `libxkbcommon0` - Keyboard handling
- `libxcomposite1` - X11 composite extension
- `libxdamage1` - X11 damage extension
- `libxrandr2` - X11 RandR extension
- `libgbm1` - Generic Buffer Manager
- `libxss1` - X11 screen saver extension
- `libasound2` - Audio library
- `libglib2.0-0` - GLib library (CRITICAL)
- `libgtk-3-0` - GTK+ library
- `libgconf-2-4` - GConf library
- `libpangocairo-1.0-0` - Pango Cairo
- `libatk1.0-0` - Accessibility Toolkit
- `libcairo-gobject2` - Cairo GObject
- `libgdk-pixbuf2.0-0` - GDK Pixbuf

### Image Processing Dependencies
- `libgl1-mesa-glx` - OpenGL library
- `libsm6` - X11 Session Management
- `libxext6` - X11 extension library
- `libxrender-dev` - X11 rendering
- `libgomp1` - OpenMP library

## Manual Installation (if needed)

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 \
    libasound2 libglib2.0-0 libgtk-3-0 libgconf-2-4 \
    libxrandr2 libasound2 libpangocairo-1.0-0 libatk1.0-0 \
    libcairo-gobject2 libgtk-3-0 libgdk-pixbuf2.0-0 \
    libgl1-mesa-glx libsm6 libxext6 libxrender-dev libgomp1
```

### CentOS/RHEL/Fedora
```bash
sudo yum install -y \
    nss atk-bridge drm2 libxkbcommon \
    libXcomposite libXdamage libXrandr mesa-libgbm \
    libXss alsa-lib glib2 gtk3 GConf2 \
    libXrandr alsa-lib pango cairo gtk3 gdk-pixbuf2 \
    mesa-libGL libSM libXext libXrender libgomp
```

## Troubleshooting

### Common Issues

1. **"libglib-2.0.so.0: cannot open shared object file"**
   - Install system dependencies using the commands above
   - The app will fall back to RSS scraping if this fails

2. **"Executable doesn't exist at /home/user/.cache/ms-playwright/"**
   - Run: `python -m playwright install chromium`
   - Or run: `python setup_playwright.py`

3. **"BrowserType.launch: Target page, context or browser has been closed"**
   - This usually indicates missing system dependencies
   - Install the system libraries listed above

4. **Playwright fails on Streamlit Cloud**
   - This is expected due to limited system access
   - The app will automatically fall back to RSS scraping
   - RSS scraping provides the same functionality with different data sources

## Verification

Test Playwright installation:

```python
from playwright.async_api import async_playwright
import asyncio

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        await browser.close()
        print(f'Success: {title}')

asyncio.run(test())
```

## Fallback Strategy

Pinterest Factory is designed to work with or without Playwright:

1. **Playwright Available**: Direct Pinterest scraping with real-time data
2. **Playwright Unavailable**: RSS feed scraping with curated Pinterest content
3. **Both Fail**: Uses cached/simulated data for testing

The app will automatically detect Playwright availability and use the appropriate method.

## Deployment Notes

### Streamlit Cloud
- System dependencies cannot be installed manually
- The app handles this gracefully with RSS fallback
- No additional configuration needed

### Docker
Add this to your Dockerfile:
```dockerfile
# Install system dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 \
    libasound2 libglib2.0-0 libgtk-3-0 libgconf-2-4 \
    libxrandr2 libasound2 libpangocairo-1.0-0 libatk1.0-0 \
    libcairo-gobject2 libgtk-3-0 libgdk-pixbuf2.0-0 \
    libgl1-mesa-glx libsm6 libxext6 libxrender-dev libgomp1

# Install Playwright browsers
RUN python -m playwright install chromium
```

### Self-Hosted
Run the installation script:
```bash
bash install_dependencies.sh
```

## Performance Notes

- Playwright scraping is more accurate but slower
- RSS scraping is faster but uses curated feeds
- Both methods provide sufficient data for AI hook generation
- The app automatically chooses the best available method
