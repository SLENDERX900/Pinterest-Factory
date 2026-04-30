"""
components/pin_generator.py — Tab 3: Pin Generation
Generates Pinterest pins using PIL/Pillow from recipe data and hooks.
Features web scraping for images, hook text cleaning, and 3 dynamic templates.
"""

import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import zipfile
from datetime import datetime
import random
from utils.hf_image_client import generate_tailored_image


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


# ── Text Wrapping ───────────────────────────────────────────────────────────

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


# ── Branding Stamp ─────────────────────────────────────────────────────────

def add_branding_stamp(image: Image.Image, font_base_path: str = None) -> Image.Image:
    """
    Add 'nobscooking.com' branding stamp at the bottom center of the image.
    Uses a semi-transparent black rectangle behind the text for visibility.
    """
    draw = ImageDraw.Draw(image)
    
    # Load bold font for branding
    try:
        if font_base_path:
            bold_font_file = os.path.join(font_base_path, 'Montserrat-Bold.ttf')
            if os.path.exists(bold_font_file):
                font = ImageFont.truetype(bold_font_file, 32)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    domain = "nobscooking.com"
    
    # Get text bounding box
    bbox = font.getbbox(domain)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position (centered horizontally, near bottom)
    x = (1000 - text_width) // 2
    y = 1420
    
    # Draw semi-transparent black rectangle behind text
    padding = 10
    rect_x1 = x - padding
    rect_y1 = y - padding
    rect_x2 = x + text_width + padding
    rect_y2 = y + text_height + padding
    
    # Create overlay for semi-transparent rectangle
    overlay = Image.new('RGBA', (1000, 1500), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=(0, 0, 0, 128))  # 50% opacity black
    
    # Composite overlay onto image
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    
    # Draw bold orange text on top
    draw = ImageDraw.Draw(image)
    draw.text((x, y), domain, font=font, fill=(204, 85, 0))  # Terracotta orange
    
    return image


# ── Template Functions ────────────────────────────────────────────────────────

def apply_template_dark_gradient(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 1: Dark Gradient overlay.
    Crop to 1000x1500, add black gradient from top to middle, draw text in white.
    """
    # Crop to 1000x1500
    image = ImageOps.fit(image, (1000, 1500), Image.Resampling.LANCZOS)
    
    # Create gradient overlay
    overlay = Image.new('RGBA', (1000, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw gradient from top (rich black 85% opacity) to middle (0% opacity)
    for y in range(750):
        alpha = int(217 * (1 - y / 750))  # 217 = 85% of 255
        draw.line([(0, y), (1000, y)], fill=(0, 0, 0, alpha))
    
    # Composite gradient onto image
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    
    # Load font (Black for maximum impact on gradient)
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Black.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 90)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw wrapped hook text in white in top third with stroke
    draw = ImageDraw.Draw(image)
    hook_lines = wrap_text(hook, font, 900)
    y_offset = 100
    for line in hook_lines:
        draw.text((50, y_offset), line, font=font, fill=(255, 255, 255))
        y_offset += 100
    
    # Add branding stamp
    image = add_branding_stamp(image, font_base_path)
    
    return image


def apply_template_center_badge(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 2: Center Badge.
    Crop to 1000x1500, draw colored rectangle in center, draw text centered.
    """
    # Crop to 1000x1500
    image = ImageOps.fit(image, (1000, 1500), Image.Resampling.LANCZOS)
    
    # Create colored rectangle overlay (deep red with 80% opacity)
    overlay = Image.new('RGBA', (1000, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw centered rectangle (dark charcoal with 85% opacity)
    badge_width, badge_height = 800, 400
    badge_x = (1000 - badge_width) // 2
    badge_y = (1500 - badge_height) // 2
    draw.rectangle([badge_x, badge_y, badge_x + badge_width, badge_y + badge_height], 
                  fill=(30, 30, 30, 217))  # Dark charcoal with 85% opacity
    
    # Composite onto image
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    
    # Load font (Bold for readability on badge)
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Bold.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 80)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw wrapped text centered in badge with stroke
    draw = ImageDraw.Draw(image)
    hook_lines = wrap_text(hook, font, 750)
    
    # Calculate vertical centering
    total_height = len(hook_lines) * 90
    start_y = badge_y + (badge_height - total_height) // 2
    
    for i, line in enumerate(hook_lines):
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        text_x = badge_x + (badge_width - text_width) // 2
        draw.text((text_x, start_y + (i * 90)), line, font=font, fill=(255, 255, 255))
    
    # Add branding stamp
    image = add_branding_stamp(image, font_base_path)
    
    return image


def apply_template_split_screen(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 3: Split Screen.
    Create 1000x1500 blank, crop photo to 1000x750 for bottom half, 
    fill top half with color, draw text in top half.
    """
    # Create blank 1000x1500 image
    result = Image.new('RGB', (1000, 1500))
    
    # Crop photo to 1000x750
    photo = ImageOps.fit(image, (1000, 750), Image.Resampling.LANCZOS)
    
    # Paste photo into bottom half
    result.paste(photo, (0, 750))
    
    # Fill top half with warm terracotta color
    draw = ImageDraw.Draw(result)
    draw.rectangle([0, 0, 1000, 750], fill=(204, 85, 0))  # Terracotta/burnt orange
    
    # Load font (Medium for cleaner look with photo)
    try:
        if font_base_path:
            font_file = os.path.join(font_base_path, 'Montserrat-Medium.ttf')
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 90)
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw wrapped text centered in top half with stroke
    hook_lines = wrap_text(hook, font, 900)
    
    # Calculate vertical centering in top half
    total_height = len(hook_lines) * 100
    start_y = (750 - total_height) // 2
    
    for i, line in enumerate(hook_lines):
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        text_x = (1000 - text_width) // 2
        draw.text((text_x, start_y + (i * 100)), line, font=font, fill=(255, 255, 255))
    
    # Add branding stamp
    result = add_branding_stamp(result, font_base_path)
    
    return result


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
                apply_template_dark_gradient,
                apply_template_center_badge,
                apply_template_split_screen
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
                st.image(pin['image'], caption=f"{pin['recipe']}\n{pin['angle']}", use_container_width=True)
        
        # Show count and download button
        st.divider()
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.metric("Total pins generated", len(pins))
        
        with col2:
            # Create zip file for download
            if st.button("📥 Download All Pins (ZIP)", use_container_width=True):
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
