"""
utils/hf_image_client.py
STEP 5: Tailored Image Generation using $0 Hugging Face Inference API
Uses free Hugging Face Inference API for image-to-image and text-to-image generation.
"""

from __future__ import annotations

import os
import io
import base64
from typing import Optional
import logging

import requests
from PIL import Image

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_API_BASE = "https://api-inference.huggingface.co/models"

# Free image-to-image models available on Hugging Face
IMAGE_TO_IMAGE_MODELS = [
    "timbrooks/instruct-pix2pix",  # Instruction-based image editing
    "lllyasviel/sd-controlnet-canny",  # ControlNet for structure preservation
]

# Free text-to-image models
TEXT_TO_IMAGE_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
]


def _hf_api_call(model: str, inputs: dict) -> Optional[bytes]:
    """
    Make a call to Hugging Face Inference API.
    
    Args:
        model: Model identifier on Hugging Face
        inputs: Input data for the model
        
    Returns:
        Image bytes or None if failed
    """
    if not HF_API_TOKEN:
        logger.warning("HF_API_TOKEN not set, skipping Hugging Face generation")
        return None
    
    url = f"{HF_API_BASE}/{model}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=inputs,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 503:
            # Model is loading
            logger.info(f"Model {model} is loading, retrying...")
            import time
            time.sleep(20)
            return _hf_api_call(model, inputs)
        else:
            logger.warning(f"HF API error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.warning(f"HF API call failed: {e}")
        return None


def _generate_with_text_to_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1536
) -> Optional[Image.Image]:
    """
    Generate image from text using Stable Diffusion.
    
    Args:
        prompt: Text description of desired image
        negative_prompt: Things to avoid in the image
        width: Image width
        height: Image height
        
    Returns:
        PIL Image or None
    """
    # Try each model in order
    for model in TEXT_TO_IMAGE_MODELS:
        inputs = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
            }
        }
        
        image_bytes = _hf_api_call(model, inputs)
        if image_bytes:
            try:
                return Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.debug(f"Failed to open generated image: {e}")
                continue
    
    return None


def _generate_with_image_to_image(
    base_image: Image.Image,
    prompt: str,
    strength: float = 0.7
) -> Optional[Image.Image]:
    """
    Transform an image based on a text prompt (image-to-image).
    
    Args:
        base_image: Original PIL Image
        prompt: Instruction for transformation
        strength: How much to modify (0.0 = same, 1.0 = completely new)
        
    Returns:
        PIL Image or None
    """
    if not HF_API_TOKEN:
        return None
    
    # Convert image to bytes
    img_buffer = io.BytesIO()
    base_image.convert('RGB').save(img_buffer, format='JPEG')
    img_bytes = img_buffer.getvalue()
    
    # Try InstructPix2Pix
    model = "timbrooks/instruct-pix2pix"
    url = f"{HF_API_BASE}/{model}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    try:
        # Encode image as base64 for API
        img_b64 = base64.b64encode(img_bytes).decode()
        
        inputs = {
            "inputs": {
                "image": img_b64,
                "prompt": prompt,
                "num_inference_steps": 20,
                "image_guidance_scale": 1.5,
                "guidance_scale": 7.5,
            }
        }
        
        response = requests.post(url, headers=headers, json=inputs, timeout=120)
        
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            logger.warning(f"Image-to-image failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Image-to-image generation failed: {e}")
        return None


def _build_vibe_prompt(recipe_name: str, hook: str, vibe_keywords: list[str]) -> str:
    """
    Build a detailed prompt for image generation based on recipe and hook.
    
    Args:
        recipe_name: Name of the recipe
        hook: The Pinterest hook text
        vibe_keywords: Visual mood descriptors
        
    Returns:
        Detailed text prompt for image generation
    """
    base_prompt = f"""
    Professional food photography of {recipe_name}.
    Style: Pinterest-ready, appetizing, well-lit.
    Vibe: {', '.join(vibe_keywords)}.
    Context: {hook}.
    
    Technical details:
    - Shot from above (flat lay) or 45-degree angle
    - Natural lighting, soft shadows
    - Clean composition with negative space for text overlay
    - High quality, 4K, sharp focus
    - Color palette: warm, inviting, food-photography style
    - Professional food styling
    """
    
    return base_prompt.strip()


def generate_tailored_image(
    recipe_name: str,
    hook: str,
    vibe_prompt: str = "bright, appetizing, professional food photography",
    base_image: Optional[Image.Image] = None,
    fallback_image: Optional[Image.Image] = None,
    output_size: tuple[int, int] = (1000, 1500)
) -> Optional[Image.Image]:
    """
    STEP 5: Generate a tailored image for a specific Pinterest hook.
    
    Strategy:
    1. If base_image provided, use image-to-image transformation
    2. If no base_image or image-to-image fails, use text-to-image
    3. If both fail, return fallback_image
    
    Args:
        recipe_name: Name of the recipe
        hook: The Pinterest hook text
        vibe_prompt: Visual direction (comma-separated keywords)
        base_image: Optional original recipe image to transform
        fallback_image: Image to return if generation fails
        output_size: Target output size (width, height)
        
    Returns:
        PIL Image or fallback_image if generation fails
    """
    # Parse vibe keywords
    vibe_keywords = [k.strip() for k in vibe_prompt.split(',')]
    
    # Build detailed prompt
    detailed_prompt = _build_vibe_prompt(recipe_name, hook, vibe_keywords)
    negative_prompt = "text, watermark, blurry, low quality, dark, unappetizing, cluttered"
    
    logger.info(f"Generating tailored image for: {recipe_name} - {hook[:50]}...")
    
    generated_image = None
    
    # Try 1: Image-to-image if base image provided
    if base_image and HF_API_TOKEN:
        logger.info("Attempting image-to-image transformation...")
        img2img_prompt = f"Transform this food photo to look: {vibe_prompt}. Keep the main dish but adjust lighting, colors, and mood to match: {hook}"
        generated_image = _generate_with_image_to_image(base_image, img2img_prompt)
    
    # Try 2: Text-to-image if image-to-image failed or no base image
    if generated_image is None and HF_API_TOKEN:
        logger.info("Attempting text-to-image generation...")
        width, height = output_size
        generated_image = _generate_with_text_to_image(
            detailed_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height
        )
    
    # Resize to target size if successful
    if generated_image:
        generated_image = generated_image.resize(output_size, Image.Resampling.LANCZOS)
        logger.info("Successfully generated tailored image")
        return generated_image
    
    # Return fallback if all methods failed
    logger.warning("All generation methods failed, returning fallback")
    return fallback_image


def batch_generate_images(
    recipe_data: list[dict],
    output_dir: str = "generated_images"
) -> list[dict]:
    """
    Batch generate images for multiple recipes and their hooks.
    
    Args:
        recipe_data: List of dicts with keys: name, hook, vibe_prompt, base_image_path
        output_dir: Directory to save generated images
        
    Returns:
        List of results with paths to generated images
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for i, item in enumerate(recipe_data):
        try:
            # Load base image if provided
            base_img = None
            if item.get('base_image_path') and os.path.exists(item['base_image_path']):
                base_img = Image.open(item['base_image_path'])
            
            # Generate image
            generated = generate_tailored_image(
                recipe_name=item['name'],
                hook=item['hook'],
                vibe_prompt=item.get('vibe_prompt', 'bright, appetizing'),
                base_image=base_img
            )
            
            if generated:
                # Save image
                filename = f"{item['name'].replace(' ', '_')}_{i}.png"
                filepath = os.path.join(output_dir, filename)
                generated.save(filepath)
                
                results.append({
                    'recipe': item['name'],
                    'hook': item['hook'],
                    'image_path': filepath,
                    'success': True
                })
            else:
                results.append({
                    'recipe': item['name'],
                    'hook': item['hook'],
                    'image_path': None,
                    'success': False
                })
                
        except Exception as e:
            logger.error(f"Failed to generate image for {item.get('name')}: {e}")
            results.append({
                'recipe': item.get('name', 'unknown'),
                'hook': item.get('hook', ''),
                'image_path': None,
                'success': False,
                'error': str(e)
            })
    
    return results
