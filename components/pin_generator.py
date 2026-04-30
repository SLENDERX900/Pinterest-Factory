"""
components/pin_generator.py — Tab 3: Pin Generation
Generates Pinterest pins using PIL/Pillow from recipe data and hooks.
Features web scraping for images, hook text cleaning, and 3 dynamic templates.
"""

import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
from io import BytesIO
import zipfile
from datetime import datetime
import random
from utils.hf_image_client import generate_tailored_image


# ── Pinterest Standard ────────────────────────────────────────────────────────
PIN_WIDTH = 1000
PIN_HEIGHT = 1500
FONT_SIZE_HEADLINE = 130  # Much larger for impact
FONT_SIZE_SUB = 70
BRAND_FONT_SIZE = 28  # Small but readable as requested


# ── Web Scraping Helper ───────────────────────────────────────────────────────

def fetch_recipe_image(url: str) -> Image.Image | None:
    """
    Fetch the main image from a recipe URL using web scraping.
    Looks for og:image meta tag or similar.
    
    Args:
        url: Recipe URL
    
    Returns:
        PIL Image object or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            img_response = requests.get(image_url, headers=headers, timeout=10)
            img_response.raise_for_status()
            return Image.open(BytesIO(img_response.content))
        
        # Fallback: try twitter:image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            image_url = twitter_image['content']
            img_response = requests.get(image_url, headers=headers, timeout=10)
            img_response.raise_for_status()
            return Image.open(BytesIO(img_response.content))
        
        # Fallback: try first img tag with recipe-related class
        for img in soup.find_all('img'):
            if img.get('src') and any(x in img.get('src', '').lower() for x in ['recipe', 'food', 'dish']):
                img_url = img['src']
                if not img_url.startswith('http'):
                    img_url = url + img_url
                img_response = requests.get(img_url, headers=headers, timeout=10)
                img_response.raise_for_status()
                return Image.open(BytesIO(img_response.content))
        
        return None
    
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
        return None


# ── Hook Text Cleaner ────────────────────────────────────────────────────────

def clean_hook_text(hook: str) -> str:
    """
    Clean Ollama output to remove conversational filler and extract actual hooks.
    More aggressive stripping to remove all conversational filler.
    
    Args:
        hook: Raw hook text from Ollama
    
    Returns:
        Cleaned hook text
    """
    if not hook:
        return hook
    
    # Debug: log original hook
    print(f"DEBUG: Original hook: '{hook}'")
    
    # Convert to lowercase for case-insensitive matching, but preserve original
    hook_lower = hook.lower()
    
    # Remove common conversational filler (case-insensitive, more aggressive)
    filler_phrases = [
        'here are the 5 pinterest hooks:',
        'here are 5 pinterest hooks:',
        'here are the hooks:',
        'here are hooks:',
        'pinterest hooks:',
        'hooks:',
        'here are',
        'pinterest',
        '1.', '2.', '3.', '4.', '5.',
        '-', '*',
    ]
    
    cleaned = hook
    for phrase in filler_phrases:
        # Replace both lowercase and original case versions
        cleaned = cleaned.replace(phrase, '')
        cleaned = cleaned.replace(phrase.capitalize(), '')
        cleaned = cleaned.replace(phrase.upper(), '')
    
    # Also remove any lines that contain these phrases
    lines = cleaned.split('\n')
    cleaned_lines = []
    for line in lines:
        line_lower = line.lower()
        if not any(phrase in line_lower for phrase in ['here are', 'pinterest hooks', 'hooks:']):
            cleaned_lines.append(line.strip())
    
    # Filter out empty/short lines
    cleaned_lines = [line for line in cleaned_lines if line and len(line) > 3]
    
    # Debug: log cleaned result
    print(f"DEBUG: Cleaned lines: {cleaned_lines}")
    
    # Return first meaningful line or original if no good lines found
    if cleaned_lines:
        return cleaned_lines[0]
    return hook


# ── Text Rendering with Stroke ─────────────────────────────────────────────

def draw_text_with_stroke(draw, text, font, x, y, fill_color, stroke_color, stroke_width=4):
    """Draw text with outline stroke for better readability on images."""
    # Draw stroke by offsetting in all directions
    for dx in range(-stroke_width, stroke_width + 1, 2):
        for dy in range(-stroke_width, stroke_width + 1, 2):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_color)


def wrap_text(text: str, font, max_width: int) -> list[str]:
    """
    Wrap text to fit within max_width pixels.
    Returns a list of lines.
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


# ── Branding Watermark ──────────────────────────────────────────────────────

def add_branding_watermark(image: Image.Image, font_base_path: str = None) -> Image.Image:
    """
    Add subtle 'nobscooking.com' watermark at bottom of pin.
    Positioned at Y=1420 with semi-transparent background for readability.
    """
    draw = ImageDraw.Draw(image)
    
    # Load font
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Medium.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, BRAND_FONT_SIZE)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    domain = "nobscooking.com"
    
    # Get text size
    bbox = font.getbbox(domain)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position at bottom center as requested (Y=1420 on 1000x1500 image)
    x = (PIN_WIDTH - text_width) // 2  # Perfectly centered on X-axis
    y = 1420  # Near bottom edge as requested
    
    # Add semi-transparent black rectangle behind text for readability
    padding = 10
    bg_rect = [
        x - padding,
        y - padding,
        x + text_width + padding,
        y + text_height + padding
    ]
    
    # Create semi-transparent overlay
    overlay = Image.new('RGBA', (PIN_WIDTH, PIN_HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(bg_rect, fill=(0, 0, 0, 128))  # Semi-transparent black
    
    # Composite the overlay onto the main image
    image = Image.alpha_composite(image.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(image)  # Re-create draw context after composite
    
    # Draw white text with dark stroke for maximum visibility
    draw_text_with_stroke(draw, domain, font, x, y, 
                         fill_color=(255, 255, 255),  # White text
                         stroke_color=(0, 0, 0),        # Black stroke
                         stroke_width=2)               # Subtle stroke
    
    return image.convert('RGB')  # Convert back to RGB for consistency


# ── Template Functions ────────────────────────────────────────────────────────

def apply_template_hero_top(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 1: Hero Text at Top.
    Large bold text at top with gradient fade, food image below.
    Clean, modern Pinterest style.
    """
    # Start with full-size image
    img = ImageOps.fit(image, (PIN_WIDTH, PIN_HEIGHT), Image.Resampling.LANCZOS)
    
    # Create gradient overlay at top for text readability
    overlay = Image.new('RGBA', (PIN_WIDTH, PIN_HEIGHT), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Strong gradient from top (60% of image height)
    gradient_height = int(PIN_HEIGHT * 0.6)
    for y in range(gradient_height):
        # Fade from 85% black at top to 0% at bottom of gradient area
        alpha = int(217 * (1 - y / gradient_height))
        draw_ov.line([(0, y), (PIN_WIDTH, y)], fill=(0, 0, 0, alpha))
    
    # Composite
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    # Load large bold font
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Black.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, FONT_SIZE_HEADLINE)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw text with stroke at top
    draw = ImageDraw.Draw(img)
    hook_lines = wrap_text(hook, font, PIN_WIDTH - 100)
    
    y_offset = 80
    line_spacing = FONT_SIZE_HEADLINE + 20
    
    for line in hook_lines[:3]:  # Max 3 lines
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (PIN_WIDTH - text_width) // 2  # Center horizontally
        
        draw_text_with_stroke(draw, line, font, x, y_offset,
                            fill_color=(255, 255, 255),
                            stroke_color=(0, 0, 0),
                            stroke_width=6)
        y_offset += line_spacing
    
    # Add watermark
    img = add_branding_watermark(img, font_base_path)
    
    return img


def apply_template_bottom_banner(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 2: Bottom Banner.
    Food image fills top, text on solid color banner at bottom.
    Great for showing off the food.
    """
    # Create canvas
    img = Image.new('RGB', (PIN_WIDTH, PIN_HEIGHT))
    
    # Resize and crop food image to top 70%
    food_img = ImageOps.fit(image, (PIN_WIDTH, int(PIN_HEIGHT * 0.7)), Image.Resampling.LANCZOS)
    img.paste(food_img, (0, 0))
    
    # Draw solid color banner at bottom (30%)
    draw = ImageDraw.Draw(img)
    banner_color = (204, 85, 0)  # Warm terracotta
    draw.rectangle([0, int(PIN_HEIGHT * 0.7), PIN_WIDTH, PIN_HEIGHT], fill=banner_color)
    
    # Load font
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-ExtraBold.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, FONT_SIZE_SUB)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw text in banner area
    hook_lines = wrap_text(hook, font, PIN_WIDTH - 80)
    
    banner_top = int(PIN_HEIGHT * 0.7)
    banner_height = int(PIN_HEIGHT * 0.3)
    
    total_text_height = len(hook_lines[:2]) * (FONT_SIZE_SUB + 15)
    y_offset = banner_top + (banner_height - total_text_height) // 2
    
    for line in hook_lines[:2]:  # Max 2 lines
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (PIN_WIDTH - text_width) // 2
        
        draw_text_with_stroke(draw, line, font, x, y_offset,
                            fill_color=(255, 255, 255),
                            stroke_color=(0, 0, 0),
                            stroke_width=4)
        y_offset += FONT_SIZE_SUB + 15
    
    # Add watermark
    img = add_branding_watermark(img, font_base_path)
    
    return img


def apply_template_side_overlay(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 3: Side Overlay.
    Food image on right, colored overlay panel on left with text.
    Modern asymmetrical design.
    """
    # Create canvas
    img = Image.new('RGB', (PIN_WIDTH, PIN_HEIGHT))
    
    # Food image on right side (65% width)
    food_width = int(PIN_WIDTH * 0.65)
    food_img = ImageOps.fit(image, (food_width, PIN_HEIGHT), Image.Resampling.LANCZOS)
    img.paste(food_img, (PIN_WIDTH - food_width, 0))
    
    # Left panel with gradient
    overlay = Image.new('RGBA', (PIN_WIDTH, PIN_HEIGHT), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    panel_width = int(PIN_WIDTH * 0.45)
    # Gradient from left (solid) to right (transparent where food starts)
    for x in range(panel_width):
        alpha = int(230 * (1 - x / panel_width * 0.3))  # Keep mostly opaque
        draw_ov.line([(x, 0), (x, PIN_HEIGHT)], fill=(40, 40, 40, alpha))
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    # Load font
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Black.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 100)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw text on left panel
    draw = ImageDraw.Draw(img)
    hook_lines = wrap_text(hook, font, panel_width - 60)
    
    # Vertically center text
    total_height = len(hook_lines[:3]) * 120
    y_offset = (PIN_HEIGHT - total_height) // 2
    
    for line in hook_lines[:3]:  # Max 3 lines
        draw_text_with_stroke(draw, line, font, 40, y_offset,
                            fill_color=(255, 255, 255),
                            stroke_color=(0, 0, 0),
                            stroke_width=5)
        y_offset += 120
    
    # Add watermark at bottom right
    img = add_branding_watermark(img, font_base_path)
    
    return img


# ── Main Render Function ─────────────────────────────────────────────────────

def render_pin_generator():
    st.subheader("Pin Generation")
    st.caption("Generate Pinterest pins from recipe URLs and hooks using dynamic templates.")
    
    # Check if we have data to work with
    if not st.session_state.get('recipes') or not st.session_state.get('hooks'):
        st.warning("No recipe data or hooks found. Please complete Step 1 (Batch Intake) and Step 2 (AI Copy Engine) first.")
        return
    
    # Font path (base directory, templates will use specific weights)
    font_base_path = "Montserrat/static"
    
    # Generation settings
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Recipes:** {len(st.session_state.recipes)}")
    with col2:
        st.write(f"**Total Hooks:** {sum(len(v) for v in st.session_state.hooks.values())}")
    
    st.divider()
    
    # Generate button
    if st.button("🎨 Generate Pins", type="primary", use_container_width=True):
        with st.spinner("Fetching images and generating pins..."):
            generated_images = []
            template_functions = [
                apply_template_hero_top,
                apply_template_bottom_banner,
                apply_template_side_overlay
            ]
            
            print("DEBUG: Starting pin generation...")
            
            # Iterate through recipes and their hooks
            for recipe in st.session_state.recipes:
                recipe_name = recipe.get('name', 'Unknown')
                recipe_url = recipe.get('url', '')
                hooks = st.session_state.hooks.get(recipe_name, {})
                
                print(f"DEBUG: Processing recipe: {recipe_name}, URL: {recipe_url}, Hooks: {len(hooks)}")
                
                # Fetch recipe image
                recipe_image = None
                if recipe_url:
                    print(f"DEBUG: Fetching image from {recipe_url}")
                    recipe_image = fetch_recipe_image(recipe_url)
                    if recipe_image:
                        print(f"DEBUG: Image fetched successfully, size: {recipe_image.size}")
                    else:
                        print(f"DEBUG: Failed to fetch image, using fallback")
                
                # If no image fetched, use a fallback colored background
                if not recipe_image:
                    print("DEBUG: Using fallback gray background")
                    recipe_image = Image.new('RGB', (1000, 1500), color=(200, 200, 200))
                
                # Apply templates to each hook
                template_idx = 0
                for angle, hook_text in hooks.items():
                    if hook_text:
                        # Clean the hook text
                        cleaned_hook = clean_hook_text(hook_text)
                        print(f"DEBUG: Hook for {angle}: '{cleaned_hook}'")
                        
                        # Rotate through templates
                        template_func = template_functions[template_idx % len(template_functions)]
                        template_idx += 1
                        print(f"DEBUG: Applying template: {template_func.__name__}")
                        
                        # Try HF-tailored image first, then apply visual template fallback
                        ai_img = generate_tailored_image(recipe_name, cleaned_hook, fallback_image=None)
                        source_img = ai_img if ai_img else recipe_image.copy()
                        img = template_func(source_img, cleaned_hook, font_base_path)
                        print(f"DEBUG: Generated pin for {recipe_name} - {angle}")
                        
                        generated_images.append({
                            'image': img,
                            'recipe': recipe_name,
                            'angle': angle,
                            'hook': cleaned_hook
                        })
            
            print(f"DEBUG: Total pins generated: {len(generated_images)}")
            
            # Store in session state
            st.session_state.generated_pins = generated_images
            st.success(f"Generated {len(generated_images)} pins!")
    
    # Display results if available
    if st.session_state.get('generated_pins'):
        pins = st.session_state.generated_pins
        
        st.divider()
        st.subheader("Generated Pins Preview")
        
        # Display all pins in a grid (3 columns)
        cols = st.columns(3)
        for i, pin in enumerate(pins):
            with cols[i % 3]:
                st.image(pin['image'], caption=f"{pin['recipe']}\n{pin['angle']}", width="stretch")
        
        # Show count and download button
        st.divider()
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.metric("Total pins generated", len(pins))
        
        with col2:
            # Create zip file for download
            if st.button("📥 Download All Pins (ZIP)"):
                with st.spinner("Creating ZIP file..."):
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for i, pin in enumerate(pins):
                            # Convert PIL image to bytes
                            img_buffer = BytesIO()
                            pin['image'].save(img_buffer, format='PNG')
                            img_buffer.seek(0)
                            
                            # Create filename
                            filename = f"{pin['recipe']}_{pin['angle']}_{i+1}.png"
                            # Sanitize filename
                            filename = filename.replace(' ', '_').replace('/', '_')
                            
                            zipf.writestr(filename, img_buffer.getvalue())
                    
                    zip_buffer.seek(0)
                    
                    # Download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"pinterest_pins_{timestamp}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
