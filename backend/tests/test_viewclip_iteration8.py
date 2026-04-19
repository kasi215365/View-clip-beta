"""
View/Clip Iteration 8 Tests — Phase 2a Refactor + Phase 3 OAuth Integration
Tests:
- REGRESSION: All previously-passing endpoints from iteration 6 & 7
- PUBLIC PROBES: /api/health, /api/ready (now in routers/health.py)
- MOVED NOTIFICATIONS: /api/notifications endpoints (routers/notifications.py)
- MOVED SOCIAL: referrals, follows, search, trending (routers/social.py)
- OAUTH START: /api/oauth/youtube/start, /api/oauth/twitch/start (mock=true when env vars missing)
- OAUTH CONNECTIONS: /api/oauth/connections
- OAUTH DISCONNECT: /api/oauth/{provider}/disconnect
- OAUTH CALLBACK: /api/oauth/{provider}/callback error handling
- STREAM EXPORT: /api/streams/{id}/export with youtube/twitch/x/custom platforms
"""

import pytest
import requests
import os
import pyotp
import time
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@viewclip.com"
ADMIN_PASSWORD = "Admin123!"


# =============================================================================
# FIXTURES
# =============================================================================
@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token via admin portal login (assumes 2FA disabled)"""
    response = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    if data.get("require_2fa"):
        pytest.skip("2FA is enabled on admin account - disable it first")
    return data.get("token")


@pytest.fixture(scope="module")
def streamer_token():
    """Create a test streamer and return token"""
    unique_email = f"TEST_streamer_iter8_{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": unique_email,
        "password": "Test123!",
        "name": "Iter8 Streamer",
        "role": "streamer"
    })
    assert reg_resp.status_code == 200, f"Streamer registration failed: {reg_resp.text}"
    return reg_resp.json()["token"]


@pytest.fixture(scope="module")
def viewer_token():
    """Create a test viewer and return token"""
    unique_email = f"TEST_viewer_iter8_{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": unique_email,
        "password": "Test123!",
        "name": "Iter8 Viewer",
        "role": "viewer"
    })
    assert reg_resp.status_code == 200, f"Viewer registration failed: {reg_resp.text}"
    return reg_resp.json()["token"]


# =============================================================================
# PUBLIC HEALTH PROBES (routers/health.py)
# =============================================================================
class TestPublicHealthProbes:
    """Test public health/ready probes - no auth required"""
    
    def test_health_endpoint_public(self):
        """GET /api/health returns {status:'ok', version:'1.4.0'} without auth"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok", f"Expected status:ok, got {data}"
        assert data["version"] == "1.4.0", f"Expected version 1.4.0, got {data.get('version')}"
        print(f"✓ /api/health returns {data}")
    
    def test_ready_endpoint_public(self):
        """GET /api/ready returns {status:'ready'} when DB up"""
        response = requests.get(f"{BASE_URL}/api/ready")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ready", f"Expected status:ready, got {data}"
        print(f"✓ /api/ready returns {data}")
    
    def test_x_request_id_header(self):
        """Every response carries X-Request-ID header"""
        response = requests.get(f"{BASE_URL}/api/health")
        req_id = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
        assert req_id is not None and len(req_id) > 0, "Missing X-Request-ID header"
        print(f"✓ X-Request-ID: {req_id}")
    
    def test_x_request_id_echoed(self):
        """When client supplies X-Request-ID, it is echoed back"""
        custom_id = "test-iter8-request-id-12345"
        response = requests.get(f"{BASE_URL}/api/health", headers={"X-Request-ID": custom_id})
        returned_id = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
        assert returned_id == custom_id, f"Expected {custom_id}, got {returned_id}"
        print(f"✓ X-Request-ID echoed: {returned_id}")


# =============================================================================
# NOTIFICATIONS (routers/notifications.py)
# =============================================================================
class TestNotifications:
    """Test notifications endpoints - require auth"""
    
    def test_notifications_requires_auth(self):
        """GET /api/notifications requires auth (401 without token)"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ /api/notifications requires auth")
    
    def test_notifications_list(self, admin_token):
        """GET /api/notifications returns notifications list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "notifications" in data, "Missing notifications key"
        assert "unread_count" in data, "Missing unread_count key"
        print(f"✓ /api/notifications returns {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_mark_notification_read(self, admin_token):
        """POST /api/notifications/{id}/read marks notification as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First get notifications
        list_resp = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        notifications = list_resp.json().get("notifications", [])
        
        if not notifications:
            pytest.skip("No notifications to mark as read")
        
        notif_id = notifications[0]["id"]
        response = requests.post(f"{BASE_URL}/api/notifications/{notif_id}/read", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Marked notification {notif_id} as read")
    
    def test_mark_all_read(self, admin_token):
        """POST /api/notifications/read-all marks all notifications as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/notifications/read-all", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data
        print(f"✓ /api/notifications/read-all: {data}")


# =============================================================================
# SOCIAL ENDPOINTS (routers/social.py)
# =============================================================================
class TestSocialEndpoints:
    """Test social/discovery endpoints - referrals, follows, search, trending"""
    
    def test_referrals_my(self, admin_token):
        """GET /api/referrals/my returns user's referral info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/referrals/my", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "code" in data, "Missing referral code"
        assert "referred_count" in data, "Missing referred_count"
        assert "earnings" in data, "Missing earnings"
        print(f"✓ /api/referrals/my: code={data['code']}, referred={data['referred_count']}")
    
    def test_referrals_leaderboard(self):
        """GET /api/referrals/leaderboard returns top referrers (public)"""
        response = requests.get(f"{BASE_URL}/api/referrals/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "leaderboard" in data, "Missing leaderboard key"
        print(f"✓ /api/referrals/leaderboard: {len(data['leaderboard'])} entries")
    
    def test_referrals_validate_code(self, admin_token):
        """GET /api/referrals/validate/{code} validates referral code"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First get user's referral code
        my_resp = requests.get(f"{BASE_URL}/api/referrals/my", headers=headers)
        code = my_resp.json().get("code")
        
        if not code:
            pytest.skip("No referral code available")
        
        response = requests.get(f"{BASE_URL}/api/referrals/validate/{code}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True, f"Expected valid=true, got {data}"
        print(f"✓ /api/referrals/validate/{code}: valid={data['valid']}")
    
    def test_referrals_validate_invalid_code(self):
        """GET /api/referrals/validate/{code} returns valid=false for invalid code"""
        response = requests.get(f"{BASE_URL}/api/referrals/validate/INVALID_CODE_XYZ")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False, f"Expected valid=false, got {data}"
        print("✓ Invalid referral code returns valid=false")
    
    def test_search_endpoint(self):
        """GET /api/search?q=... returns search results (public)"""
        response = requests.get(f"{BASE_URL}/api/search", params={"q": "test"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "content" in data, "Missing content key"
        assert "streams" in data, "Missing streams key"
        assert "streamers" in data, "Missing streamers key"
        assert "query" in data, "Missing query key"
        print(f"✓ /api/search?q=test: {len(data['content'])} content, {len(data['streams'])} streams, {len(data['streamers'])} streamers")
    
    def test_trending_endpoint(self):
        """GET /api/trending returns trending content and streams (public)"""
        response = requests.get(f"{BASE_URL}/api/trending")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "content" in data, "Missing content key"
        assert "live_streams" in data, "Missing live_streams key"
        print(f"✓ /api/trending: {len(data['content'])} content, {len(data['live_streams'])} live streams")
    
    def test_follow_status(self, admin_token, streamer_token):
        """GET /api/streamers/{id}/follow-status returns follow status"""
        # Get streamer user id
        streamer_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {streamer_token}"})
        streamer_id = streamer_resp.json()["id"]
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/streamers/{streamer_id}/follow-status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "following" in data, "Missing following key"
        assert "followers_count" in data, "Missing followers_count key"
        print(f"✓ /api/streamers/{streamer_id}/follow-status: following={data['following']}")
    
    def test_follow_unfollow_flow(self, viewer_token, streamer_token):
        """POST /api/streamers/{id}/follow and /unfollow work correctly"""
        # Get streamer user id
        streamer_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {streamer_token}"})
        streamer_id = streamer_resp.json()["id"]
        
        headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # Follow
        follow_resp = requests.post(f"{BASE_URL}/api/streamers/{streamer_id}/follow", headers=headers)
        assert follow_resp.status_code == 200, f"Follow failed: {follow_resp.text}"
        assert follow_resp.json()["following"] == True
        print(f"✓ Followed streamer {streamer_id}")
        
        # Unfollow
        unfollow_resp = requests.post(f"{BASE_URL}/api/streamers/{streamer_id}/unfollow", headers=headers)
        assert unfollow_resp.status_code == 200, f"Unfollow failed: {unfollow_resp.text}"
        assert unfollow_resp.json()["following"] == False
        print(f"✓ Unfollowed streamer {streamer_id}")
    
    def test_my_follows(self, admin_token):
        """GET /api/users/me/follows returns user's follows"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/me/follows", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "follows" in data, "Missing follows key"
        print(f"✓ /api/users/me/follows: {len(data['follows'])} follows")


# =============================================================================
# OAUTH ENDPOINTS (routers/oauth.py)
# =============================================================================
class TestOAuthEndpoints:
    """Test OAuth endpoints - YouTube + Twitch with mock fallback"""
    
    def test_oauth_youtube_start_mock(self, admin_token):
        """POST /api/oauth/youtube/start returns mock=true when env vars not set"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/oauth/youtube/start", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("mock") == True, f"Expected mock=true, got {data}"
        assert "message" in data, "Missing message"
        assert "YOUTUBE_CLIENT_ID" in data["message"], f"Message should mention YOUTUBE_CLIENT_ID: {data['message']}"
        print(f"✓ /api/oauth/youtube/start: mock={data['mock']}, message={data['message'][:50]}...")
    
    def test_oauth_twitch_start_mock(self, admin_token):
        """POST /api/oauth/twitch/start returns mock=true when env vars not set"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/oauth/twitch/start", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("mock") == True, f"Expected mock=true, got {data}"
        assert "message" in data, "Missing message"
        assert "TWITCH_CLIENT_ID" in data["message"], f"Message should mention TWITCH_CLIENT_ID: {data['message']}"
        print(f"✓ /api/oauth/twitch/start: mock={data['mock']}, message={data['message'][:50]}...")
    
    def test_oauth_start_unknown_provider(self, admin_token):
        """POST /api/oauth/xyz/start returns 400 for unknown provider"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/oauth/xyz/start", headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Unknown provider returns 400")
    
    def test_oauth_connections(self, admin_token):
        """GET /api/oauth/connections returns connections and available_providers"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/oauth/connections", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "connections" in data, "Missing connections key"
        assert "available_providers" in data, "Missing available_providers key"
        
        # Verify available_providers structure
        providers = {p["id"]: p for p in data["available_providers"]}
        assert "youtube" in providers, "Missing youtube provider"
        assert "twitch" in providers, "Missing twitch provider"
        assert providers["youtube"]["configured"] == False, "YouTube should not be configured"
        assert providers["twitch"]["configured"] == False, "Twitch should not be configured"
        
        print(f"✓ /api/oauth/connections: {len(data['connections'])} connections, providers: {list(providers.keys())}")
    
    def test_oauth_disconnect_not_connected(self, admin_token):
        """POST /api/oauth/youtube/disconnect returns disconnected=false when not connected"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/oauth/youtube/disconnect", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["disconnected"] == False, f"Expected disconnected=false, got {data}"
        assert data["provider"] == "youtube", f"Expected provider=youtube, got {data}"
        print(f"✓ /api/oauth/youtube/disconnect (not connected): {data}")
    
    def test_oauth_disconnect_unknown_provider(self, admin_token):
        """POST /api/oauth/xyz/disconnect returns 400 for unknown provider"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/oauth/xyz/disconnect", headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Unknown provider disconnect returns 400")
    
    def test_oauth_callback_error(self):
        """GET /api/oauth/youtube/callback?error=access_denied redirects with error"""
        response = requests.get(
            f"{BASE_URL}/api/oauth/youtube/callback",
            params={"error": "access_denied"},
            allow_redirects=False
        )
        assert response.status_code in [302, 307], f"Expected redirect, got {response.status_code}"
        location = response.headers.get("location", "")
        assert "oauth=youtube" in location, f"Missing oauth=youtube in redirect: {location}"
        assert "status=error" in location, f"Missing status=error in redirect: {location}"
        assert "msg=access_denied" in location, f"Missing msg=access_denied in redirect: {location}"
        print(f"✓ OAuth callback with error redirects correctly: {location}")
    
    def test_oauth_callback_missing_params(self):
        """GET /api/oauth/youtube/callback with no code/state redirects with missing_params"""
        response = requests.get(
            f"{BASE_URL}/api/oauth/youtube/callback",
            allow_redirects=False
        )
        assert response.status_code in [302, 307], f"Expected redirect, got {response.status_code}"
        location = response.headers.get("location", "")
        assert "msg=missing_params" in location, f"Missing msg=missing_params in redirect: {location}"
        print(f"✓ OAuth callback with missing params redirects correctly: {location}")
    
    def test_oauth_callback_invalid_state(self):
        """GET /api/oauth/youtube/callback with bogus state+code redirects with invalid_state"""
        response = requests.get(
            f"{BASE_URL}/api/oauth/youtube/callback",
            params={"code": "bogus_code", "state": "bogus_state"},
            allow_redirects=False
        )
        assert response.status_code in [302, 307], f"Expected redirect, got {response.status_code}"
        location = response.headers.get("location", "")
        assert "msg=invalid_state" in location, f"Missing msg=invalid_state in redirect: {location}"
        print(f"✓ OAuth callback with invalid state redirects correctly: {location}")


# =============================================================================
# STREAM EXPORT (server.py /streams/{id}/export)
# =============================================================================
class TestStreamExport:
    """Test stream export with YouTube/Twitch/X/Custom platforms"""
    
    @pytest.fixture
    def saved_stream(self, admin_token):
        """Create and save a stream for export testing (using admin who has subscription)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create stream
        create_resp = requests.post(f"{BASE_URL}/api/streams", headers=headers, json={
            "title": f"TEST Export Stream {uuid.uuid4().hex[:8]}",
            "description": "Test stream for export",
            "video_url": "https://example.com/video.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        })
        assert create_resp.status_code == 200, f"Create stream failed: {create_resp.text}"
        stream = create_resp.json()
        stream_id = stream["id"]
        
        # End stream (if live)
        if stream.get("is_live"):
            requests.post(f"{BASE_URL}/api/streams/{stream_id}/end", headers=headers)
        
        # Save stream
        save_resp = requests.post(f"{BASE_URL}/api/streams/{stream_id}/save", headers=headers)
        assert save_resp.status_code == 200, f"Save stream failed: {save_resp.text}"
        
        return stream_id, headers
    
    def test_export_youtube_mock(self, saved_stream):
        """POST /api/streams/{id}/export platform=youtube returns mock=true, note=not_connected"""
        stream_id, headers = saved_stream
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/export",
            headers=headers,
            json={"platform": "youtube"}
        )
        assert response.status_code == 200, f"Export failed: {response.text}"
        data = response.json()
        assert "export" in data, "Missing export key"
        export = data["export"]
        assert export["mock"] == True, f"Expected mock=true, got {export}"
        assert export["note"] == "not_connected", f"Expected note=not_connected, got {export.get('note')}"
        print(f"✓ Export to YouTube: mock={export['mock']}, note={export['note']}")
    
    def test_export_twitch_mock(self, saved_stream):
        """POST /api/streams/{id}/export platform=twitch returns mock=true, note=not_connected"""
        stream_id, headers = saved_stream
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/export",
            headers=headers,
            json={"platform": "twitch"}
        )
        assert response.status_code == 200, f"Export failed: {response.text}"
        data = response.json()
        export = data["export"]
        assert export["mock"] == True, f"Expected mock=true, got {export}"
        assert export["note"] == "not_connected", f"Expected note=not_connected, got {export.get('note')}"
        print(f"✓ Export to Twitch: mock={export['mock']}, note={export['note']}")
    
    def test_export_x_platform(self, saved_stream):
        """POST /api/streams/{id}/export platform=x returns mock=true, note=null"""
        stream_id, headers = saved_stream
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/export",
            headers=headers,
            json={"platform": "x"}
        )
        assert response.status_code == 200, f"Export failed: {response.text}"
        data = response.json()
        export = data["export"]
        assert export["mock"] == True, f"Expected mock=true, got {export}"
        assert export.get("note") is None, f"Expected note=null for x platform, got {export.get('note')}"
        print(f"✓ Export to X: mock={export['mock']}, note={export.get('note')}")
    
    def test_export_custom_platform(self, saved_stream):
        """POST /api/streams/{id}/export platform=custom returns mock=true, note=null"""
        stream_id, headers = saved_stream
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/export",
            headers=headers,
            json={"platform": "custom", "target_url": "https://custom.example.com/video"}
        )
        assert response.status_code == 200, f"Export failed: {response.text}"
        data = response.json()
        export = data["export"]
        assert export["mock"] == True, f"Expected mock=true, got {export}"
        assert export.get("note") is None, f"Expected note=null for custom platform, got {export.get('note')}"
        print(f"✓ Export to Custom: mock={export['mock']}, note={export.get('note')}")
    
    def test_export_unsaved_stream_fails(self, admin_token):
        """POST /api/streams/{id}/export fails for unsaved stream"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create stream but don't save
        create_resp = requests.post(f"{BASE_URL}/api/streams", headers=headers, json={
            "title": f"TEST Unsaved Stream {uuid.uuid4().hex[:8]}",
            "description": "Test unsaved stream",
            "video_url": "https://example.com/video.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        })
        assert create_resp.status_code == 200, f"Create stream failed: {create_resp.text}"
        stream_id = create_resp.json()["id"]
        
        # End stream first
        requests.post(f"{BASE_URL}/api/streams/{stream_id}/end", headers=headers)
        
        # Try to export without saving
        response = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/export",
            headers=headers,
            json={"platform": "youtube"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Export unsaved stream returns 400")


# =============================================================================
# REGRESSION TESTS - Admin 2FA, Recovery Codes, Key Rotation
# =============================================================================
class TestAdmin2FARegression:
    """Regression tests for admin 2FA features from iteration 6 & 7"""
    
    def test_2fa_status(self, admin_token):
        """GET /api/admin/auth/2fa/status returns enabled/pending_setup"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/auth/2fa/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "enabled" in data, "Missing enabled key"
        assert "pending_setup" in data, "Missing pending_setup key"
        print(f"✓ 2FA status: enabled={data['enabled']}, pending_setup={data['pending_setup']}")
    
    def test_2fa_setup_enable_disable_flow(self, admin_token):
        """Full 2FA setup → enable → disable flow with recovery codes"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Setup
        setup_resp = requests.post(f"{BASE_URL}/api/admin/auth/2fa/setup", headers=headers)
        assert setup_resp.status_code == 200, f"Setup failed: {setup_resp.text}"
        setup_data = setup_resp.json()
        assert "secret" in setup_data, "Missing secret"
        assert "qr_code_png_base64" in setup_data, "Missing QR code"
        secret = setup_data["secret"]
        print(f"✓ 2FA setup: got secret and QR code")
        
        # Enable with valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()
        enable_resp = requests.post(f"{BASE_URL}/api/admin/auth/2fa/enable", headers=headers, json={"code": code})
        assert enable_resp.status_code == 200, f"Enable failed: {enable_resp.text}"
        enable_data = enable_resp.json()
        assert "recovery_codes" in enable_data, "Missing recovery_codes"
        assert len(enable_data["recovery_codes"]) == 10, f"Expected 10 recovery codes, got {len(enable_data['recovery_codes'])}"
        print(f"✓ 2FA enabled with {len(enable_data['recovery_codes'])} recovery codes")
        
        # Verify status shows enabled
        status_resp = requests.get(f"{BASE_URL}/api/admin/auth/2fa/status", headers=headers)
        assert status_resp.json()["enabled"] == True, "2FA should be enabled"
        
        # Disable with valid TOTP code
        time.sleep(1)  # Ensure fresh code
        disable_code = totp.now()
        disable_resp = requests.post(f"{BASE_URL}/api/admin/auth/2fa/disable", headers=headers, json={"code": disable_code})
        assert disable_resp.status_code == 200, f"Disable failed: {disable_resp.text}"
        print("✓ 2FA disabled")
        
        # Verify status shows disabled
        final_status = requests.get(f"{BASE_URL}/api/admin/auth/2fa/status", headers=headers)
        assert final_status.json()["enabled"] == False, "2FA should be disabled"
        print("✓ 2FA status confirmed disabled")


# =============================================================================
# REGRESSION TESTS - Payments, Gifts, Content, Streams, Subscriptions
# =============================================================================
class TestPaymentsRegression:
    """Regression tests for payment features"""
    
    def test_gift_tiers(self):
        """GET /api/gifts/tiers returns 8 tiers"""
        response = requests.get(f"{BASE_URL}/api/gifts/tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tiers" in data, "Missing tiers key"
        assert len(data["tiers"]) == 8, f"Expected 8 tiers, got {len(data['tiers'])}"
        print(f"✓ /api/gifts/tiers: {len(data['tiers'])} tiers")
    
    def test_subscription_checkout(self, admin_token):
        """POST /api/payments/checkout/subscribe works"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/payments/checkout/subscribe", headers=headers, json={
            "type": "viewer",
            "origin_url": "https://viewer-pro.preview.emergentagent.com"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "url" in data, "Missing checkout url"
        assert "session_id" in data, "Missing session_id"
        print(f"✓ Subscription checkout: session_id={data['session_id'][:20]}...")
    
    def test_connect_onboard_mock(self, streamer_token):
        """POST /api/streamers/connect/onboard returns mock=true"""
        headers = {"Authorization": f"Bearer {streamer_token}"}
        response = requests.post(f"{BASE_URL}/api/streamers/connect/onboard", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("mock") == True, f"Expected mock=true, got {data}"
        print(f"✓ Connect onboard: mock={data['mock']}")


class TestContentStreamsRegression:
    """Regression tests for content and streams"""
    
    def test_content_list(self):
        """GET /api/content returns content list"""
        response = requests.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ /api/content: {len(response.json())} items")
    
    def test_streams_list(self):
        """GET /api/streams returns streams list"""
        response = requests.get(f"{BASE_URL}/api/streams")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ /api/streams: {len(response.json())} streams")
    
    def test_promos_list(self):
        """GET /api/promos returns promos"""
        response = requests.get(f"{BASE_URL}/api/promos")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ /api/promos: {len(response.json())} promos")


class TestAdminSystemHealthRegression:
    """Regression tests for admin system health"""
    
    def test_admin_system_health(self, admin_token):
        """GET /api/admin/system/health returns version 1.4.0 and all fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/health", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Version check
        assert data["version"] == "1.4.0", f"Expected version 1.4.0, got {data.get('version')}"
        
        # Check required fields
        assert "layers" in data, "Missing layers"
        assert len(data["layers"]) == 3, f"Expected 3 DB layers, got {len(data['layers'])}"
        assert "firewall" in data, "Missing firewall"
        assert "encryption" in data, "Missing encryption"
        assert "integrations" in data, "Missing integrations"
        
        print(f"✓ Admin system health: version={data['version']}, {len(data['layers'])} layers")
    
    def test_admin_audit_log(self, admin_token):
        """GET /api/admin/audit returns audit log"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/audit", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "audit" in data, "Missing audit key"
        print(f"✓ /api/admin/audit: {len(data['audit'])} entries")
    
    def test_key_rotation(self, admin_token):
        """POST /api/admin/system/rotate-keys includes totp_rotated/totp_failed"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/system/rotate-keys", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "totp_rotated" in data, "Missing totp_rotated"
        assert "totp_failed" in data, "Missing totp_failed"
        print(f"✓ Key rotation: totp_rotated={data['totp_rotated']}, totp_failed={data['totp_failed']}")


# =============================================================================
# CLEANUP - Ensure 2FA is disabled at end
# =============================================================================
class TestCleanup:
    """Cleanup: Ensure 2FA is disabled on admin account"""
    
    def test_cleanup_disable_2fa(self, admin_token):
        """Cleanup: Ensure 2FA is disabled at end of tests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        status_resp = requests.get(f"{BASE_URL}/api/admin/auth/2fa/status", headers=headers)
        
        if status_resp.json().get("enabled"):
            # Setup to get secret, enable, then disable
            setup_resp = requests.post(f"{BASE_URL}/api/admin/auth/2fa/setup", headers=headers)
            secret = setup_resp.json()["secret"]
            totp = pyotp.TOTP(secret)
            time.sleep(1)
            requests.post(f"{BASE_URL}/api/admin/auth/2fa/enable", headers=headers, json={"code": totp.now()})
            time.sleep(1)
            requests.post(f"{BASE_URL}/api/admin/auth/2fa/disable", headers=headers, json={"code": totp.now()})
        
        # Verify disabled
        final_status = requests.get(f"{BASE_URL}/api/admin/auth/2fa/status", headers=headers)
        assert final_status.json()["enabled"] == False, "2FA should be disabled for cleanup"
        print("✓ Cleanup: 2FA disabled on admin account")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
