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
BRAND_FONT_SIZE = 50  # Much larger for visibility with default font


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
    print(f"WATERMARK DEBUG: === STARTING WATERMARK FUNCTION ===")
    print(f"WATERMARK DEBUG: Adding watermark to image size: {image.size}, mode: {image.mode}")
    print(f"WATERMARK DEBUG: This should be very visible in terminal!")
    import sys
    sys.stdout.flush()
    
    # Convert to RGBA if needed
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    draw = ImageDraw.Draw(image)
    
    # Load font with bulletproof error handling
    try:
        # Use absolute path to ensure we find the font
        current_dir = os.path.dirname(os.path.abspath(__file__))
        font_file = os.path.join(current_dir, '..', 'fonts', 'Montserrat-Bold.ttf')
        
        # Debug: Print the exact path we're trying
        print(f"WATERMARK DEBUG: Attempting to load font from: {font_file}")
        print(f"WATERMARK DEBUG: Font file exists: {os.path.exists(font_file)}")
        
        if not os.path.exists(font_file):
            st.error("STOP: Montserrat-Bold.ttf not found in the fonts directory!")
            st.error(f"Expected font at: {font_file}")
            st.stop()
        
        font = ImageFont.truetype(font_file, BRAND_FONT_SIZE)
        print(f"WATERMARK DEBUG: Successfully loaded font: {font_file}")
        
    except Exception as e:
        st.error(f"STOP: Font loading failed: {str(e)}")
        st.error("Please ensure Montserrat-Bold.ttf is in the fonts directory")
        st.stop()
    
    domain = "nobscooking.com"
    
    # Get text size
    bbox = font.getbbox(domain)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    print(f"DEBUG: Text '{domain}' size: {text_width}x{text_height} pixels")
    
    # Position at bottom center as requested (Y=1420 on 1000x1500 image)
    x = (PIN_WIDTH - text_width) // 2  # Perfectly centered on X-axis
    y = 1420  # Near bottom edge as requested
    
    print(f"DEBUG: Positioning text at ({x}, {y})")
    
    # Add semi-transparent black rectangle behind text for readability
    padding = 10
    bg_rect = [
        x - padding,
        y - padding,
        x + text_width + padding,
        y + text_height + padding
    ]
    
    print(f"DEBUG: Drawing background rectangle: {bg_rect}")
    
    # Draw semi-transparent background
    draw.rectangle(bg_rect, fill=(0, 0, 0, 180))  # More opaque for better visibility
    
    # Draw white text with dark stroke for maximum visibility
    print(f"DEBUG: Drawing text with stroke")
    draw_text_with_stroke(draw, domain, font, x, y, 
                         fill_color=(255, 255, 255),  # White text
                         stroke_color=(0, 0, 0),        # Black stroke
                         stroke_width=2)               # Subtle stroke
    
    print(f"WATERMARK DEBUG: Watermark added successfully")
    print(f"WATERMARK DEBUG: === WATERMARK FUNCTION COMPLETE ===")
    import sys
    sys.stdout.flush()
    
    # Convert back to RGB for consistency
    if image.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
        image = background
    
    return image


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
    
    # Load font with bulletproof error handling
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        font_file = os.path.join(current_dir, '..', 'fonts', 'Montserrat-Bold.ttf')
        
        if not os.path.exists(font_file):
            st.error("STOP: Montserrat-Bold.ttf not found in the fonts directory!")
            st.error(f"Expected font at: {font_file}")
            st.stop()
        
        font = ImageFont.truetype(font_file, FONT_SIZE_HEADLINE)
        
    except Exception as e:
        st.error(f"STOP: Font loading failed: {str(e)}")
        st.error("Please ensure Montserrat-Bold.ttf is in the fonts directory")
        st.stop()
    
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


def apply_template_center_badge(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 2: Center Badge.
    Dark charcoal box directly in the middle of the 1000x1500 image.
    Food image as background with centered overlay box.
    """
    # Create canvas with food image as background
    img = ImageOps.fit(image, (PIN_WIDTH, PIN_HEIGHT), Image.Resampling.LANCZOS)
    
    # Draw dark charcoal box in the center [100, 500, 900, 1000]
    draw = ImageDraw.Draw(img)
    badge_color = (40, 40, 40)  # Dark charcoal
    draw.rectangle([100, 500, 900, 1000], fill=badge_color)
    
    # Load font with bulletproof error handling
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        font_file = os.path.join(current_dir, '..', 'fonts', 'Montserrat-Bold.ttf')
        
        if not os.path.exists(font_file):
            st.error("STOP: Montserrat-Bold.ttf not found in the fonts directory!")
            st.error(f"Expected font at: {font_file}")
            st.stop()
        
        font = ImageFont.truetype(font_file, FONT_SIZE_SUB)
        
    except Exception as e:
        st.error(f"STOP: Font loading failed: {str(e)}")
        st.error("Please ensure Montserrat-Bold.ttf is in the fonts directory")
        st.stop()
    
    # Draw text in the centered badge area
    hook_lines = wrap_text(hook, font, 700)  # Badge width minus padding
    
    badge_center_x = 500  # Center of [100, 500, 900, 1000]
    badge_center_y = 750  # Center of [100, 500, 900, 1000]
    
    total_text_height = len(hook_lines[:3]) * (FONT_SIZE_SUB + 10)
    y_offset = badge_center_y - (total_text_height // 2)
    
    for line in hook_lines[:3]:  # Max 3 lines
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = badge_center_x - (text_width // 2)  # Center in badge
        
        draw_text_with_stroke(draw, line, font, x, y_offset,
                            fill_color=(255, 255, 255),  # ENFORCED WHITE TEXT
                            stroke_color=(0, 0, 0),
                            stroke_width=4)
        y_offset += FONT_SIZE_SUB + 10
    
    # Add watermark
    img = add_branding_watermark(img, font_base_path)
    
    return img


def apply_template_split_screen(image: Image.Image, hook: str, font_base_path: str = None) -> Image.Image:
    """
    Template 3: Split Screen.
    Orange block on TOP, food image on bottom.
    Modern split design with orange header.
    """
    # Create canvas
    img = Image.new('RGB', (PIN_WIDTH, PIN_HEIGHT))
    
    # Draw orange block on TOP [0, 0, 1000, 750]
    draw = ImageDraw.Draw(img)
    orange_color = (255, 140, 0)  # Orange
    draw.rectangle([0, 0, PIN_WIDTH, 750], fill=orange_color)
    
    # Paste food image at bottom using coordinates (0, 750)
    food_img = ImageOps.fit(image, (PIN_WIDTH, 750), Image.Resampling.LANCZOS)
    img.paste(food_img, (0, 750))
    
    # Load font with bulletproof error handling
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        font_file = os.path.join(current_dir, '..', 'fonts', 'Montserrat-Bold.ttf')
        
        if not os.path.exists(font_file):
            st.error("STOP: Montserrat-Bold.ttf not found in the fonts directory!")
            st.error(f"Expected font at: {font_file}")
            st.stop()
        
        font = ImageFont.truetype(font_file, FONT_SIZE_SUB)
        
    except Exception as e:
        st.error(f"STOP: Font loading failed: {str(e)}")
        st.error("Please ensure Montserrat-Bold.ttf is in the fonts directory")
        st.stop()
    
    # Draw text in orange top area
    hook_lines = wrap_text(hook, font, PIN_WIDTH - 80)
    
    orange_height = 750
    total_text_height = len(hook_lines[:2]) * (FONT_SIZE_SUB + 15)
    y_offset = (orange_height - total_text_height) // 2
    
    for line in hook_lines[:2]:  # Max 2 lines
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (PIN_WIDTH - text_width) // 2  # Center in orange area
        
        draw_text_with_stroke(draw, line, font, x, y_offset,
                            fill_color=(255, 255, 255),  # ENFORCED WHITE TEXT
                            stroke_color=(0, 0, 0),
                            stroke_width=4)
        y_offset += FONT_SIZE_SUB + 15
    
    # Add watermark
    img = add_branding_watermark(img, font_base_path)
    
    return img


# ── Hugging Face Image-to-Image Helper ───────────────────────────────────────

def hf_image_to_image(image: Image.Image, recipe_name: str, hook: str) -> Image.Image:
    """
    Generate tailored image using Hugging Face image-to-image model.
    Bulletproof handling of timeouts and API failures.
    """
    try:
        # Check HF token
        hf_token = st.secrets.get("HF_TOKEN")
        if not hf_token or hf_token == "your_hugging_face_token_here":
            print("HF DEBUG: No valid HF_TOKEN found in secrets, using fallback image")
            return image
        
        print(f"HF DEBUG: Starting image-to-image generation for: {recipe_name}")
        print(f"HF DEBUG: Hook: {hook}")
        
        # Prepare image bytes
        import io
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        image_bytes = img_buffer.getvalue()
        
        # Create dynamic prompt
        prompt = f"Professional food photography of {recipe_name}, tailored to highlight: {hook}. Make it appetizing and high quality."
        print(f"HF DEBUG: Generated prompt: {prompt}")
        
        # HF API setup
        api_url = "https://api-inference.huggingface.co/models/timbrooks/instruct-pix2pix"
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "image": image_bytes
        }
        
        print("HF DEBUG: Making API call with timeout=20...")
        
        # Make API call with strict timeout
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        
        if response.status_code == 200:
            print("HF DEBUG: API call successful, processing response...")
            result_image = Image.open(io.BytesIO(response.content))
            print("HF DEBUG: Successfully generated tailored image")
            return result_image
        elif response.status_code == 503:
            print("HF DEBUG: Model loading (503), using fallback image")
            return image
        elif response.status_code == 429:
            print("HF DEBUG: Rate limited (429), using fallback image")
            return image
        else:
            print(f"HF DEBUG: API error {response.status_code}: {response.text[:100]}, using fallback")
            return image
            
    except requests.exceptions.Timeout:
        print("HF DEBUG: Request timed out after 20 seconds, using fallback image")
        return image
    except Exception as e:
        print(f"HF DEBUG: Unexpected error: {str(e)}, using fallback image")
        return image


# ── Main Render Function ─────────────────────────────────────────────────────

def render_pin_generator():
    st.subheader("Pin Generation")
    st.caption("Generate Pinterest pins from recipe URLs and hooks using dynamic templates.")
    
    # Check if we have data to work with
    if not st.session_state.get('recipes') or not st.session_state.get('hooks'):
        st.warning("No recipe data or hooks found. Please complete Step 1 (Batch Intake) and Step 2 (AI Copy Engine) first.")
        return
    
    # Check HF token availability
    hf_token = st.secrets.get("HF_TOKEN")
    if not hf_token or hf_token == "your_hugging_face_token_here":
        st.warning("⚠️ **Hugging Face token not found** in secrets.toml")
        st.info("📝 **To enable AI-tailored images:**")
        st.code("""
# Add to .streamlit/secrets.toml:
HF_TOKEN = "hf_your_actual_token_here"
        """)
        st.info("Or add HF_TOKEN to your Streamlit Cloud secrets")
        hf_available = False
    else:
        hf_available = True
        print("HF DEBUG: Valid HF_TOKEN found in secrets")
    
    # Font path (use local fonts directory)
    font_base_path = "fonts"
    
    # Generation settings
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Recipes:** {len(st.session_state.recipes)}")
    with col2:
        st.write(f"**Total Hooks:** {sum(len(v) for v in st.session_state.hooks.values())}")
    
    st.divider()
    
    # Generate button
    if st.button("🎨 Generate Pins", type="primary", width='stretch'):
        with st.spinner("Fetching images and generating pins..."):
            generated_images = []
            template_functions = [
                apply_template_hero_top,
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
                        
                        # Try HF-tailored image first, then apply visual template
                        if hf_available:
                            print(f"DEBUG: Attempting HF image generation for {recipe_name}")
                            tailored_img = hf_image_to_image(recipe_image.copy(), recipe_name, cleaned_hook)
                            source_img = tailored_img
                        else:
                            print(f"DEBUG: HF not available, using original image")
                            source_img = recipe_image.copy()
                        
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
                        width='stretch'
                    )
