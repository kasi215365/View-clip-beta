import requests
import sys
import json
from datetime import datetime

class StreamingPlatformTester:
    def __init__(self, base_url="https://watch-interact-hub.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f" (Expected: {expected_status})"
                try:
                    error_data = response.json()
                    details += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f" - {response.text[:100]}"

            self.log_test(name, success, details)
            
            if success:
                try:
                    return response.json()
                except:
                    return {}
            return None

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return None

    def test_auth_flow(self):
        """Test complete authentication flow"""
        print("\n🔐 Testing Authentication...")
        
        # Test user registration
        timestamp = datetime.now().strftime('%H%M%S')
        test_user = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}",
            "role": "viewer"
        }
        
        register_result = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user
        )
        
        if register_result and 'token' in register_result:
            self.token = register_result['token']
            self.user_id = register_result['user']['id']
            
            # Test login with same credentials
            login_result = self.run_test(
                "User Login",
                "POST",
                "auth/login",
                200,
                data={"email": test_user["email"], "password": test_user["password"]}
            )
            
            # Test get current user
            self.run_test(
                "Get Current User",
                "GET",
                "auth/me",
                200
            )
            
            return True
        
        return False

    def test_content_management(self):
        """Test content management APIs"""
        print("\n📺 Testing Content Management...")
        
        # Test get all content
        self.run_test(
            "Get All Content",
            "GET",
            "content",
            200
        )
        
        # Test get content by type
        self.run_test(
            "Get Movies",
            "GET",
            "content?type=movie",
            200
        )
        
        self.run_test(
            "Get TV Shows",
            "GET",
            "content?type=tv-show",
            200
        )
        
        self.run_test(
            "Get Sports",
            "GET",
            "content?type=sport",
            200
        )

    def test_admin_content_creation(self):
        """Test admin content creation (requires admin role)"""
        print("\n👑 Testing Admin Content Creation...")
        
        # Register admin user
        timestamp = datetime.now().strftime('%H%M%S')
        admin_user = {
            "email": f"admin_{timestamp}@example.com",
            "password": "AdminPass123!",
            "name": f"Admin User {timestamp}",
            "role": "admin"
        }
        
        admin_result = self.run_test(
            "Admin Registration",
            "POST",
            "auth/register",
            200,
            data=admin_user
        )
        
        if admin_result and 'token' in admin_result:
            old_token = self.token
            self.token = admin_result['token']
            
            # Test content creation
            test_content = {
                "title": f"Test Movie {timestamp}",
                "description": "A test movie for API testing",
                "type": "movie",
                "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800",
                "duration": 3600
            }
            
            content_result = self.run_test(
                "Create Content (Admin)",
                "POST",
                "content",
                200,
                data=test_content
            )
            
            if content_result and 'id' in content_result:
                content_id = content_result['id']
                
                # Test get specific content
                self.run_test(
                    "Get Specific Content",
                    "GET",
                    f"content/{content_id}",
                    200
                )
                
                # Restore original token
                self.token = old_token
                
                # Test view increment
                self.run_test(
                    "Increment Content View",
                    "POST",
                    f"content/{content_id}/view",
                    200
                )
                
                return content_id
            
            self.token = old_token
        
        return None

    def test_streaming_functionality(self):
        """Test live streaming functionality"""
        print("\n📡 Testing Live Streaming...")
        
        # Test get all streams
        self.run_test(
            "Get All Streams",
            "GET",
            "streams",
            200
        )
        
        # Test get live streams
        self.run_test(
            "Get Live Streams",
            "GET",
            "streams?is_live=true",
            200
        )
        
        # Test get past streams
        self.run_test(
            "Get Past Streams",
            "GET",
            "streams?is_live=false",
            200
        )

    def test_streamer_functionality(self):
        """Test streamer-specific functionality"""
        print("\n🎥 Testing Streamer Functionality...")
        
        # Register streamer user
        timestamp = datetime.now().strftime('%H%M%S')
        streamer_user = {
            "email": f"streamer_{timestamp}@example.com",
            "password": "StreamerPass123!",
            "name": f"Streamer {timestamp}",
            "role": "streamer"
        }
        
        streamer_result = self.run_test(
            "Streamer Registration",
            "POST",
            "auth/register",
            200,
            data=streamer_user
        )
        
        if streamer_result and 'token' in streamer_result:
            old_token = self.token
            self.token = streamer_result['token']
            
            # Test subscription first (required for streaming)
            sub_result = self.run_test(
                "Streamer Subscription",
                "POST",
                "subscriptions/subscribe",
                200,
                data={"type": "streamer"}
            )
            
            if sub_result:
                # Test stream creation
                test_stream = {
                    "title": f"Test Stream {timestamp}",
                    "description": "A test live stream",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                    "thumbnail_url": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800"
                }
                
                stream_result = self.run_test(
                    "Create Live Stream",
                    "POST",
                    "streams",
                    200,
                    data=test_stream
                )
                
                if stream_result and 'id' in stream_result:
                    stream_id = stream_result['id']
                    
                    # Test get specific stream
                    self.run_test(
                        "Get Specific Stream",
                        "GET",
                        f"streams/{stream_id}",
                        200
                    )
                    
                    # Test earnings endpoints
                    self.run_test(
                        "Get Earnings",
                        "GET",
                        "earnings",
                        200
                    )
                    
                    self.run_test(
                        "Get Total Earnings",
                        "GET",
                        "earnings/total",
                        200
                    )
                    
                    # Test end stream
                    self.run_test(
                        "End Stream",
                        "POST",
                        f"streams/{stream_id}/end",
                        200
                    )
                    
                    # Test save stream
                    self.run_test(
                        "Save Stream",
                        "POST",
                        f"streams/{stream_id}/save",
                        200
                    )
                    
                    self.token = old_token
                    return stream_id
            
            self.token = old_token
        
        return None

    def test_subscription_flow(self):
        """Test subscription functionality"""
        print("\n💳 Testing Subscription Flow...")
        
        # Test viewer subscription
        viewer_sub = self.run_test(
            "Viewer Subscription",
            "POST",
            "subscriptions/subscribe",
            200,
            data={"type": "viewer"}
        )
        
        if viewer_sub:
            # Test subscription status
            self.run_test(
                "Get Subscription Status",
                "GET",
                "subscriptions/status",
                200
            )

    def test_interactive_features(self, stream_id=None):
        """Test chat and gifting features"""
        print("\n💬 Testing Interactive Features...")
        
        if stream_id:
            # Test comments
            comment_result = self.run_test(
                "Send Comment",
                "POST",
                "comments",
                200,
                data={"stream_id": stream_id, "text": "Great stream!"}
            )
            
            # Test get comments
            self.run_test(
                "Get Comments",
                "GET",
                f"comments/{stream_id}",
                200
            )
            
            # Test send gift
            self.run_test(
                "Send Gift",
                "POST",
                "gifts",
                200,
                data={"stream_id": stream_id, "amount": 5.0}
            )
            
            # Test join stream
            self.run_test(
                "Join Stream",
                "POST",
                f"streams/{stream_id}/join",
                200
            )

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Streaming Platform API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Test authentication first
        if not self.test_auth_flow():
            print("❌ Authentication failed - stopping tests")
            return False
        
        # Test content management
        self.test_content_management()
        
        # Test admin functionality
        content_id = self.test_admin_content_creation()
        
        # Test streaming functionality
        self.test_streaming_functionality()
        
        # Test subscription flow
        self.test_subscription_flow()
        
        # Test streamer functionality
        stream_id = self.test_streamer_functionality()
        
        # Test interactive features
        if stream_id:
            self.test_interactive_features(stream_id)
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = StreamingPlatformTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_reports/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': (tester.tests_passed/tester.tests_run)*100 if tester.tests_run > 0 else 0,
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())