import requests
import json
import os
import base64
from datetime import datetime
from PIL import Image, ImageDraw
import random
from google.cloud import storage
from openai import OpenAI

# ==================== CONFIGURATION ====================
# Instagram API Configuration
IG_ID = '17841468472081947'
ACCESS_TOKEN = 'EAALpn9BNFMkBP9cf3BB4z2WhhGIj0hmF4h1pwh7AU8mbnYWhjRkm2ZBQezWA5KfR1z1AMTkFNd1xqfjEznEZCLZAkvOpA5cEHrS2d7bBNl4YP1ZBzNGaHZAm5DUZA2Rxc2aObeu2mCpS1t52R6KpfhWK9IR6mdekham31ARmWuFlK1rDnwMLpmD6wS6CZBXOb7fEm1ZCZAziHd1RuMZBxPHzRSbXVwvHyFRc4VPILO4L0kRFQbcBM0Mpn4sfY9cAJBYSSdHtue7owGjZAfU9F3W8tqB'
API_VERSION = 'v24.0'
BASE_URL = f'https://graph.facebook.com/{API_VERSION}'

# Google Cloud Configuration
class SimpleGoogleCloudUploader:
    def __init__(self, bucket_name, credentials_path):
        """Simple Google Cloud uploader"""
        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            self.bucket_name = bucket_name
            
            # Ensure bucket is publicly accessible
            self.setup_bucket_permissions()
            
            print(f"✅ Google Cloud Storage connected - Bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ Google Cloud Storage initialization failed: {e}")
            self.client = None
            self.bucket = None

    def setup_bucket_permissions(self):
        """Set bucket permissions for public read access"""
        try:
            # Check if bucket is already publicly accessible
            policy = self.bucket.get_iam_policy()
            public_accessible = False
            
            for binding in policy.bindings:
                if binding['role'] == 'roles/storage.objectViewer' and 'allUsers' in binding['members']:
                    public_accessible = True
                    break
            
            if not public_accessible:
                print("🔄 Configuring bucket for public access...")
                # Add public read permission
                policy = self.bucket.get_iam_policy()
                policy.bindings.append({
                    'role': 'roles/storage.objectViewer',
                    'members': {'allUsers'}
                })
                self.bucket.set_iam_policy(policy)
                print("✅ Bucket configured for public access")
            else:
                print("✅ Bucket is already publicly accessible")
                
        except Exception as e:
            print(f"⚠️ Could not configure bucket permissions: {e}")

# Initialize Google Cloud Uploader
cloud_uploader = SimpleGoogleCloudUploader(
    bucket_name="eastonchau.com",
    credentials_path="total-velocity-467206-e8-34fc0a96437e.json"
)

# Initialize Qwen3 API Client
def init_qwen_client():
    """Initialize Qwen3 client"""
    try:
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  
        )
        print("✅ Qwen3 API client initialized successfully")
        return client
    except Exception as e:
        print(f"❌ Qwen3 API client initialization failed: {e}")
        return None

qwen_client = init_qwen_client()

# Constants
REQUIRED_IMAGES = 9

print("✅ Local Image Instagram Poster with Google Cloud Initialized")

# ==================== GOOGLE CLOUD FUNCTIONS ====================

def upload_to_google_cloud(local_image_path, cloud_folder="instagram_posts"):
    """Upload image to Google Cloud Storage and return public URL"""
    try:
        if not cloud_uploader.client:
            print("❌ Google Cloud client not initialized")
            return None
        
        # Generate cloud filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(local_image_path)
        cloud_filename = f"{cloud_folder}/{timestamp}_{filename}"
        
        print(f"📤 Uploading to Google Cloud: {cloud_filename}")
        
        # Upload file
        blob = cloud_uploader.bucket.blob(cloud_filename)
        blob.upload_from_filename(local_image_path)
        
        # For Uniform Bucket-Level Access, use public URL
        public_url = f"https://storage.googleapis.com/{cloud_uploader.bucket_name}/{cloud_filename}"
        
        print(f"✅ Image uploaded to Google Cloud: {cloud_filename}")
        print(f"🌐 Public URL: {public_url}")
        
        # Verify URL accessibility
        try:
            test_response = requests.head(public_url, timeout=10)
            if test_response.status_code == 200:
                print("✅ Public URL is accessible")
            else:
                print(f"⚠️ Public URL returned status: {test_response.status_code}")
        except Exception as e:
            print(f"⚠️ Could not verify URL accessibility: {e}")
        
        return public_url
        
    except Exception as e:
        print(f"❌ Google Cloud upload failed: {e}")
        return None

def test_google_cloud_connection():
    """Test Google Cloud connection"""
    try:
        if not cloud_uploader.client:
            print("❌ Google Cloud client not initialized")
            return False
        
        # Test listing files in bucket
        blobs = cloud_uploader.client.list_blobs(cloud_uploader.bucket_name, max_results=1)
        blob_count = sum(1 for _ in blobs)
        print(f"✅ Google Cloud connection test passed - Found {blob_count} blobs in bucket")
        return True
        
    except Exception as e:
        print(f"❌ Google Cloud connection test failed: {e}")
        return False

# ==================== IMAGE PROCESSING FUNCTIONS ====================

def combine_nine_images(image_paths, output_path):
    """Combine exactly 9 images into a 3x3 grid for Instagram post"""
    try:
        if len(image_paths) != 9:
            raise Exception("Exactly 9 images are required for 3x3 grid combination")
        
        print(f"🔄 Combining 9 images into 3x3 grid...")
        
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

# ==================== AI CAPTION GENERATION ====================

def generate_instagram_caption(sensor_data=None, image_count=9):
    """Generate Instagram caption using Qwen3"""
    try:
        if not qwen_client:
            print("⚠️ Qwen3 client not available, using fallback caption")
            return "🌿 Environmental Monitoring | 9 different perspectives showcasing our beautiful environment. Let's protect our planet together! 🌍 #Environment #Sustainability #EcoFriendly"
        
        if sensor_data is None:
            sensor_data = {}
        
        temperature = sensor_data.get('temperature', 'Unknown')
        humidity = sensor_data.get('humidity', 'Unknown')
        
        prompt = f"""
        You are an environmental KOL in Hong Kong. Create an engaging Instagram caption for a post showing {image_count} environmental monitoring images in a 3x3 grid.
        
        Environmental Data:
        - Temperature: {temperature}°C
        - Humidity: {humidity}%
        
        Create a compelling caption that:

        1. Includes the environmental data naturally
        2. Uses relevant emojis
        3. Encourages engagement about environmental protection
        4. Is 2-3 sentences maximum
        5. You must use English
        6. Don't change when others comment.
        
        Write in English with a friendly, educational tone.
        """
        
        completion = qwen_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a popular environmental influencer creating engaging Instagram captions. Use emojis and keep it concise but impactful."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        caption = completion.choices[0].message.content.strip()
        print(f"✅ Generated caption: {caption}")
        return caption
        
    except Exception as e:
        print(f"❌ AI caption generation failed: {e}")
        # Fallback caption
        return f"🌿 Environmental Monitoring | {image_count} different perspectives showcasing our environment. Every angle tells a story of our planet's health. 🌍 #EnvironmentalMonitoring #EcoAwareness #SustainableFuture"

# ==================== INSTAGRAM PUBLISHING ====================

def post_to_instagram(image_url, caption):
    """Post image to Instagram using the provided Instagram API code"""
    try:
        print(f"🔄 Posting to Instagram...")
        print(f"📝 Caption: {caption}")
        print(f"🖼️ Image URL: {image_url}")
        
        # Create container
        create_url = f'{BASE_URL}/{IG_ID}/media'
        params = {'image_url': image_url, 'caption': caption, 'access_token': ACCESS_TOKEN}
        response = requests.post(create_url, params=params)
        container_data = response.json()

        if response.status_code == 200:
            container_id = container_data['id']
            print(f"✅ Container created: {container_id}")
            
            # PUBLISH
            publish_url = f'{BASE_URL}/{IG_ID}/media_publish'
            publish_params = {'creation_id': container_id, 'access_token': ACCESS_TOKEN}
            publish_response = requests.post(publish_url, params=publish_params)
            
            if publish_response.status_code == 200:
                media_id = publish_response.json()['id']
                instagram_url = f"https://www.instagram.com/p/{media_id}/"
                print(f"✅ POSTED! {instagram_url}")
                return {
                    'success': True,
                    'media_id': media_id,
                    'url': instagram_url
                }
            else:
                error_msg = f"Publish failed: {publish_response.json()}"
                print(f"❌ {error_msg}")
                return {'error': error_msg}
        else:
            error_msg = f"Container creation failed: {response.json()}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}
            
    except Exception as e:
        print(f"❌ Instagram posting failed: {e}")
        return {'error': str(e)}

# ==================== MAIN POSTING FUNCTION ====================

def post_local_images_to_instagram(image_paths, sensor_data=None, auto_post=True):
    """Main function to process local images and post to Instagram via Google Cloud"""
    try:
        print("🚀 Starting local image Instagram post with Google Cloud...")
        
        # First test Google Cloud connection
        if not test_google_cloud_connection():
            return {'status': 'error', 'message': 'Google Cloud connection failed'}
        
        # Validate inputs
        if len(image_paths) != REQUIRED_IMAGES:
            return {
                'status': 'error',
                'message': f'Need exactly {REQUIRED_IMAGES} images, but got {len(image_paths)}'
            }
        
        # Check if all images exist
        missing_images = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                missing_images.append(img_path)
        
        if missing_images:
            return {
                'status': 'error', 
                'message': f'Missing images: {missing_images}'
            }
        
        print(f"✅ All {len(image_paths)} images found")
        
        # Create combined image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"instagram_post_{timestamp}.jpg"
        combined_image_path = f"output/{combined_filename}"
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Combine images into 3x3 grid
        combined_path = combine_nine_images(image_paths, combined_image_path)
        if not combined_path:
            return {'status': 'error', 'message': 'Failed to combine images'}
        
        print(f"✅ Combined image created: {combined_path}")
        
        # Upload combined image to Google Cloud
        cloud_image_url = upload_to_google_cloud(combined_path, "instagram_combined")
        if not cloud_image_url:
            return {'status': 'error', 'message': 'Failed to upload image to Google Cloud'}
        
        # Generate caption
        caption = generate_instagram_caption(sensor_data, len(image_paths))
        
        # Post to Instagram
        instagram_result = None
        if auto_post:
            instagram_result = post_to_instagram(cloud_image_url, caption)
        
        # Return results
        result = {
            'status': 'success',
            'message': f'Successfully processed {len(image_paths)} local images and posted to Instagram',
            'local_combined_image': combined_path,
            'cloud_image_url': cloud_image_url,
            'caption': caption,
            'instagram_post': instagram_result,
            'image_details': [os.path.basename(path) for path in image_paths]
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Local image posting failed: {e}")
        return {'status': 'error', 'message': str(e)}

# ==================== COMMAND LINE INTERFACE ====================

def find_images_in_folder(folder_path):
    """Find all image files in a folder"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    image_files = []
    
    for file in os.listdir(folder_path):
        file_lower = file.lower()
        if any(file_lower.endswith(ext) for ext in image_extensions):
            full_path = os.path.join(folder_path, file)
            image_files.append(full_path)
    
    return sorted(image_files)

def quick_post(folder_path, temperature=24, humidity=64):
    """Quick post function for automated use"""
    all_images = find_images_in_folder(folder_path)
    
    if len(all_images) < 9:
        print(f"❌ Need 9 images, but found {len(all_images)} in {folder_path}")
        return
    
    selected_images = all_images[:9]
    
    sensor_data = {
        'temperature': temperature,
        'humidity': humidity
    }
    
    print(f"🚀 Quick posting {len(selected_images)} images from {folder_path}")
    result = post_local_images_to_instagram(selected_images, sensor_data, auto_post=True)
    
    print(f"📊 Result: {result.get('message')}")
    if result.get('status') == 'success' and result.get('instagram_post', {}).get('success'):
        print(f"📱 Instagram: {result.get('instagram_post', {}).get('url')}")
    elif result.get('status') == 'success':
        print(f"📝 Caption: {result.get('caption')}")
        print(f"🖼️ Local Image: {result.get('local_combined_image')}")
        print(f"🌐 Cloud URL: {result.get('cloud_image_url')}")
    
    return result

def main():
    """Main program menu"""
    while True:
        print("\n" + "="*50)
        print("📱 LOCAL IMAGE INSTAGRAM POSTER")
        print("="*50)
        print("1. Quick Post (Use first 9 images in folder)")
        print("2. Test Google Cloud Connection")
        print("3. Exit")
        
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == '1':
            folder_path = input("Enter folder path: ").strip()
            if os.path.exists(folder_path):
                quick_post(folder_path)
            else:
                print("❌ Folder does not exist!")
        elif choice == '2':
            test_google_cloud_connection()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main()