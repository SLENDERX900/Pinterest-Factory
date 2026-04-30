"""
utils/image_generator.py - Free Hugging Face Image Generation
Implements $0 image generation using Hugging Face Inference API
"""

import requests
import io
import base64
from typing import List, Dict, Optional
import time
import os
from PIL import Image
import json

class HuggingFaceImageGenerator:
    """
    Free image generation using Hugging Face Inference API
    """
    
    def __init__(self):
        # Free Hugging Face models that work well for food/recipe images
        self.models = {
            "text2image": {
                "stable_diffusion": "runwayml/stable-diffusion-v1-5",  # Most reliable free model
                "dreamlike_art": "dreamlike-art/dreamlike-diffusion-1.0",  # Artistic style
                "realistic_vision": "SG161222/Realistic_Vision_V1.0",  # Realistic food photos
            },
            "image2image": {
                "stable_diffusion_img2img": "runwayml/stable-diffusion-v1-5",
                "instruct_pix2pix": "timbrooks/instruct-pix2pix",  # Instruction-based editing
            }
        }
        
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY', '')}",
            "Content-Type": "application/json"
        }
        
    def generate_hook_images(self, recipe_image_url: str, hooks: List[Dict]) -> List[Dict]:
        """
        Generate tailored images for each hook's vibe
        """
        print(f"🎨 Generating {len(hooks)} tailored images for hooks...")
        
        generated_images = []
        
        # Download the original recipe image
        try:
            original_image = self._download_image(recipe_image_url)
            print("✅ Original recipe image downloaded")
        except Exception as e:
            print(f"❌ Failed to download original image: {e}")
            # Generate text-to-image as fallback
            return self._generate_text_to_images_fallback(hooks)
        
        # Generate image for each hook
        for i, hook_data in enumerate(hooks):
            hook_text = hook_data.get('hook', '')
            vibe_prompt = hook_data.get('vibe_prompt', '')
            
            print(f"🎨 Generating image {i+1}/{len(hooks)}: {hook_text}")
            
            try:
                # Create enhanced prompt based on hook vibe
                enhanced_prompt = self._create_enhanced_prompt(hook_text, vibe_prompt)
                
                # Generate image using image-to-image
                generated_image = self._generate_image_to_image(
                    original_image, 
                    enhanced_prompt,
                    model=self.models["image2image"]["stable_diffusion_img2img"]
                )
                
                if generated_image:
                    image_data = {
                        'hook_index': i,
                        'hook_text': hook_text,
                        'vibe_prompt': vibe_prompt,
                        'enhanced_prompt': enhanced_prompt,
                        'image_base64': generated_image,
                        'generation_method': 'image2image',
                        'model_used': self.models["image2image"]["stable_diffusion_img2img"]
                    }
                    generated_images.append(image_data)
                    print(f"✅ Generated image {i+1}")
                else:
                    # Fallback to text-to-image
                    fallback_image = self._generate_text_to_image(enhanced_prompt)
                    if fallback_image:
                        image_data = {
                            'hook_index': i,
                            'hook_text': hook_text,
                            'vibe_prompt': vibe_prompt,
                            'enhanced_prompt': enhanced_prompt,
                            'image_base64': fallback_image,
                            'generation_method': 'text2image_fallback',
                            'model_used': self.models["text2image"]["stable_diffusion"]
                        }
                        generated_images.append(image_data)
                        print(f"✅ Fallback image {i+1} generated")
                    
            except Exception as e:
                print(f"❌ Error generating image {i+1}: {e}")
                continue
        
        print(f"🎉 Successfully generated {len(generated_images)} images")
        return generated_images
    
    def _download_image(self, image_url: str) -> Image.Image:
        """Download image from URL"""
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        image_bytes = io.BytesIO(response.content)
        image = Image.open(image_bytes)
        
        # Resize to standard size for processing
        image = image.resize((512, 512), Image.Resampling.LANCZOS)
        
        return image
    
    def _create_enhanced_prompt(self, hook_text: str, vibe_prompt: str) -> str:
        """
        Create enhanced prompt combining hook text and vibe
        """
        # Food photography style keywords
        style_keywords = [
            "professional food photography", "high quality", "detailed", 
            "vibrant colors", " appetizing", "restaurant quality", 
            "natural lighting", "shallow depth of field", "food styling"
        ]
        
        # Combine all elements
        prompt_parts = [
            hook_text,
            vibe_prompt,
            " ".join(style_keywords)
        ]
        
        # Clean and format prompt
        enhanced_prompt = ", ".join(filter(None, prompt_parts))
        
        # Add negative prompts for better results
        negative_prompt = "blurry, low quality, distorted, ugly, bad lighting, oversaturated, watermark, text, signature"
        
        return f"{enhanced_prompt}. Negative prompt: {negative_prompt}"
    
    def _generate_image_to_image(self, input_image: Image.Image, prompt: str, model: str) -> Optional[str]:
        """
        Generate image using image-to-image model
        """
        try:
            # Convert image to base64
            buffered = io.BytesIO()
            input_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Prepare API request
            payload = {
                "inputs": {
                    "prompt": prompt,
                    "image": image_base64,
                    "num_inference_steps": 20,
                    "guidance_scale": 7.5,
                    "strength": 0.8  # How much to change the original image
                }
            }
            
            response = requests.post(
                f"{self.api_url}/{model}",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                # Handle different response formats
                if response.headers.get('content-type', '').startswith('image/'):
                    # Direct image response
                    image_bytes = response.content
                    return base64.b64encode(image_bytes).decode()
                else:
                    # JSON response with base64 image
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        # Some models return the image directly
                        image_data = result[0] if isinstance(result[0], bytes) else result
                        if isinstance(image_data, bytes):
                            return base64.b64encode(image_data).decode()
                    elif isinstance(result, dict) and 'image' in result:
                        return result['image']
            
            print(f"⚠️ Image-to-image API response: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"❌ Image-to-image generation error: {e}")
            return None
    
    def _generate_text_to_image(self, prompt: str, model: str = None) -> Optional[str]:
        """
        Generate image using text-to-image model (fallback)
        """
        try:
            if not model:
                model = self.models["text2image"]["stable_diffusion"]
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": 25,
                    "guidance_scale": 7.5,
                    "width": 512,
                    "height": 512
                }
            }
            
            response = requests.post(
                f"{self.api_url}/{model}",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                # Handle image response
                if response.headers.get('content-type', '').startswith('image/'):
                    image_bytes = response.content
                    return base64.b64encode(image_bytes).decode()
                else:
                    # Try to parse as JSON
                    result = response.json()
                    if isinstance(result, bytes):
                        return base64.b64encode(result).decode()
            
            return None
            
        except Exception as e:
            print(f"❌ Text-to-image generation error: {e}")
            return None
    
    def _generate_text_to_images_fallback(self, hooks: List[Dict]) -> List[Dict]:
        """
        Generate text-to-image images when original image download fails
        """
        print("🔄 Using text-to-image fallback for all images...")
        
        generated_images = []
        
        for i, hook_data in enumerate(hooks):
            hook_text = hook_data.get('hook', '')
            vibe_prompt = hook_data.get('vibe_prompt', '')
            
            enhanced_prompt = self._create_enhanced_prompt(hook_text, vibe_prompt)
            
            try:
                image_base64 = self._generate_text_to_image(enhanced_prompt)
                
                if image_base64:
                    image_data = {
                        'hook_index': i,
                        'hook_text': hook_text,
                        'vibe_prompt': vibe_prompt,
                        'enhanced_prompt': enhanced_prompt,
                        'image_base64': image_base64,
                        'generation_method': 'text2image_fallback',
                        'model_used': self.models["text2image"]["stable_diffusion"]
                    }
                    generated_images.append(image_data)
                    print(f"✅ Fallback image {i+1} generated")
                
            except Exception as e:
                print(f"❌ Fallback image {i+1} failed: {e}")
                continue
        
        return generated_images
    
    def save_images_locally(self, generated_images: List[Dict], output_dir: str = "generated_images") -> List[str]:
        """
        Save generated images to local files
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []
        
        for i, image_data in enumerate(generated_images):
            try:
                # Decode base64 image
                image_bytes = base64.b64decode(image_data['image_base64'])
                image = Image.open(io.BytesIO(image_bytes))
                
                # Generate filename
                hook_text = image_data['hook_text'][:20].replace(" ", "_").replace("/", "_")
                filename = f"hook_{i+1}_{hook_text}_{int(time.time())}.png"
                filepath = os.path.join(output_dir, filename)
                
                # Save image
                image.save(filepath, 'PNG')
                saved_paths.append(filepath)
                
                print(f"💾 Saved image: {filename}")
                
            except Exception as e:
                print(f"❌ Error saving image {i+1}: {e}")
                continue
        
        return saved_paths

# Convenience function for easy integration
def generate_hook_images(recipe_image_url: str, hooks: List[Dict]) -> List[Dict]:
    """
    Convenience function to generate images for hooks
    """
    generator = HuggingFaceImageGenerator()
    return generator.generate_hook_images(recipe_image_url, hooks)
