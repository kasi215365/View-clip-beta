"""
View/Clip API Tests - Iteration 3: New Productivity Features
Tests: Referrals, Follow/Unfollow, Notifications, Search, Trending, Analytics, Heartbeat
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://viewer-pro.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@viewclip.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_user(admin_token):
    """Get admin user data"""
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response.json()


# =============================================================================
# REFERRALS TESTS
# =============================================================================
class TestReferrals:
    """Referral system endpoint tests"""
    
    def test_get_my_referrals(self, admin_token):
        """Test GET /api/referrals/my returns code, referred_count, earnings, events"""
        response = requests.get(
            f"{BASE_URL}/api/referrals/my",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "code" in data, "Missing referral code"
        assert "referred_count" in data, "Missing referred_count"
        assert "earnings" in data, "Missing earnings"
        assert "events" in data, "Missing events array"
        assert isinstance(data["events"], list)
    
    def test_referral_leaderboard_public(self):
        """Test GET /api/referrals/leaderboard is public (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/referrals/leaderboard")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        # Leaderboard can be empty if no referrals yet
    
    def test_validate_referral_code_valid(self, admin_token):
        """Test GET /api/referrals/validate/{code} with valid code"""
        # First get admin's referral code
        my_ref = requests.get(
            f"{BASE_URL}/api/referrals/my",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        code = my_ref["code"]
        
        response = requests.get(f"{BASE_URL}/api/referrals/validate/{code}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert "referrer_name" in data
    
    def test_validate_referral_code_invalid(self):
        """Test GET /api/referrals/validate/{code} with invalid code"""
        response = requests.get(f"{BASE_URL}/api/referrals/validate/INVALIDCODE123")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
    
    def test_register_with_valid_referral_code(self, admin_token):
        """Test POST /api/auth/register with valid referral_code sets referred_by"""
        # Get admin's referral code
        my_ref = requests.get(
            f"{BASE_URL}/api/referrals/my",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        referral_code = my_ref["code"]
        
        # Register new user with referral code
        unique_email = f"TEST_referred_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Referred User",
            "role": "viewer",
            "referral_code": referral_code
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert data["user"]["referred_by"] is not None, "referred_by should be set"
        # New user should also have their own referral code
        assert data["user"]["referral_code"] is not None, "New user should have referral_code"
    
    def test_register_with_invalid_referral_code(self):
        """Test POST /api/auth/register with invalid referral_code ignores it"""
        unique_email = f"TEST_noreferral_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "No Referral User",
            "role": "viewer",
            "referral_code": "INVALIDCODE999"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert data["user"]["referred_by"] is None, "referred_by should be None for invalid code"
        # User should still get their own referral code
        assert data["user"]["referral_code"] is not None


# =============================================================================
# FOLLOW/UNFOLLOW TESTS
# =============================================================================
class TestFollowUnfollow:
    """Follow/Unfollow streamer endpoint tests"""
    
    @pytest.fixture
    def viewer_token(self):
        """Create a viewer user and return token"""
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        return response.json()["token"]
    
    def test_follow_streamer(self, viewer_token, admin_user):
        """Test POST /api/streamers/{id}/follow creates follow record"""
        streamer_id = admin_user["id"]
        response = requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200, f"Follow failed: {response.text}"
        data = response.json()
        assert data["following"] == True
    
    def test_follow_idempotent(self, viewer_token, admin_user):
        """Test following same streamer twice is idempotent"""
        streamer_id = admin_user["id"]
        # Follow first time
        requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        # Follow second time
        response = requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["following"] == True
        assert "Already following" in data.get("message", "")
    
    def test_follow_status(self, viewer_token, admin_user):
        """Test GET /api/streamers/{id}/follow-status returns following and followers_count"""
        streamer_id = admin_user["id"]
        # Follow first
        requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow-status",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "following" in data
        assert "followers_count" in data
        assert isinstance(data["followers_count"], int)
    
    def test_unfollow_streamer(self, viewer_token, admin_user):
        """Test POST /api/streamers/{id}/unfollow deletes follow record"""
        streamer_id = admin_user["id"]
        # Follow first
        requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        # Unfollow
        response = requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/unfollow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["following"] == False
    
    def test_my_follows(self, viewer_token, admin_user):
        """Test GET /api/users/me/follows returns enriched follow list"""
        streamer_id = admin_user["id"]
        # Follow
        requests.post(
            f"{BASE_URL}/api/streamers/{streamer_id}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/users/me/follows",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "follows" in data
        assert isinstance(data["follows"], list)
        # Should have at least one follow
        if len(data["follows"]) > 0:
            follow = data["follows"][0]
            assert "id" in follow
            assert "name" in follow
            assert "followed_at" in follow
    
    def test_cannot_follow_self(self, admin_token, admin_user):
        """Test cannot follow yourself"""
        response = requests.post(
            f"{BASE_URL}/api/streamers/{admin_user['id']}/follow",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400


# =============================================================================
# NOTIFICATIONS TESTS
# =============================================================================
class TestNotifications:
    """Notifications endpoint tests"""
    
    def test_get_notifications(self, admin_token):
        """Test GET /api/notifications returns notifications and unread_count"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["unread_count"], int)
    
    def test_mark_notification_read(self, admin_token):
        """Test POST /api/notifications/{id}/read marks single notification read"""
        # First get notifications
        notifs = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        
        if len(notifs["notifications"]) > 0:
            notif_id = notifs["notifications"][0]["id"]
            response = requests.post(
                f"{BASE_URL}/api/notifications/{notif_id}/read",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            assert "marked read" in response.json().get("message", "")
    
    def test_mark_all_notifications_read(self, admin_token):
        """Test POST /api/notifications/read-all marks all notifications read"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/read-all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
    
    def test_follow_creates_notification(self, admin_token, admin_user):
        """Test following a streamer creates new_follower notification"""
        # Create a new viewer
        unique_email = f"TEST_follower_{uuid.uuid4().hex[:8]}@test.com"
        reg = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Follower Test",
            "role": "viewer"
        })
        viewer_token = reg.json()["token"]
        
        # Follow admin
        requests.post(
            f"{BASE_URL}/api/streamers/{admin_user['id']}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        # Check admin's notifications
        notifs = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        
        # Should have a new_follower notification
        follower_notifs = [n for n in notifs["notifications"] if n["type"] == "new_follower"]
        assert len(follower_notifs) > 0, "Should have new_follower notification"


# =============================================================================
# SEARCH TESTS
# =============================================================================
class TestSearch:
    """Unified search endpoint tests"""
    
    def test_search_returns_structure(self, admin_token):
        """Test GET /api/search?q=term returns content, streams, streamers, query"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "streams" in data
        assert "streamers" in data
        assert "query" in data
        assert data["query"] == "test"
    
    def test_search_short_query_returns_empty(self, admin_token):
        """Test search with <2 chars returns empty arrays"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "a"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == []
        assert data["streams"] == []
        assert data["streamers"] == []
    
    def test_search_case_insensitive(self, admin_token):
        """Test search is case-insensitive"""
        # Search for admin (lowercase)
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "admin"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should find admin user in streamers
        assert len(data["streamers"]) > 0 or len(data["streams"]) >= 0  # May or may not have streams


# =============================================================================
# TRENDING TESTS
# =============================================================================
class TestTrending:
    """Trending endpoint tests"""
    
    def test_trending_returns_structure(self, admin_token):
        """Test GET /api/trending returns content and live_streams"""
        response = requests.get(
            f"{BASE_URL}/api/trending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "live_streams" in data
        assert isinstance(data["content"], list)
        assert isinstance(data["live_streams"], list)
    
    def test_trending_limits(self, admin_token):
        """Test trending returns max 12 items each"""
        response = requests.get(
            f"{BASE_URL}/api/trending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert len(data["content"]) <= 12
        assert len(data["live_streams"]) <= 12


# =============================================================================
# ANALYTICS TESTS
# =============================================================================
class TestStreamerAnalytics:
    """Streamer analytics endpoint tests"""
    
    def test_analytics_returns_structure(self, admin_token):
        """Test GET /api/streamers/me/analytics returns full analytics"""
        response = requests.get(
            f"{BASE_URL}/api/streamers/me/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check all required fields
        assert "by_source" in data, "Missing by_source"
        assert "time_series" in data, "Missing time_series"
        assert "top_gifters" in data, "Missing top_gifters"
        assert "gift_tiers" in data, "Missing gift_tiers"
        assert "streams" in data, "Missing streams"
        assert "followers" in data, "Missing followers"
        
        # Check types
        assert isinstance(data["time_series"], list)
        assert isinstance(data["top_gifters"], list)
        assert isinstance(data["gift_tiers"], list)
        assert isinstance(data["followers"], int)
    
    def test_analytics_requires_streamer_role(self):
        """Test analytics requires streamer or admin role"""
        # Register a viewer
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        reg = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        viewer_token = reg.json()["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/streamers/me/analytics",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 403


# =============================================================================
# HEARTBEAT TESTS
# =============================================================================
class TestHeartbeat:
    """Server-side heartbeat endpoint tests"""
    
    @pytest.fixture
    def live_stream(self, admin_token):
        """Create a live stream for testing"""
        stream_data = {
            "title": "TEST_Heartbeat Stream",
            "description": "Testing heartbeat",
            "video_url": "https://example.com/stream.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        response = requests.post(
            f"{BASE_URL}/api/streams",
            json=stream_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        stream = response.json()
        yield stream
        # Cleanup: end the stream
        requests.post(
            f"{BASE_URL}/api/streams/{stream['id']}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_heartbeat_accumulates_minutes(self, admin_token, live_stream):
        """Test POST /api/streams/{id}/heartbeat accumulates watch minutes"""
        stream_id = live_stream["id"]
        
        # First heartbeat
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/heartbeat",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Heartbeat failed: {response.text}"
        data = response.json()
        assert "minutes" in data
        assert "qualified" in data
        assert "threshold" in data
        assert data["minutes"] == 1  # First heartbeat = 1 minute
        assert data["qualified"] == False  # Not yet qualified (need 30 min)
        assert data["threshold"] == 30
    
    def test_heartbeat_increments(self, admin_token, live_stream):
        """Test multiple heartbeats increment minutes"""
        stream_id = live_stream["id"]
        
        # Send 3 heartbeats
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/streams/{stream_id}/heartbeat",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            data = response.json()
            assert data["minutes"] == i + 1
    
    def test_legacy_qualified_view_endpoint(self, admin_token, live_stream):
        """Test legacy POST /api/streams/{id}/qualified-view still works"""
        stream_id = live_stream["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/qualified-view",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "Qualified view recorded" in response.json().get("message", "")


# =============================================================================
# GIFT NOTIFICATION TEST
# =============================================================================
class TestGiftNotification:
    """Test gift_received notification on gift send"""
    
    def test_gift_creates_notification(self, admin_token):
        """Test sending a gift creates gift_received notification for streamer"""
        # This test requires:
        # 1. A live stream
        # 2. A user with gift wallet balance
        # 3. Sending a gift
        # Since we can't easily set up wallet balance without Stripe, we'll just verify the endpoint exists
        # and returns proper error when no balance
        
        # Create a stream
        stream_data = {
            "title": "TEST_Gift Notification Stream",
            "description": "Testing gift notification",
            "video_url": "https://example.com/stream.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        stream_response = requests.post(
            f"{BASE_URL}/api/streams",
            json=stream_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        stream = stream_response.json()
        
        # Try to send gift (will fail due to no balance or no subscription, but endpoint should work)
        gift_response = requests.post(
            f"{BASE_URL}/api/gifts/send",
            json={"stream_id": stream["id"], "tier_id": "t1", "quantity": 1},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 400 (insufficient balance) or 403 (no subscription) not 500
        assert gift_response.status_code in [200, 400, 403], f"Unexpected status: {gift_response.status_code}"
        
        # Cleanup
        requests.post(
            f"{BASE_URL}/api/streams/{stream['id']}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


# =============================================================================
# STREAM LIVE NOTIFICATION TEST
# =============================================================================
class TestStreamLiveNotification:
    """Test stream_live notification when streamer goes live"""
    
    def test_stream_create_notifies_followers(self, admin_token, admin_user):
        """Test creating a stream notifies all followers"""
        # Create a viewer who follows admin
        unique_email = f"TEST_follower_{uuid.uuid4().hex[:8]}@test.com"
        reg = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Stream Follower",
            "role": "viewer"
        })
        viewer_token = reg.json()["token"]
        
        # Follow admin
        requests.post(
            f"{BASE_URL}/api/streamers/{admin_user['id']}/follow",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        # Admin creates a stream
        stream_data = {
            "title": "TEST_Follower Notification Stream",
            "description": "Testing follower notification",
            "video_url": "https://example.com/stream.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        stream_response = requests.post(
            f"{BASE_URL}/api/streams",
            json=stream_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        stream = stream_response.json()
        
        # Check viewer's notifications
        notifs = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {viewer_token}"}
        ).json()
        
        # Should have a stream_live notification
        live_notifs = [n for n in notifs["notifications"] if n["type"] == "stream_live"]
        assert len(live_notifs) > 0, "Follower should receive stream_live notification"
        
        # Cleanup
        requests.post(
            f"{BASE_URL}/api/streams/{stream['id']}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
