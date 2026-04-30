# Fonts Directory

This directory contains font files used for Pinterest pin generation.

## Required Fonts

The application needs bold, readable fonts for Pinterest pins. Recommended fonts:

1. **Montserrat-Bold.ttf** - Modern, clean, highly readable
2. **OpenSans-Bold.ttf** - Alternative option
3. **Roboto-Bold.ttf** - Google Fonts alternative

## How to Add Fonts

1. Download font files from:
   - Google Fonts: https://fonts.google.com/
   - Font Squirrel: https://www.fontsquirrel.com/

2. Place .ttf files in this directory

3. Update font paths in `components/pin_generator.py`:
   ```python
   font_path = "fonts/Montserrat-Bold.ttf"
   ```

## Font Requirements

- **Bold weight** for better visibility
- **High readability** at small sizes
- **Web-safe** licensing for commercial use
- **TTF format** for PIL/Pillow compatibility
