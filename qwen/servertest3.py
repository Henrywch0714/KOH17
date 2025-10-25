# server.py - Complete integrated version optimized for 9 images
from flask import Flask, request, jsonify
import json
import os
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import random
from google.cloud import storage
import openai
from openai import OpenAI
import requests
import threading
import time


app = Flask(__name__)

# ==================== CONFIGURATION - NEEDS UPDATE ====================
# TODO: Update these configuration values with your actual credentials

class SimpleGoogleCloudUploader:
    def __init__(self, bucket_name, credentials_path):
        """Simple Google Cloud uploader"""
        try:
            # TODO: Update with your Google Cloud credentials path
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            self.bucket_name = bucket_name
            print(f"✅ Google Cloud Storage connected - Bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ Google Cloud Storage initialization failed: {e}")
            self.client = None
            self.bucket = None

# TODO: Update with your Google Cloud configuration
cloud_uploader = SimpleGoogleCloudUploader(
    bucket_name="eastonchau.com",  # CHANGE: Your bucket name
    credentials_path="total-velocity-467206-e8-34fc0a96437e.json"  # CHANGE: Your credentials file path
)

# Initialize Qwen3 API Client
def init_qwen_client():
    """Initialize Qwen3 client"""
    try:
        # TODO: Set DASHSCOPE_API_KEY in your environment variables
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),  # CHANGE: Your DashScope API key
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  
        )
        print("✅ Qwen3 API client initialized successfully")
        return client
    except Exception as e:
        print(f"❌ Qwen3 API client initialization failed: {e}")
        return None

qwen_client = init_qwen_client()

# Instagram API Configuration - NEEDS UPDATE
# TODO: Update with your Instagram Business Account credentials
IG_ID = '17841468472081947'  # CHANGE: Your Instagram Business Account ID
ACCESS_TOKEN = 'EAALpn9BNFMkBP4K3VcYQ7XpqMOHZCrElr6j3gLgDfX49hZCEheGSOZCacyQHc2Q1xUfkashjJcmSQDVVcEvDpOkJpkhXuLgXZAuh3NtIrHDFgIf5mkLfpyqmipMZA2c6YtZADpdTDa70LAmfPWQaqm2RCWsnZC2aGsEfcVeotFfdultTQnN9ZBBP4D3zYegZAac3AwffMIOdhYPrIapJSR6GBvfQTRVdDqvmi3jGKxrBVvU936OaP5OL0ZA6jcHD7QnteuMjAd3TAjSXhxMZBDF4XVD'  # CHANGE: Your long-lived access token
API_VERSION = 'v24.0'
BASE_URL = f'https://graph.facebook.com/{API_VERSION}'

# ==================== IMAGE PROCESSING CLASS ====================

class EnvironmentalDataProcessor:
    def __init__(self):
        self.data_file = "camera_sensor_data.json"
    
    def save_camera_image(self, image_data, image_number=1):
        """Save individual camera image with numbering"""
        try:
            # If it's base64 encoded image
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Read image using BytesIO
            image_stream = io.BytesIO(image_bytes)
            image = Image.open(image_stream)
            
            # Generate filename with numbering
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"camera_{timestamp}_{image_number:02d}.jpg"  # 01, 02, 03, etc.
            image_path = f"images/{filename}"
            
            # Ensure directory exists
            os.makedirs("images", exist_ok=True)
            
            # Convert image mode and save
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image.save(image_path, 'JPEG', quality=85)
            print(f"✅ Image {image_number} saved: {filename}")
            
            return image_path
            
        except Exception as e:
            print(f"❌ Image {image_number} saving failed: {e}")
            return None

    def get_data_status(self, image_count, sensor_data):
        """Get data completeness status"""
        status = []
        if image_count > 0:
            status.append(f"Has {image_count} Images")
        else:
            status.append("No Images")
            
        if sensor_data:
            status.append("Has Sensor Data")
        else:
            status.append("No Sensor Data")
            
        return " | ".join(status)

    def save_data_record(self, record):
        """Save data record"""
        try:
            # Read existing data
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
            
            # Add new record
            existing_data.append(record)
            
            # Save data
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Data record saved successfully")
            
        except Exception as e:
            print(f"❌ Data saving failed: {e}")

# Create processor instance
processor = EnvironmentalDataProcessor()

# ==================== IMAGE COMBINATION FUNCTIONS ====================

def combine_nine_images(image_paths, output_path):
    """Combine exactly 9 images into a 3x3 grid for Instagram post"""
    try:
        if len(image_paths) != 9:
            raise Exception("Exactly 9 images are required for 3x3 grid combination")
        
        print(f"🔄 Combining 9 images into 3x3 grid for Instagram post...")
        
        # Load all 9 images
        images = []
        for i, img_path in enumerate(image_paths):
            if os.path.exists(img_path):
                img = Image.open(img_path)
                images.append(img)
                print(f"✅ Loaded image {i+1}/9: {os.path.basename(img_path)}")
            else:
                raise Exception(f"Image not found: {img_path}")
        
        # Instagram recommended aspect ratio (4:5)
        instagram_width = 1080
        instagram_height = 1350
        
        # Create final canvas
        final_image = Image.new('RGB', (instagram_width, instagram_height), 'white')
        
        # 3x3 grid configuration
        grid_cols = 3
        grid_rows = 3
        cell_width = instagram_width // grid_cols
        cell_height = instagram_height // grid_rows
        
        # Add subtle border between cells
        border_size = 2
        
        # Place each image in the grid
        for i, img in enumerate(images):
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate position with borders
            x_position = col * cell_width + border_size
            y_position = row * cell_height + border_size
            actual_cell_width = cell_width - (2 * border_size)
            actual_cell_height = cell_height - (2 * border_size)
            
            # Resize image to fit cell
            resized_img = resize_to_fit(img, actual_cell_width, actual_cell_height)
            
            # Paste image in position
            final_image.paste(resized_img, (x_position, y_position))
        
        # Add outer border
        final_image = add_image_border(final_image, border_size=20, border_color='white')
        
        # Save final combined image
        final_image.save(output_path, 'JPEG', quality=95)
        print(f"✅ 3x3 grid image saved: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ 9-image combination failed: {e}")
        import traceback
        print(f"🔍 Detailed error: {traceback.format_exc()}")
        return None

def resize_to_fit(image, target_width, target_height):
    """Resize image to fit within target dimensions while maintaining aspect ratio"""
    img_ratio = image.width / image.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * img_ratio)
    
    resized_img = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    new_img = Image.new('RGB', (target_width, target_height), 'white')
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    new_img.paste(resized_img, (x_offset, y_offset))
    
    return new_img

def add_image_border(image, border_size=10, border_color='white'):
    """Add border around image"""
    try:
        new_width = image.width + (border_size * 2)
        new_height = image.height + (border_size * 2)
        bordered_image = Image.new('RGB', (new_width, new_height), border_color)
        bordered_image.paste(image, (border_size, border_size))
        return bordered_image
    except Exception as e:
        print(f"❌ Border addition failed: {e}")
        return image

def combine_multiple_images(image_paths, output_path):
    """Universal image combiner - automatically handles different numbers of images"""
    try:
        if not image_paths:
            raise Exception("No images provided for combination")
        
        # Special case: exactly 9 images - use 3x3 grid
        if len(image_paths) == 9:
            return combine_nine_images(image_paths, output_path)
        
        print(f"🔄 Combining {len(image_paths)} images...")
        
        # Load all images
        images = []
        for img_path in image_paths:
            if os.path.exists(img_path):
                img = Image.open(img_path)
                images.append(img)
                print(f"✅ Loaded image: {os.path.basename(img_path)}")
            else:
                print(f"⚠️ Image not found: {img_path}")
        
        if not images:
            raise Exception("No valid images to combine")
        
        # Instagram recommended aspect ratio (4:5)
        instagram_width = 1080
        instagram_height = 1350
        
        # Create final canvas
        final_image = Image.new('RGB', (instagram_width, instagram_height), 'white')
        
        # Choose layout based on number of images
        image_count = len(images)
        
        if image_count == 1:
            # Single image
            img = resize_to_fit(images[0], instagram_width, instagram_height)
            final_image.paste(img, (0, 0))
            
        elif image_count == 2:
            # Two images side by side
            img_width = instagram_width // 2
            for i, img in enumerate(images):
                img = resize_to_fit(img, img_width, instagram_height)
                x_position = i * img_width
                final_image.paste(img, (x_position, 0))
                
        elif image_count == 3:
            # One large on top, two small below
            top_img = resize_to_fit(images[0], instagram_width, instagram_height // 2)
            final_image.paste(top_img, (0, 0))
            
            bottom_width = instagram_width // 2
            bottom_height = instagram_height // 2
            
            for i, img in enumerate(images[1:3], 1):
                img = resize_to_fit(img, bottom_width, bottom_height)
                x_position = (i-1) * bottom_width
                y_position = instagram_height // 2
                final_image.paste(img, (x_position, y_position))
                
        elif image_count == 4:
            # 2x2 grid
            cell_width = instagram_width // 2
            cell_height = instagram_height // 2
            
            for i, img in enumerate(images):
                img = resize_to_fit(img, cell_width, cell_height)
                row = i // 2
                col = i % 2
                x_position = col * cell_width
                y_position = row * cell_height
                final_image.paste(img, (x_position, y_position))
                
        else:
            # For 5+ images (but not 9), use first 9 or adaptive layout
            if image_count > 9:
                print(f"⚠️ Using first 9 images out of {image_count}")
                return combine_nine_images(images[:9], output_path)
            else:
                # Use collage layout for 5-8 images
                return create_adaptive_collage(images, output_path, instagram_width, instagram_height)
        
        # Add border
        final_image = add_image_border(final_image, border_size=10)
        
        # Save final combined image
        final_image.save(output_path, 'JPEG', quality=95)
        print(f"✅ Combined image saved: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Image combination failed: {e}")
        import traceback
        print(f"🔍 Detailed error: {traceback.format_exc()}")
        return None

def create_adaptive_collage(images, output_path, width, height):
    """Create adaptive collage for 5-8 images"""
    try:
        image_count = len(images)
        print(f"🔄 Creating adaptive collage for {image_count} images...")
        
        # Create canvas
        final_image = Image.new('RGB', (width, height), 'white')
        
        if image_count == 5:
            # Top: 2 images, Middle: 1 image, Bottom: 2 images
            top_height = height // 3
            middle_height = height // 3
            bottom_height = height // 3
            
            # Top row - 2 images
            top_width = width // 2
            for i in range(2):
                img = resize_to_fit(images[i], top_width, top_height)
                x = i * top_width
                final_image.paste(img, (x, 0))
            
            # Middle row - 1 image
            middle_img = resize_to_fit(images[2], width, middle_height)
            final_image.paste(middle_img, (0, top_height))
            
            # Bottom row - 2 images
            for i in range(2):
                img = resize_to_fit(images[3 + i], top_width, bottom_height)
                x = i * top_width
                final_image.paste(img, (x, top_height + middle_height))
                
        elif image_count == 6:
            # 3x2 grid
            cols = 3
            rows = 2
            cell_width = width // cols
            cell_height = height // rows
            
            for i, img in enumerate(images):
                row = i // cols
                col = i % cols
                resized_img = resize_to_fit(img, cell_width, cell_height)
                x = col * cell_width
                y = row * cell_height
                final_image.paste(resized_img, (x, y))
                
        elif image_count == 7:
            # Top: 3 images, Middle: 1 image, Bottom: 3 images
            top_height = height // 3
            middle_height = height // 3
            bottom_height = height // 3
            
            # Top row - 3 images
            top_width = width // 3
            for i in range(3):
                img = resize_to_fit(images[i], top_width, top_height)
                x = i * top_width
                final_image.paste(img, (x, 0))
            
            # Middle row - 1 image
            middle_img = resize_to_fit(images[3], width, middle_height)
            final_image.paste(middle_img, (0, top_height))
            
            # Bottom row - 3 images
            for i in range(3):
                img = resize_to_fit(images[4 + i], top_width, bottom_height)
                x = i * top_width
                final_image.paste(img, (x, top_height + middle_height))
                
        elif image_count == 8:
            # 4x2 grid
            cols = 4
            rows = 2
            cell_width = width // cols
            cell_height = height // rows
            
            for i, img in enumerate(images):
                row = i // cols
                col = i % cols
                resized_img = resize_to_fit(img, cell_width, cell_height)
                x = col * cell_width
                y = row * cell_height
                final_image.paste(resized_img, (x, y))
        
        # Add border
        final_image = add_image_border(final_image, border_size=10)
        final_image.save(output_path, 'JPEG', quality=95)
        print(f"✅ Adaptive collage saved: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Adaptive collage creation failed: {e}")
        return None

# ==================== IMAGE ANALYSIS FUNCTIONS ====================

def encode_image_to_base64(image_path):
    """Encode image to base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Image encoding failed: {e}")
        return None

def analyze_multiple_images_with_qwen(image_paths):
    """Analyze multiple images individually and provide combined insights"""
    try:
        if not qwen_client:
            raise Exception("Qwen3 client not initialized")
        
        if not image_paths:
            return "No images available for analysis"
        
        print(f"🔄 Analyzing {len(image_paths)} individual images...")
        
        individual_analyses = []
        
        for i, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                print(f"⚠️ Image not found: {image_path}")
                continue
                
            image_name = os.path.basename(image_path)
            print(f"📊 Analyzing image {i+1}/{len(image_paths)}: {image_name}")
            
            base64_image = encode_image_to_base64(image_path)
            if not base64_image:
                individual_analyses.append(f"Image {i+1}: Analysis failed")
                continue
            
            prompt = f"""
Please analyze this image individually. Focus on:

1. Main visual content and subjects
2. Color scheme and lighting
3. Composition and perspective
4. Key visual elements that stand out
5. Overall mood and atmosphere

Provide a concise but detailed analysis in English.
"""
            
            response = qwen_client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            analysis = response.choices[0].message.content.strip()
            individual_analyses.append(f"Image {i+1} ({image_name}): {analysis}")
            print(f"✅ Analysis completed for image {i+1}")
        
        # Generate combined insights
        combined_analysis = generate_combined_insights(individual_analyses)
        
        return combined_analysis
        
    except Exception as e:
        print(f"❌ Multiple image analysis failed: {e}")
        return "Multiple image analysis temporarily unavailable"

def generate_combined_insights(individual_analyses):
    """Generate combined insights from individual image analyses"""
    try:
        if not qwen_client:
            return "\n".join(individual_analyses)
        
        analysis_text = "\n\n".join(individual_analyses)
        
        prompt = f"""
Based on the following individual analyses of multiple images, provide a comprehensive combined insight:

{analysis_text}

Please provide:
1. Overall theme or story that connects these images
2. Key visual patterns or contrasts between the images
3. How the images complement each other
4. The collective narrative they create

Keep the response concise but insightful in English.
"""
        
        response = qwen_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a visual analysis expert skilled at finding connections and narratives across multiple images."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=400
        )
        
        combined_insights = response.choices[0].message.content.strip()
        return f"Individual Analyses:\n{analysis_text}\n\nCombined Insights:\n{combined_insights}"
        
    except Exception as e:
        print(f"❌ Combined insights generation failed: {e}")
        return "\n".join(individual_analyses)

# ==================== CAPTION GENERATION FUNCTIONS ====================

def generate_instagram_caption_with_qwen(record, image_paths=None):
    """Generate Instagram caption using Qwen3 API based on multiple image contents and environmental data"""
    try:
        if not qwen_client:
            raise Exception("Qwen3 client not initialized")
            
        # Prepare environmental data
        sensor_data = record.get('sensor_data', {})
        temperature = sensor_data.get('temperature', 'Unknown')
        humidity = sensor_data.get('humidity', 'Unknown')
        data_status = record.get('data_status', '')
        
        # Get image information
        image_count = len(image_paths) if image_paths else 0
        image_names = [os.path.basename(path) for path in image_paths] if image_paths else ["Environmental Monitoring"]
        
        # Analyze multiple images
        combined_image_analysis = ""
        if image_paths and any(os.path.exists(path) for path in image_paths):
            print(f"🔄 Analyzing {len(image_paths)} individual images...")
            combined_image_analysis = analyze_multiple_images_with_qwen(image_paths)
        else:
            combined_image_analysis = "Environmental monitoring data visualization from multiple perspectives"
        
        # Build detailed prompt for multiple images
        prompt = f"""
You are a professional Instagram content creator. Please create engaging captions and descriptions for a post that combines {image_count} environmental monitoring images.

【MULTIPLE IMAGE INFORMATION】
- Number of Images: {image_count}
- Image Names: {', '.join(image_names)}
- Combined Image Analysis: {combined_image_analysis}

【ENVIRONMENTAL MONITORING DATA】
- Temperature: {temperature}°C
- Humidity: {humidity}%
- Data Status: {data_status}

【CREATION REQUIREMENTS】
Please generate 3 different style options for a complete Instagram post that showcases multiple environmental perspectives. Each option should include:

📌 MAIN TITLE (concise, powerful, with relevant emojis, under 15 words)
📝 DETAILED DESCRIPTION (2-3 sentences, naturally combining the multiple image perspectives and environmental data)
🏷️ RELEVANT HASHTAGS (5-8 precise hashtags)

Three style requirements:
1. Scientific Comprehensive Style - Focus on comprehensive data analysis from multiple angles
2. Visual Storytelling Style - Focus on the visual narrative created by multiple images
3. Environmental Documentary Style - Focus on documenting environmental conditions from different perspectives

Since this post combines multiple images, emphasize:
- The comprehensive view provided by multiple images
- How different angles/perspectives complement each other
- The complete environmental story being told

Format example:
【Option 1 - Scientific Comprehensive】
🌡️ Multi-Angle Environmental Analysis | {temperature}°C
Comprehensive environmental monitoring from {image_count} different perspectives, showing consistent data: temperature {temperature}°C, humidity {humidity}% across all views.
#EnvironmentalScience #MultiAngle #DataAnalysis #Temperature{temperature} #ComprehensiveMonitoring

Please start creating:
"""
        
        # Call Qwen3 API
        response = qwen_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a professional social media content creator specializing in:
1. Creating compelling narratives from multiple images
2. Skillfully combining environmental data with visual storytelling
3. Creating English content suitable for Instagram platform
4. Using appropriate emojis and hashtags for multi-image posts"""
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=1200,
            temperature=0.8
        )
        
        # Extract generated caption options
        caption_options = response.choices[0].message.content.strip()
        print(f"✅ Qwen3 generated multi-image caption options:\n{caption_options}")
        
        return caption_options
        
    except Exception as e:
        print(f"❌ Qwen3 API call failed: {e}")
        return generate_fallback_multiple_image_caption(record, image_paths)

def generate_fallback_multiple_image_caption(record, image_paths):
    """Generate fallback caption for multiple images (when API call fails)"""
    sensor_data = record.get('sensor_data', {})
    temperature = sensor_data.get('temperature', 'Unknown')
    humidity = sensor_data.get('humidity', 'Unknown')
    
    image_count = len(image_paths) if image_paths else 0
    
    return f"""
【Option 1 - Scientific Comprehensive】
🌡️ {image_count}-Angle Environmental Monitoring | {temperature}°C
Comprehensive environmental data from {image_count} different perspectives. Consistent readings: temperature {temperature}°C, humidity {humidity}%.
#EnvironmentalMonitoring #MultiPerspective #DataAnalysis #Temperature{temperature} #ComprehensiveData

【Option 2 - Visual Storytelling】  
📸 Environmental Story in {image_count} Frames | {temperature}°C
Telling the complete environmental story through {image_count} different views. Current conditions: {temperature}°C, {humidity}% humidity.
#VisualStorytelling #EnvironmentalViews #MultiFrame #{image_count}Perspectives #ClimateDocumentary

【Option 3 - Environmental Documentary】
🌍 Environmental Documentation | {image_count} Views
Documenting environmental conditions from multiple angles. Recorded data: temperature {temperature}°C, humidity {humidity}%.
#EnvironmentalDocumentary #MultiAngle #ClimateRecord #SustainableMonitoring #EcoDocumentation
"""

def generate_instagram_caption(record):
    """Generate Instagram caption (based on image content and environmental data)"""
    try:
        # Get individual image paths
        individual_image_paths = record.get('individual_image_paths', [])
        # Generate caption options using Qwen3
        caption_options = generate_instagram_caption_with_qwen(record, individual_image_paths)
        # Parse and select the first option's main title
        selected_caption = parse_first_caption(caption_options)
        return selected_caption
    except Exception as e:
        print(f"❌ Caption generation failed, using fallback: {e}")
        sensor_data = record.get('sensor_data', {})
        temperature = sensor_data.get('temperature', 'Unknown')
        humidity = sensor_data.get('humidity', 'Unknown')
        
        image_count = len(record.get('individual_image_paths', []))
        image_name = f"{image_count}-Image Environmental Monitoring"
        
        return f"🌿 {image_name} | Temperature: {temperature}°C | Humidity: {humidity}%"

def parse_first_caption(caption_options):
    """Parse the first caption from generated options"""
    try:
        lines = caption_options.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # Find the first title line containing emoji and pipe symbol
            if '|' in line and any(char in line for char in ['🌡️', '🌿', '🌍', '📊', '📷']):
                return line
            # Or find the section starting with 【Option 1】
            elif line.startswith('【Option 1'):
                # Return the next line as title
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        
        # If not found, return first non-empty content
        for line in lines:
            if line.strip() and not line.startswith('【'):
                return line.strip()
                
    except Exception as e:
        print(f"❌ Caption parsing failed: {e}")
    
    return "Environmental Monitoring Data Update"

# ==================== INSTAGRAM PUBLISHING FUNCTIONS ====================

def post_to_instagram(image_path, caption):
    """Post image to Instagram"""
    try:
        # Get image URL (using existing cloud storage functionality)
        if image_path.startswith(('http://', 'https://')):
            image_url = image_path
        else:
            # Upload to cloud storage
            cloud_url = cloud_uploader.upload_processed_image(image_path)
            if cloud_url:
                image_url = convert_to_public_url(cloud_url)
            else:
                return {'error': 'Unable to upload image to cloud storage'}
        
        print(f"🔄 Preparing to post to Instagram, Image URL: {image_url}")
        print(f"📝 Caption: {caption}")
        
        # Create container
        create_url = f'{BASE_URL}/{IG_ID}/media'
        params = {
            'image_url': image_url, 
            'caption': caption,
            'access_token': ACCESS_TOKEN
        }
        
        response = requests.post(create_url, params=params)
        container_data = response.json()
        
        if response.status_code == 200:
            container_id = container_data['id']
            print(f"✅ Instagram container created successfully: {container_id}")
            
            # Publish
            publish_url = f'{BASE_URL}/{IG_ID}/media_publish'
            publish_params = {
                'creation_id': container_id, 
                'access_token': ACCESS_TOKEN
            }
            
            publish_response = requests.post(publish_url, params=publish_params)
            if publish_response.status_code == 200:
                media_id = publish_response.json()['id']
                instagram_url = f"https://www.instagram.com/p/{media_id}/"
                print(f"✅ Instagram post successful: {instagram_url}")
                return {
                    'success': True,
                    'media_id': media_id,
                    'url': instagram_url
                }
            else:
                error_msg = f"Publishing failed: {publish_response.json()}"
                print(f"❌ {error_msg}")
                return {'error': error_msg}
        else:
            error_msg = f"Container creation failed: {response.json()}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}
            
    except Exception as e:
        error_msg = f"Instagram posting exception: {e}"
        print(f"❌ {error_msg}")
        return {'error': error_msg}

def convert_to_public_url(cloud_url):
    """Convert cloud storage URL to publicly accessible URL"""
    if cloud_url.startswith('gs://'):
        bucket_path = cloud_url[5:]  # Remove 'gs://'
        bucket_name, object_path = bucket_path.split('/', 1)
        return f"https://storage.googleapis.com/{bucket_name}/{object_path}"
    return cloud_url

# ==================== MAIN DATA PROCESSING FUNCTION ====================

def process_multiple_camera_data(image_data_list, sensor_data, require_min_images=9):
    """Process multiple camera images and sensor data - requires minimum 9 images"""
    try:
        print(f"🔄 Processing {len(image_data_list)} camera images...")
        
        # Check if we have enough images
        if len(image_data_list) < require_min_images:
            error_msg = f"Insufficient images: received {len(image_data_list)}, required {require_min_images}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        # Save all individual images
        individual_image_paths = []
        for i, image_data in enumerate(image_data_list):
            if image_data:
                image_path = processor.save_camera_image(image_data, i+1)
                if image_path and image_path != "failed_to_save":
                    individual_image_paths.append(image_path)
                    print(f"✅ Saved individual image {i+1}: {os.path.basename(image_path)}")
        
        # Check if we have exactly 9 images for optimal layout
        image_count = len(individual_image_paths)
        if image_count == 9:
            print("🎯 Perfect! 9 images detected - creating optimized 3x3 grid")
        elif image_count > 9:
            print(f"⚠️ {image_count} images received, using first 9 for 3x3 grid")
            individual_image_paths = individual_image_paths[:9]
        else:
            # This should not happen due to the check above, but just in case
            error_msg = f"After processing: {image_count} valid images, but required {require_min_images}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        # Generate combined image for Instagram post (always 3x3 grid)
        combined_image_path = None
        if individual_image_paths:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_filename = f"combined_instagram_{timestamp}.jpg"
            combined_image_path = f"reports/{combined_filename}"
            os.makedirs("reports", exist_ok=True)
            
            # Always use 3x3 grid for exactly 9 images
            combined_image_path = combine_nine_images(individual_image_paths, combined_image_path)
        
        # Upload combined image to cloud storage
        cloud_report_url = None
        if combined_image_path and cloud_uploader.client:
            cloud_report_url = cloud_uploader.upload_processed_image(combined_image_path)
            if cloud_report_url:
                print(f"✅ Combined image uploaded to cloud storage: {cloud_report_url}")
        
        # Create complete data record
        record = {
            'individual_image_paths': individual_image_paths,
            'combined_image_path': combined_image_path,
            'cloud_report_url': cloud_report_url,
            'image_timestamp': datetime.now().isoformat(),
            'sensor_data': sensor_data or {},
            'processed_at': datetime.now().isoformat(),
            'data_status': processor.get_data_status(len(individual_image_paths), sensor_data)
        }
        
        # Save data record
        processor.save_data_record(record)
        
        print(f"✅ Multiple image processing completed - Individual: {len(individual_image_paths)} images, Combined: {combined_image_path}")
        return record, combined_image_path, individual_image_paths
        
    except Exception as e:
        print(f"❌ Multiple image processing error: {e}")
        import traceback
        print(f"🔍 Detailed error: {traceback.format_exc()}")
        
        error_record = {
            'error': str(e),
            'sensor_data': sensor_data or {},
            'processed_at': datetime.now().isoformat(),
            'data_status': 'error'
        }
        
        return error_record, None, []

# ==================== FLASK API ENDPOINTS ====================

@app.route('/')
def home():
    return jsonify({
        'message': 'Environmental Monitoring Server Running',
        'status': 'active',
        'endpoints': {
            'Health Check': '/api/health',
            'Test Connection': '/api/test-simple', 
            'Receive Data': '/api/camera-sensor-data',
            'File List': '/api/files',
            'Cloud Files': '/api/cloud/files',
            'Image Analysis Test': '/api/test-image-analysis',
            'Manual Instagram Post': '/api/post-to-instagram'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy', 
        'message': 'Server running normally',
        'timestamp': datetime.now().isoformat()
    })

# Add these global variables to manage image collection
image_collection_buffer = []
last_collection_time = None
COLLECTION_TIMEOUT = 30  # seconds - wait up to 30 seconds for 9 images
REQUIRED_IMAGES = 9

@app.route('/api/camera-sensor-data', methods=['POST'])
def receive_camera_sensor_data():
    """Receive multiple camera images and sensor data - waits for exactly 9 images"""
    global image_collection_buffer, last_collection_time
    
    try:
        # Get complete data
        data = request.json
        print("📡 Received camera images and sensor data")
        
        # Extract data
        image_data_list = data.get('image_data_list', [])
        sensor_data = data.get('sensor_data', {})
        auto_post = data.get('auto_post', False)
        
        print(f"🔍 Data check - Images in this batch: {len(image_data_list)}, Total in buffer: {len(image_collection_buffer)}, Auto Post: {auto_post}")
        
        # Add new images to buffer
        image_collection_buffer.extend(image_data_list)
        last_collection_time = datetime.now()
        
        # Check if we have enough images
        if len(image_collection_buffer) >= REQUIRED_IMAGES:
            print(f"🎯 Collected {len(image_collection_buffer)} images, processing {REQUIRED_IMAGES} for Instagram post")
            
            # Take exactly REQUIRED_IMAGES from buffer
            images_to_process = image_collection_buffer[:REQUIRED_IMAGES]
            
            # Process multiple images (requires exactly 9 images)
            record, combined_image_path, individual_image_paths = process_multiple_camera_data(
                images_to_process, sensor_data, require_min_images=REQUIRED_IMAGES
            )
            
            # Clear the buffer after successful processing
            image_collection_buffer = image_collection_buffer[REQUIRED_IMAGES:]
            print(f"🔄 Buffer updated: {len(image_collection_buffer)} images remaining")
            
            # Add paths to record for caption generation
            record['combined_image_path'] = combined_image_path
            record['individual_image_paths'] = individual_image_paths
            
            # Generate caption based on multiple image contents using Qwen3
            caption_options = generate_instagram_caption(record)
            selected_caption = parse_first_caption(caption_options)
            
            print(f"📝 Final selected caption: {selected_caption}")
            
            # If auto post enabled and combined image generated successfully
            instagram_result = None
            if auto_post and combined_image_path and os.path.exists(combined_image_path):
                print("🔄 Attempting to post combined 9-image grid to Instagram...")
                instagram_result = post_to_instagram(combined_image_path, selected_caption)
            
            # Return success response
            response_data = {
                'status': 'success',
                'individual_images_count': len(individual_image_paths),
                'combined_image': combined_image_path,
                'cloud_report_url': record.get('cloud_report_url'),
                'data_status': record.get('data_status', 'unknown'),
                'message': f'Successfully processed {len(individual_image_paths)} images into 3x3 Instagram grid',
                'selected_caption': selected_caption,
                'instagram_post': instagram_result,
                'layout_type': '3x3 grid',
                'images_remaining_in_buffer': len(image_collection_buffer)
            }
            
            return jsonify(response_data)
        else:
            # Not enough images yet, wait for more
            images_needed = REQUIRED_IMAGES - len(image_collection_buffer)
            return jsonify({
                'status': 'collecting',
                'message': f'Collecting images... {len(image_collection_buffer)}/{REQUIRED_IMAGES} received',
                'images_received': len(image_collection_buffer),
                'images_needed': images_needed,
                'buffer_status': 'waiting_for_more_images'
            })
        
    except Exception as e:
        print(f"❌ Data reception error: {e}")
        import traceback
        print(f"🔍 Detailed error: {traceback.format_exc()}")
        return jsonify({'error': f'Server processing error: {str(e)}'}), 500

@app.route('/api/cloud/files', methods=['GET'])
def list_cloud_files():
    """List files in cloud storage"""
    try:
        if not cloud_uploader.client:
            return jsonify({'error': 'Cloud storage not configured'}), 500
            
        prefix = request.args.get('prefix', 'processed_images')
        files = []
        
        # Get cloud storage file list
        blobs = cloud_uploader.client.list_blobs(cloud_uploader.bucket_name, prefix=prefix)
        for blob in blobs:
            files.append({
                'name': blob.name,
                'size': blob.size,
                'updated': blob.updated.isoformat() if blob.updated else None
            })
        
        return jsonify({
            'status': 'success',
            'bucket': cloud_uploader.bucket_name,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-image-analysis', methods=['POST'])
def test_image_analysis():
    """Test image analysis functionality"""
    try:
        data = request.json
        image_paths = data.get('image_paths', [])
        
        if not image_paths:
            return jsonify({'error': 'No image paths provided'}), 400
        
        # Check if images exist
        valid_paths = [path for path in image_paths if os.path.exists(path)]
        if not valid_paths:
            return jsonify({'error': 'No valid image paths found'}), 400
        
        print(f"🔄 Testing combination of {len(valid_paths)} images...")
        
        # Combine images
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_path = f"reports/test_combined_{timestamp}.jpg"
        combined_result = combine_multiple_images(valid_paths, combined_path)
        
        # Analyze individual images
        analysis_result = analyze_multiple_images_with_qwen(valid_paths)
        
        # Generate caption
        test_record = {
            'sensor_data': {'temperature': 25.5, 'humidity': 60},
            'data_status': f'Test with {len(valid_paths)} images'
        }
        caption_options = generate_instagram_caption_with_qwen(test_record, valid_paths)
        
        return jsonify({
            'status': 'success',
            'individual_images': valid_paths,
            'combined_image': combined_result,
            'image_analysis': analysis_result,
            'caption_options': caption_options,
            'image_count': len(valid_paths)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/post-to-instagram', methods=['POST'])
def manual_post_to_instagram():
    """Manual post to Instagram"""
    try:
        data = request.json
        image_path = data.get('image_path')
        caption = data.get('caption')
        
        if not image_path or not caption:
            return jsonify({'error': 'Missing image path or caption'}), 400
        
        result = post_to_instagram(image_path, caption)
        
        return jsonify({
            'status': 'success' if result.get('success') else 'error',
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# 添加新的端点专门处理单次9张图片
@app.route('/api/process-nine-images', methods=['POST'])
def process_nine_images_directly():
    """Process exactly 9 images in one request"""
    try:
        data = request.json
        image_data_list = data.get('image_data_list', [])
        sensor_data = data.get('sensor_data', {})
        auto_post = data.get('auto_post', True)  # 默认自动发布
        
        # 严格检查必须是9张图片
        if len(image_data_list) != REQUIRED_IMAGES:
            return jsonify({
                'status': 'error',
                'message': f'This endpoint requires exactly {REQUIRED_IMAGES} images, but received {len(image_data_list)}',
                'required': REQUIRED_IMAGES,
                'received': len(image_data_list)
            }), 400
        
        print(f"🎯 Direct processing of {REQUIRED_IMAGES} images for Instagram")
        
        # 处理9张图片
        record, combined_image_path, individual_image_paths = process_multiple_camera_data(
            image_data_list, sensor_data, require_min_images=REQUIRED_IMAGES
        )
        
        # 生成标题和发布
        record['combined_image_path'] = combined_image_path
        record['individual_image_paths'] = individual_image_paths
        
        caption_options = generate_instagram_caption(record)
        selected_caption = parse_first_caption(caption_options)
        
        instagram_result = None
        if auto_post and combined_image_path and os.path.exists(combined_image_path):
            print("🔄 Posting to Instagram...")
            instagram_result = post_to_instagram(combined_image_path, selected_caption)
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully processed and posted {REQUIRED_IMAGES} images',
            'combined_image': combined_image_path,
            'selected_caption': selected_caption,
            'instagram_post': instagram_result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
def cleanup_image_buffer():
    """Periodically clean up old images in buffer"""
    global image_collection_buffer, last_collection_time
    
    while True:
        time.sleep(60)  # Check every minute
        
        if last_collection_time and image_collection_buffer:
            time_since_last = (datetime.now() - last_collection_time).total_seconds()
            
            if time_since_last > COLLECTION_TIMEOUT:
                print(f"🕒 Buffer timeout: {len(image_collection_buffer)} images discarded (no new images for {COLLECTION_TIMEOUT}s)")
                image_collection_buffer = []
                last_collection_time = None

# Start cleanup thread when server starts
cleanup_thread = threading.Thread(target=cleanup_image_buffer, daemon=True)
cleanup_thread.start()
if __name__ == '__main__':
    print("🚀 Starting Environmental Monitoring Server...")
    print("🎯 Optimized for 9-image 3x3 grid combinations")
    os.makedirs("images", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
