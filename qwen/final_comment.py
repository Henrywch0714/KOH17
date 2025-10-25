import requests
import json
import time
import random
from openai import OpenAI
import os
from typing import List, Dict

class InstagramAIAutoReplier:
    def __init__(self):
        # API Configuration
        self.ACCESS_TOKEN = "EAALpn9BNFMkBP9cf3BB4z2WhhGIj0hmF4h1pwh7AU8mbnYWhjRkm2ZBQezWA5KfR1z1AMTkFNd1xqfjEznEZCLZAkvOpA5cEHrS2d7bBNl4YP1ZBzNGaHZAm5DUZA2Rxc2aObeu2mCpS1t52R6KpfhWK9IR6mdekham31ARmWuFlK1rDnwMLpmD6wS6CZBXOb7fEm1ZCZAziHd1RuMZBxPHzRSbXVwvHyFRc4VPILO4L0kRFQbcBM0Mpn4sfY9cAJBYSSdHtue7owGjZAfU9F3W8tqB"
        self.INSTAGRAM_USER_ID = "17841468472081947"
        self.base_url = "https://graph.facebook.com/v19.0"
        self.session = requests.Session()
        
        # Qwen3 Configuration
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  
        )
        
        # Automation Configuration
        self.reply_delay_min = 10  # Minimum delay (seconds)
        self.reply_delay_max = 30  # Maximum delay (seconds)
        self.max_replies_per_run = 5  # Maximum replies per run
        
        # Comment state management
        self.replied_comments_file = "replied_comments.json"
        self.pending_comments_file = "pending_comments.json"
        self.load_comment_states()
        
        print("✅ Instagram AI Auto-reply System Initialized")

    def load_comment_states(self):
        """Load comment states"""
        try:
            # Replied comments
            if os.path.exists(self.replied_comments_file):
                with open(self.replied_comments_file, 'r', encoding='utf-8') as f:
                    self.replied_comments = set(json.load(f))
            else:
                self.replied_comments = set()
            
            # Pending comments
            if os.path.exists(self.pending_comments_file):
                with open(self.pending_comments_file, 'r', encoding='utf-8') as f:
                    self.pending_comments = json.load(f)
            else:
                self.pending_comments = []
                
            print(f"✅ Loaded {len(self.replied_comments)} replied comments, {len(self.pending_comments)} pending comments")
            
        except Exception as e:
            print(f"❌ Failed to load comment states: {e}")
            self.replied_comments = set()
            self.pending_comments = []

    def save_comment_states(self):
        """Save comment states"""
        try:
            # Save replied comments
            with open(self.replied_comments_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.replied_comments), f, ensure_ascii=False, indent=2)
            
            # Save pending comments
            with open(self.pending_comments_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_comments, f, ensure_ascii=False, indent=2)
                
            print("💾 Comment states saved successfully")
            
        except Exception as e:
            print(f"❌ Failed to save comment states: {e}")

    def mark_comment_as_replied(self, comment_id: str, reply_text: str = ""):
        """Mark comment as replied"""
        self.replied_comments.add(comment_id)
        
        # Remove from pending list
        self.pending_comments = [c for c in self.pending_comments if c.get('id') != comment_id]
        
        self.save_comment_states()

    def add_to_pending_comments(self, comment_data: Dict):
        """Add to pending comments list"""
        # Check if already exists
        for comment in self.pending_comments:
            if comment.get('id') == comment_data.get('id'):
                return False
        
        self.pending_comments.append(comment_data)
        self.save_comment_states()
        return True

    def get_all_media(self, limit: int = 10) -> List[Dict]:
        """Get all media posts"""
        print(f"📸 Getting recent {limit} media posts...")
        
        params = {
            'fields': 'id,caption,media_type,comments_count',
            'limit': limit,
            'access_token': self.ACCESS_TOKEN
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/{self.INSTAGRAM_USER_ID}/media",
                params=params
            )
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"❌ Failed to get media: {e}")
            return []

    def get_media_comments(self, media_id: str) -> List[Dict]:
        """Get all comments under media"""
        params = {
            'fields': 'id,text,username,timestamp,like_count',
            'access_token': self.ACCESS_TOKEN
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/{media_id}/comments",
                params=params
            )
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"❌ Failed to get comments: {e}")
            return []

    def get_comment_replies(self, comment_id: str) -> List[Dict]:
        """Get comment replies (check if already replied)"""
        params = {
            'fields': 'id,text,username',
            'access_token': self.ACCESS_TOKEN
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/{comment_id}/replies",
                params=params
            )
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"❌ Failed to get replies: {e}")
            return []

    def is_already_replied(self, comment_id: str) -> bool:
        """Check if already replied (local check + API double check)"""
        # Local check
        if comment_id in self.replied_comments:
            return True
        
        # API check (ensure nothing is missed)
        try:
            replies = self.get_comment_replies(comment_id)
            for reply in replies:
                if reply.get('username') == 'keyopinionhiker':  # Your username
                    # If API found replied but local not recorded, update local record
                    self.mark_comment_as_replied(comment_id)
                    return True
        except Exception as e:
            print(f"⚠️ API check failed, using local cache: {e}")
        
        return False

    def generate_ai_reply(self, user_comment: str, username: str, post_caption: str = "") -> str:
        """Use Qwen3 to generate intelligent reply"""
        try:
            prompt = f"""
            You are an environmental KOL in Hong Kong, reply to Instagram comments in a casual and friendly tone, using emojis.
            
            Post Content: {post_caption}
            User Comment: "{user_comment}"
            Username: {username}
            
            Reply with a short, engaging sentence using relevant emojis. Be supportive and educational.
            Keep the reply to 1-2 sentences, natural and friendly.
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are a popular environmental influencer in Hong Kong. Reply to Instagram comments with short, friendly responses using emojis. You must use English. Replies should be natural and friendly, like chatting with friends."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
                temperature=0.8
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ AI reply generation failed: {e}")
            # Fallback replies
            fallback_replies = [
                "Thank you for your comment! 🌱 We will continue to work hard to protect the environment! 💚",
                "Thanks for your support! Let's work together for environmental protection! ♻️",
                "Thank you for your support! Hong Kong's environment will keep getting better! 🌳",
                "Thanks for your comment! Let's protect our planet together! 🌍"
            ]
            return random.choice(fallback_replies)

    def reply_to_comment(self, comment_id: str, reply_text: str) -> bool:
        """Reply to comment"""
        params = {
            'message': reply_text,
            'access_token': self.ACCESS_TOKEN
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/{comment_id}/replies",
                data=params
            )
            
            if response.status_code == 200:
                print(f"✅ Reply successful: {reply_text}")
                return True
            else:
                print(f"❌ Reply failed: {response.json()}")
                return False
                
        except Exception as e:
            print(f"❌ Reply request failed: {e}")
            return False

    def human_like_delay(self):
        """Simulate human-like delay"""
        delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
        print(f"⏳ Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def scan_for_new_comments(self) -> int:
        """Scan for new comments and add to pending list"""
        print("🔍 Scanning for new comments...")
        
        media_list = self.get_all_media(limit=10)
        new_comments_count = 0
        
        for media in media_list:
            comments = self.get_media_comments(media['id'])
            
            for comment in comments:
                comment_id = comment['id']
                
                # Check if already replied
                if self.is_already_replied(comment_id):
                    continue
                
                # Check if already in pending list
                already_pending = any(c.get('id') == comment_id for c in self.pending_comments)
                if already_pending:
                    continue
                
                # Add to pending list
                comment_data = {
                    'id': comment_id,
                    'text': comment.get('text', ''),
                    'username': comment.get('username', ''),
                    'media_id': media['id'],
                    'media_caption': media.get('caption', ''),
                    'timestamp': comment.get('timestamp', ''),
                    'scanned_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if self.add_to_pending_comments(comment_data):
                    print(f"📝 Added to pending: @{comment_data['username']} - {comment_data['text'][:50]}...")
                    new_comments_count += 1
        
        print(f"✅ Scan completed: {new_comments_count} new comments added to pending")
        return new_comments_count

    def process_pending_comments(self) -> int:
        """Process pending comments"""
        print(f"🔄 Processing {len(self.pending_comments)} pending comments...")
        
        processed_count = 0
        successful_replies = 0
        
        # Sort by time (reply to older comments first)
        sorted_pending = sorted(self.pending_comments, 
                              key=lambda x: x.get('timestamp', ''))
        
        for comment in sorted_pending:
            if processed_count >= self.max_replies_per_run:
                break
                
            comment_id = comment['id']
            username = comment['username']
            comment_text = comment['text']
            
            print(f"\n👤 Processing: @{username}")
            print(f"💬 Comment: {comment_text}")
            
            # Double check if already replied
            if self.is_already_replied(comment_id):
                print("⏭️ Already replied, removing from pending")
                self.mark_comment_as_replied(comment_id)
                continue
            
            # Generate AI reply
            ai_reply = self.generate_ai_reply(
                comment_text, 
                username, 
                comment.get('media_caption', '')
            )
            print(f"🤖 AI Reply: {ai_reply}")
            
            # Send reply
            if self.reply_to_comment(comment_id, ai_reply):
                successful_replies += 1
                self.mark_comment_as_replied(comment_id, ai_reply)
                print(f"✅ Reply successful ({successful_replies}/{self.max_replies_per_run})")
            else:
                print("❌ Reply failed, keeping in pending")
            
            processed_count += 1
            self.human_like_delay()
        
        return successful_replies

    def auto_reply_to_all_comments(self):
        """Auto-reply to all unreplied comments (new version)"""
        print("🚀 Starting enhanced auto-reply system...")
        
        # Step 1: Scan for new comments
        new_comments = self.scan_for_new_comments()
        
        # Step 2: Process pending comments
        successful_replies = self.process_pending_comments()
        
        # Show statistics
        print(f"\n📊 Statistics:")
        print(f"   New comments found: {new_comments}")
        print(f"   Successful replies: {successful_replies}")
        print(f"   Still pending: {len(self.pending_comments)}")
        print(f"   Total replied: {len(self.replied_comments)}")

    def reply_to_specific_media(self, media_id: str):
        """Reply to all comments on specific media"""
        print(f"🎯 Replying to comments on specific media {media_id}...")
        
        comments = self.get_media_comments(media_id)
        print(f"Found {len(comments)} comments")
        
        for i, comment in enumerate(comments, 1):
            if self.is_already_replied(comment['id']):
                print(f"⏭️ {i}. Already replied: @{comment['username']}")
                continue
            
            print(f"\n{i}. Replying to @{comment['username']}: {comment['text']}")
            
            ai_reply = self.generate_ai_reply(comment['text'], comment['username'])
            print(f"🤖 {ai_reply}")
            
            if self.reply_to_comment(comment['id'], ai_reply):
                self.mark_comment_as_replied(comment['id'], ai_reply)
                print("✅ Reply successful")
            else:
                print("❌ Reply failed")
            
            if i < len(comments):  # No delay for last one
                self.human_like_delay()

    def show_comment_stats(self):
        """Show comment statistics"""
        print(f"\n📈 Comment Statistics:")
        print(f"   Replied comments: {len(self.replied_comments)}")
        print(f"   Pending comments: {len(self.pending_comments)}")
        
        if self.pending_comments:
            print(f"\n⏳ Pending comments (showing first 5):")
            for i, comment in enumerate(self.pending_comments[:5], 1):
                print(f"   {i}. @{comment['username']}: {comment['text'][:60]}...")
        
        # Show recent replied comments
        if self.replied_comments:
            print(f"\n✅ Recently replied comments (count): {len(self.replied_comments)}")

    def clear_pending_comments(self):
        """Clear pending comments list"""
        confirm = input("Are you sure you want to clear all pending comments? (y/n): ")
        if confirm.lower() == 'y':
            self.pending_comments = []
            self.save_comment_states()
            print("✅ Pending comments cleared")
        else:
            print("❌ Operation cancelled")

    def export_comment_data(self):
        """Export comment data"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"comment_data_export_{timestamp}.json"
        
        data = {
            'export_time': timestamp,
            'replied_comments_count': len(self.replied_comments),
            'pending_comments_count': len(self.pending_comments),
            'replied_comments': list(self.replied_comments),
            'pending_comments': self.pending_comments
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Comment data exported to {filename}")

    def monitor_and_auto_reply(self, interval_minutes: int = 60):
        """Monitor and auto-reply to new comments"""
        print(f"🔍 Starting monitoring mode, checking every {interval_minutes} minutes...")
        
        while True:
            try:
                print(f"\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')} Checking for new comments...")
                self.auto_reply_to_all_comments()
                print(f"💤 Waiting {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n👋 Monitoring mode stopped")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(300)  # Wait 5 minutes after error

def main():
    """Main function"""
    bot = InstagramAIAutoReplier()
    
    while True:
        print("\n" + "="*50)
        print("🤖 Instagram AI Auto-reply System (Enhanced)")
        print("="*50)
        print("1. Scan for new comments only")
        print("2. Process pending comments only") 
        print("3. Scan & process all (full auto-reply)")
        print("4. Show comment statistics")
        print("5. Reply to specific media comments")
        print("6. Start monitoring mode")
        print("7. Clear pending comments")
        print("8. Export comment data")
        print("9. Test AI reply generation")
        print("0. Exit")
        
        choice = input("\nPlease choose operation (0-9): ").strip()
        
        if choice == '1':
            bot.scan_for_new_comments()
        elif choice == '2':
            bot.process_pending_comments()
        elif choice == '3':
            bot.auto_reply_to_all_comments()
        elif choice == '4':
            bot.show_comment_stats()
        elif choice == '5':
            media_id = input("Please enter media ID: ").strip()
            if media_id:
                bot.reply_to_specific_media(media_id)
        elif choice == '6':
            interval = input("Monitoring interval (minutes, default 60): ").strip()
            interval = int(interval) if interval.isdigit() else 60
            bot.monitor_and_auto_reply(interval)
        elif choice == '7':
            bot.clear_pending_comments()
        elif choice == '8':
            bot.export_comment_data()
        elif choice == '9':
            test_ai_reply(bot)
        elif choice == '0':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

def test_ai_reply(bot):
    """Test AI reply generation"""
    test_comments = [
        "Hong Kong's environmental work is really good!",
        "How to reduce plastic usage?",
        "Support environmental protection! Thanks for sharing",
        "Has air quality improved recently?",
        "Thanks for sharing this!"
    ]
    
    print("\n🧪 AI Reply Test:")
    for comment in test_comments:
        reply = bot.generate_ai_reply(comment, "test_user", "Environmental test post")
        print(f"💬 '{comment}'")
        print(f"🤖 '{reply}'\n")

if __name__ == "__main__":
    main()