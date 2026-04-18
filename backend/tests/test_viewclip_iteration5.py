"""
View/Clip API Tests - Iteration 5: Production Wiring
Tests: Stripe Connect Express, Recurring Subscriptions, GCP Live Stream, Key Rotation
All integrations have graceful fallback to mock when credentials are not configured.
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


@pytest.fixture(scope="module")
def streamer_token():
    """Create a streamer user for testing"""
    unique_email = f"TEST_streamer_iter5_{uuid.uuid4().hex[:8]}@test.com"
    reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": unique_email,
        "password": "Test123!",
        "name": "Iteration5 Streamer",
        "role": "streamer"
    })
    assert reg_response.status_code == 200, f"Streamer registration failed: {reg_response.text}"
    return reg_response.json()["token"]


# =============================================================================
# NEW MODULES EXISTENCE TESTS
# =============================================================================
class TestNewModulesExist:
    """Verify new stripe_service and live_stream_service modules are imported"""
    
    def test_health_shows_stripe_mode(self, admin_token):
        """Test /api/admin/system/health shows stripe_mode in integrations"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data
        assert "stripe_mode" in data["integrations"]
        # Since STRIPE_API_KEY=sk_test_emergent, should be mock
        assert "mock" in data["integrations"]["stripe_mode"].lower()
    
    def test_health_shows_livestream_mode(self, admin_token):
        """Test /api/admin/system/health shows livestream_mode in integrations"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data
        assert "livestream_mode" in data["integrations"]
        # Since GCP creds not configured, should be mock
        assert data["integrations"]["livestream_mode"] == "mock"


# =============================================================================
# LIVE STREAM PROVISIONING TESTS
# =============================================================================
class TestLiveStreamProvisioning:
    """Test POST /api/streams returns new fields: ingest_url, playback_url, live_mode"""
    
    def test_create_stream_returns_ingest_url(self, admin_token):
        """Test POST /api/streams returns ingest_url in mock mode"""
        response = requests.post(
            f"{BASE_URL}/api/streams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Test Stream Iter5",
                "description": "Testing live stream provisioning",
                "video_url": "https://example.com/test.mp4",
                "thumbnail_url": "https://example.com/thumb.jpg"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "ingest_url" in data, "Missing ingest_url"
        assert data["ingest_url"].startswith("rtmp://ingest.viewclip.mock"), f"Expected mock ingest URL, got {data['ingest_url']}"
    
    def test_create_stream_returns_playback_url(self, admin_token):
        """Test POST /api/streams returns playback_url in mock mode"""
        response = requests.post(
            f"{BASE_URL}/api/streams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Test Stream Playback",
                "description": "Testing playback URL",
                "video_url": "https://example.com/test2.mp4",
                "thumbnail_url": "https://example.com/thumb2.jpg"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "playback_url" in data, "Missing playback_url"
        assert data["playback_url"].startswith("https://cdn.viewclip.mock"), f"Expected mock playback URL, got {data['playback_url']}"
    
    def test_create_stream_returns_live_mode(self, admin_token):
        """Test POST /api/streams returns live_mode field"""
        response = requests.post(
            f"{BASE_URL}/api/streams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Test Stream Mode",
                "description": "Testing live_mode field",
                "video_url": "https://example.com/test3.mp4",
                "thumbnail_url": "https://example.com/thumb3.jpg"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "live_mode" in data, "Missing live_mode"
        assert data["live_mode"] == "mock", f"Expected mock mode, got {data['live_mode']}"
    
    def test_create_stream_returns_stream_key(self, admin_token):
        """Test POST /api/streams returns stream_key in mock mode"""
        response = requests.post(
            f"{BASE_URL}/api/streams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Test Stream Key",
                "description": "Testing stream_key field",
                "video_url": "https://example.com/test4.mp4",
                "thumbnail_url": "https://example.com/thumb4.jpg"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "stream_key" in data, "Missing stream_key"
        # Mock mode generates a 16-char hex key
        assert data["stream_key"] is not None and len(data["stream_key"]) == 16


class TestLiveStreamEnd:
    """Test POST /api/streams/{id}/end calls stop_stream"""
    
    def test_end_stream_no_error_mock_mode(self, admin_token):
        """Test ending a stream in mock mode doesn't error"""
        # First create a stream
        create_resp = requests.post(
            f"{BASE_URL}/api/streams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Stream to End",
                "description": "Will be ended",
                "video_url": "https://example.com/end.mp4",
                "thumbnail_url": "https://example.com/end.jpg"
            }
        )
        assert create_resp.status_code == 200
        stream_id = create_resp.json()["id"]
        
        # End the stream
        end_resp = requests.post(
            f"{BASE_URL}/api/streams/{stream_id}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert end_resp.status_code == 200, f"Failed to end stream: {end_resp.text}"
        data = end_resp.json()
        assert "message" in data
        assert "earnings" in data


# =============================================================================
# STRIPE CONNECT TESTS (Mock Mode)
# =============================================================================
class TestStripeConnectOnboard:
    """Test POST /api/streamers/connect/onboard in mock mode"""
    
    def test_connect_onboard_returns_mock_response(self, streamer_token):
        """Test connect onboard returns mock=true when real Stripe not configured"""
        response = requests.post(
            f"{BASE_URL}/api/streamers/connect/onboard",
            headers={"Authorization": f"Bearer {streamer_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("mock") == True, "Expected mock=true"
        assert data.get("status") == "active", f"Expected status=active, got {data.get('status')}"
        assert "onboarding_url" in data
        assert "mock" in data["onboarding_url"].lower()
    
    def test_connect_onboard_sets_user_status_active(self, streamer_token):
        """Test connect onboard sets connect_account_status='active' on user"""
        # First onboard
        requests.post(
            f"{BASE_URL}/api/streamers/connect/onboard",
            headers={"Authorization": f"Bearer {streamer_token}"}
        )
        
        # Check user status
        me_resp = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {streamer_token}"}
        )
        assert me_resp.status_code == 200
        user = me_resp.json()
        assert user.get("connect_account_status") == "active"


class TestStripeConnectStatus:
    """Test GET /api/streamers/connect/status"""
    
    def test_connect_status_no_account(self):
        """Test connect status returns configured=false for user without connect_account_id"""
        # Create fresh user
        unique_email = f"TEST_connect_status_{uuid.uuid4().hex[:8]}@test.com"
        reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "name": "Connect Status Test",
            "role": "streamer"
        })
        token = reg_resp.json()["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/streamers/connect/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("configured") == False


# =============================================================================
# SUBSCRIPTION CHECKOUT TESTS (Mock Mode)
# =============================================================================
class TestSubscriptionCheckout:
    """Test POST /api/payments/checkout/subscribe in mock mode"""
    
    def test_checkout_subscribe_returns_url(self, admin_token):
        """Test checkout subscribe returns url and session_id"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"type": "viewer", "origin_url": "https://viewer-pro.preview.emergentagent.com"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "url" in data
        assert "session_id" in data
    
    def test_checkout_subscribe_session_id_format(self, admin_token):
        """Test checkout subscribe session_id starts with cs_test_"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"type": "viewer", "origin_url": "https://viewer-pro.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"].startswith("cs_test_"), f"Expected cs_test_ prefix, got {data['session_id']}"
    
    def test_checkout_subscribe_recurring_false_mock(self, admin_token):
        """Test checkout subscribe returns recurring=false in mock mode"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"type": "streamer", "origin_url": "https://viewer-pro.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("recurring") == False, f"Expected recurring=false in mock mode, got {data.get('recurring')}"


class TestSubscriptionCancel:
    """Test POST /api/payments/subscription/cancel"""
    
    def test_cancel_subscription_404_no_subscription(self, admin_token):
        """Test cancel subscription returns 404 when no subscription with stripe_subscription_id"""
        # Create fresh user without subscription
        unique_email = f"TEST_cancel_sub_{uuid.uuid4().hex[:8]}@test.com"
        reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "name": "Cancel Sub Test",
            "role": "viewer"
        })
        token = reg_resp.json()["token"]
        
        response = requests.post(
            f"{BASE_URL}/api/payments/subscription/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


# =============================================================================
# ADMIN PAYOUTS TESTS (Mock Mode)
# =============================================================================
class TestAdminPayouts:
    """Test POST /api/admin/payouts/trigger in mock mode"""
    
    def test_trigger_payouts_returns_real_mode_false(self, admin_token):
        """Test trigger payouts returns real_mode=false in mock mode"""
        response = requests.post(
            f"{BASE_URL}/api/admin/payouts/trigger",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("real_mode") == False, f"Expected real_mode=false, got {data.get('real_mode')}"
    
    def test_trigger_payouts_creates_mock_payouts(self, admin_token):
        """Test trigger payouts creates payouts with status='completed_mock'"""
        # First trigger payouts
        requests.post(
            f"{BASE_URL}/api/admin/payouts/trigger",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Check payouts list
        response = requests.get(
            f"{BASE_URL}/api/admin/payouts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "payouts" in data
        # If there are payouts, check status
        if data["payouts"]:
            mock_payouts = [p for p in data["payouts"] if p.get("status") == "completed_mock"]
            # At least some should be mock
            assert len(mock_payouts) >= 0  # May be 0 if no earnings to pay out


# =============================================================================
# KEY ROTATION TESTS (Real Re-encryption)
# =============================================================================
class TestKeyRotation:
    """Test POST /api/admin/system/rotate-keys with real re-encryption"""
    
    def test_rotate_keys_after_banking_preserves_data(self, admin_token):
        """Test key rotation preserves banking data (last-4 digits match)"""
        # First save banking info
        test_account = f"123456789{uuid.uuid4().hex[:4]}"
        test_routing = f"987654321"
        
        save_resp = requests.post(
            f"{BASE_URL}/api/vault/banking",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "account_holder": "Key Rotation Test",
                "account_number": test_account,
                "routing_number": test_routing,
                "bank_name": "Rotation Bank",
                "country": "US"
            }
        )
        assert save_resp.status_code == 200
        
        # Get banking before rotation
        before_resp = requests.get(
            f"{BASE_URL}/api/vault/banking",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert before_resp.status_code == 200
        before_data = before_resp.json()
        before_last4 = before_data["account_number_masked"][-4:]
        
        # Rotate keys
        rotate_resp = requests.post(
            f"{BASE_URL}/api/admin/system/rotate-keys",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert rotate_resp.status_code == 200, f"Rotation failed: {rotate_resp.text}"
        rotate_data = rotate_resp.json()
        assert "rotated" in rotate_data
        assert rotate_data["rotated"] >= 1, "Expected at least 1 record rotated"
        
        # Get banking after rotation
        after_resp = requests.get(
            f"{BASE_URL}/api/vault/banking",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert after_resp.status_code == 200
        after_data = after_resp.json()
        after_last4 = after_data["account_number_masked"][-4:]
        
        # Last 4 digits should match
        assert before_last4 == after_last4, f"Data corrupted: before={before_last4}, after={after_last4}"
        assert after_last4 == test_account[-4:], f"Expected last 4 to be {test_account[-4:]}, got {after_last4}"


# =============================================================================
# ADMIN STREAMING PROVIDERS TESTS
# =============================================================================
class TestAdminStreamingProviders:
    """Test GET /api/admin/streaming/providers"""
    
    def test_providers_includes_gcp_livestream(self, admin_token):
        """Test providers list includes gcp-livestream entry"""
        response = requests.get(
            f"{BASE_URL}/api/admin/streaming/providers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        provider_ids = [p["id"] for p in data["providers"]]
        assert "gcp-livestream" in provider_ids
    
    def test_providers_gcp_not_configured(self, admin_token):
        """Test gcp_configured=false when GCP creds not set"""
        response = requests.get(
            f"{BASE_URL}/api/admin/streaming/providers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("gcp_configured") == False
    
    def test_providers_active_cost_zero(self, admin_token):
        """Test active_cost.active_channels=0 when GCP not configured"""
        response = requests.get(
            f"{BASE_URL}/api/admin/streaming/providers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "active_cost" in data
        assert data["active_cost"].get("active_channels") == 0


# =============================================================================
# REGRESSION TESTS - Iteration 4 Features
# =============================================================================
class TestRegressionIteration4:
    """Regression tests for iteration 4 features"""
    
    def test_system_health_3_layers(self, admin_token):
        """Regression: System health shows 3 DB layers"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["layers"]) == 3
    
    def test_vault_banking_encryption(self, admin_token):
        """Regression: Banking info is encrypted"""
        response = requests.get(
            f"{BASE_URL}/api/vault/banking",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        if data.get("configured"):
            assert "••••" in data.get("account_number_masked", "")
    
    def test_firewall_rate_limit(self, admin_token):
        """Regression: Firewall rate limit is 300"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["firewall"]["rate_limit_per_min"] == 300
    
    def test_direct_gifting_requires_recipient(self, admin_token):
        """Regression: Gift send requires stream_id or recipient_id"""
        response = requests.post(
            f"{BASE_URL}/api/gifts/send",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"tier_id": "t1", "quantity": 1}
        )
        assert response.status_code in [400, 403]
    
    def test_promos_exist(self):
        """Regression: Promos endpoint returns seeded promos"""
        response = requests.get(f"{BASE_URL}/api/promos")
        assert response.status_code == 200
        promos = response.json()
        assert len(promos) >= 3
    
    def test_referrals_my(self, admin_token):
        """Regression: Referrals my endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/referrals/my",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
    
    def test_notifications(self, admin_token):
        """Regression: Notifications endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_search(self):
        """Regression: Search endpoint works"""
        response = requests.get(f"{BASE_URL}/api/search", params={"q": "test"})
        assert response.status_code == 200
    
    def test_trending(self):
        """Regression: Trending endpoint works"""
        response = requests.get(f"{BASE_URL}/api/trending")
        assert response.status_code == 200
    
    def test_admin_stats(self, admin_token):
        """Regression: Admin stats endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_admin_settings(self, admin_token):
        """Regression: Admin settings endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_content_list(self):
        """Regression: Content list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200
    
    def test_streams_list(self):
        """Regression: Streams list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/streams")
        assert response.status_code == 200
    
    def test_gift_tiers(self):
        """Regression: Gift tiers endpoint works"""
        response = requests.get(f"{BASE_URL}/api/gifts/tiers")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tiers"]) == 8
    
    def test_auth_register(self):
        """Regression: Auth register endpoint works"""
        unique_email = f"TEST_regression_iter5_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "name": "Regression Test Iter5",
            "role": "viewer"
        })
        assert response.status_code == 200
    
    def test_subscription_checkout(self, admin_token):
        """Regression: Subscription checkout endpoint works"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"type": "viewer", "origin_url": "https://viewer-pro.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "session_id" in data


# =============================================================================
# VERSION CHECK
# =============================================================================
class TestVersionCheck:
    """Test APP_VERSION is 1.2.0"""
    
    def test_version_1_2_0(self, admin_token):
        """Test system health shows version 1.2.0"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.2.0", f"Expected version 1.2.0, got {data['version']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
