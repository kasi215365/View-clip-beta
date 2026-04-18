"""
View/Clip API Tests - Comprehensive backend testing
Tests: Auth, Gifts, Payments, Admin, Streams, Promos
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://viewer-pro.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@viewclip.com"
ADMIN_PASSWORD = "Admin123!"

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_register_viewer(self):
        """Test viewer registration"""
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "viewer"
        assert data["user"]["subscription_status"] == "inactive"
    
    def test_register_streamer(self):
        """Test streamer registration"""
        unique_email = f"TEST_streamer_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Streamer",
            "role": "streamer"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "streamer"
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,
            "password": "TestPass123!",
            "name": "Duplicate",
            "role": "viewer"
        })
        assert response.status_code == 400


class TestGiftTiers:
    """Gift tiers endpoint tests"""
    
    def test_get_gift_tiers(self):
        """Test GET /api/gifts/tiers returns 8 tiers"""
        response = requests.get(f"{BASE_URL}/api/gifts/tiers")
        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data
        tiers = data["tiers"]
        assert len(tiers) == 8, f"Expected 8 tiers, got {len(tiers)}"
        
        # Verify tier IDs t1-t8
        tier_ids = [t["id"] for t in tiers]
        expected_ids = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"]
        assert tier_ids == expected_ids, f"Tier IDs mismatch: {tier_ids}"
    
    def test_gift_tier_prices(self):
        """Test gift tier prices are correct"""
        response = requests.get(f"{BASE_URL}/api/gifts/tiers")
        data = response.json()
        tiers = {t["id"]: t for t in data["tiers"]}
        
        expected_prices = {
            "t1": 10.00, "t2": 20.00, "t3": 35.00, "t4": 50.00,
            "t5": 72.00, "t6": 100.00, "t7": 200.00, "t8": 300.00
        }
        for tier_id, expected_price in expected_prices.items():
            assert tiers[tier_id]["price"] == expected_price, f"Tier {tier_id} price mismatch"
    
    def test_gift_tier_values(self):
        """Test gift tier value_per_unit (streamer earnings)"""
        response = requests.get(f"{BASE_URL}/api/gifts/tiers")
        data = response.json()
        tiers = {t["id"]: t for t in data["tiers"]}
        
        # All tiers should have value_per_unit >= 0.002 (base rate)
        for tier_id, tier in tiers.items():
            assert tier["value_per_unit"] >= 0.002, f"Tier {tier_id} value below base rate"
            assert tier["qty"] == 500, f"Tier {tier_id} qty should be 500"


class TestGiftWallet:
    """Gift wallet endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_wallet_authenticated(self, auth_token):
        """Test GET /api/gifts/wallet returns wallet map"""
        response = requests.get(
            f"{BASE_URL}/api/gifts/wallet",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "wallet" in data
        assert isinstance(data["wallet"], dict)
    
    def test_get_wallet_unauthenticated(self):
        """Test wallet endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/gifts/wallet")
        assert response.status_code in [401, 403]


class TestPaymentsCheckout:
    """Stripe checkout endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_checkout_subscribe_viewer(self, auth_token):
        """Test POST /api/payments/checkout/subscribe for viewer ($7)"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            json={"type": "viewer", "origin_url": "https://test.com"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        data = response.json()
        assert "url" in data, "Missing checkout URL"
        assert "session_id" in data, "Missing session_id"
        assert data["url"].startswith("https://"), "Invalid checkout URL"
    
    def test_checkout_subscribe_streamer(self, auth_token):
        """Test POST /api/payments/checkout/subscribe for streamer ($50)"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/subscribe",
            json={"type": "streamer", "origin_url": "https://test.com"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        data = response.json()
        assert "url" in data
        assert "session_id" in data
    
    def test_checkout_gift_bundle_all_tiers(self, auth_token):
        """Test POST /api/payments/checkout/gift-bundle for all 8 tiers"""
        tier_ids = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"]
        for tier_id in tier_ids:
            response = requests.post(
                f"{BASE_URL}/api/payments/checkout/gift-bundle",
                json={"tier_id": tier_id, "origin_url": "https://test.com"},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200, f"Gift bundle checkout failed for {tier_id}: {response.text}"
            data = response.json()
            assert "url" in data, f"Missing URL for tier {tier_id}"
            assert "session_id" in data, f"Missing session_id for tier {tier_id}"
    
    def test_checkout_invalid_tier(self, auth_token):
        """Test gift bundle checkout with invalid tier"""
        response = requests.post(
            f"{BASE_URL}/api/payments/checkout/gift-bundle",
            json={"tier_id": "invalid", "origin_url": "https://test.com"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 400


class TestAdminSettings:
    """Admin settings endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_admin_settings(self, admin_token):
        """Test GET /api/admin/settings returns defaults"""
        response = requests.get(
            f"{BASE_URL}/api/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check default values
        assert data.get("earnings_per_view") == 0.005, "earnings_per_view should be 0.005"
        assert data.get("streamer_sub_price") == 50.0, "streamer_sub_price should be 50"
        assert data.get("budget_alert_percent") == 80, "budget_alert_percent should be 80"
        assert data.get("viewer_sub_price") == 7.0, "viewer_sub_price should be 7"
    
    def test_update_admin_settings(self, admin_token):
        """Test POST /api/admin/settings updates values"""
        response = requests.post(
            f"{BASE_URL}/api/admin/settings",
            json={"budget_alert_percent": 85},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("budget_alert_percent") == 85
        
        # Reset to default
        requests.post(
            f"{BASE_URL}/api/admin/settings",
            json={"budget_alert_percent": 80},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_admin_settings_requires_admin(self):
        """Test settings endpoint requires admin role"""
        # Register a viewer
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        viewer_token = reg_response.json()["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/admin/settings",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 403


class TestAdminStats:
    """Admin stats endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_admin_stats(self, admin_token):
        """Test GET /api/admin/stats returns aggregates"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "users" in data
        assert "streams" in data
        assert "content" in data
        assert "gifts" in data
        assert "financials" in data
        
        # Check users structure
        assert "total" in data["users"]
        assert "viewers" in data["users"]
        assert "streamers" in data["users"]
        assert "active_subscriptions" in data["users"]
        
        # Check financials structure
        assert "total_revenue" in data["financials"]
        assert "total_payouts_owed" in data["financials"]
        assert "net" in data["financials"]


class TestAdminUsers:
    """Admin users endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_admin_users(self, admin_token):
        """Test GET /api/admin/users lists users without sensitive data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        
        # Check no sensitive data
        for user in data["users"]:
            assert "_id" not in user, "MongoDB _id should not be exposed"
            assert "password_hash" not in user, "password_hash should not be exposed"


class TestAdminPayouts:
    """Admin payouts endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_trigger_payouts(self, admin_token):
        """Test POST /api/admin/payouts/trigger processes earnings"""
        response = requests.post(
            f"{BASE_URL}/api/admin/payouts/trigger",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "streamers_paid" in data
        assert "total_paid" in data
    
    def test_list_payouts(self, admin_token):
        """Test GET /api/admin/payouts lists payout history"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payouts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "payouts" in data
        assert isinstance(data["payouts"], list)


class TestPromos:
    """Self-promotion endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_list_promos(self):
        """Test GET /api/promos (public)"""
        response = requests.get(f"{BASE_URL}/api/promos")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_and_delete_promo(self, admin_token):
        """Test POST /api/promos and DELETE /api/promos/{id}"""
        # Create promo
        promo_data = {
            "title": "TEST_Promo",
            "description": "Test promo description",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "video_url": "https://example.com/video.mp4"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/promos",
            json=promo_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200, f"Create promo failed: {create_response.text}"
        promo = create_response.json()
        assert promo["title"] == "TEST_Promo"
        assert promo["is_promo"] == True
        promo_id = promo["id"]
        
        # Delete promo
        delete_response = requests.delete(
            f"{BASE_URL}/api/promos/{promo_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200
    
    def test_create_promo_requires_admin(self):
        """Test promo creation requires admin"""
        # Register a viewer
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        viewer_token = reg_response.json()["token"]
        
        response = requests.post(
            f"{BASE_URL}/api/promos",
            json={"title": "Test", "description": "Test", "thumbnail_url": "x", "video_url": "y"},
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 403


class TestStreams:
    """Live streams endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_list_streams(self):
        """Test GET /api/streams"""
        response = requests.get(f"{BASE_URL}/api/streams")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_stream_as_admin(self, admin_token):
        """Test POST /api/streams (admin can create without subscription)"""
        stream_data = {
            "title": "TEST_Admin Stream",
            "description": "Test stream description",
            "video_url": "https://example.com/stream.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        response = requests.post(
            f"{BASE_URL}/api/streams",
            json=stream_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Create stream failed: {response.text}"
        stream = response.json()
        assert stream["title"] == "TEST_Admin Stream"
        assert stream["is_live"] == True
        
        # End the stream
        end_response = requests.post(
            f"{BASE_URL}/api/streams/{stream['id']}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert end_response.status_code == 200
        end_data = end_response.json()
        assert "earnings" in end_data
        assert "qualified_views" in end_data
    
    def test_create_stream_requires_streamer_sub(self):
        """Test stream creation requires streamer subscription"""
        # Register a streamer without subscription
        unique_email = f"TEST_streamer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Streamer",
            "role": "streamer"
        })
        streamer_token = reg_response.json()["token"]
        
        response = requests.post(
            f"{BASE_URL}/api/streams",
            json={"title": "Test", "description": "Test", "video_url": "x", "thumbnail_url": "y"},
            headers={"Authorization": f"Bearer {streamer_token}"}
        )
        assert response.status_code == 403, "Streamer without subscription should not create streams"


class TestStreamerConnect:
    """Streamer Connect onboarding tests"""
    
    def test_connect_onboard_mock(self):
        """Test POST /api/streamers/connect/onboard (mock)"""
        # Register a streamer
        unique_email = f"TEST_streamer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Streamer",
            "role": "streamer"
        })
        streamer_token = reg_response.json()["token"]
        
        response = requests.post(
            f"{BASE_URL}/api/streamers/connect/onboard",
            headers={"Authorization": f"Bearer {streamer_token}"}
        )
        assert response.status_code == 200, f"Connect onboard failed: {response.text}"
        data = response.json()
        assert data["status"] == "active"
        assert "onboarding_url" in data
    
    def test_connect_onboard_requires_streamer(self):
        """Test connect onboard requires streamer role"""
        # Register a viewer
        unique_email = f"TEST_viewer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Viewer",
            "role": "viewer"
        })
        viewer_token = reg_response.json()["token"]
        
        response = requests.post(
            f"{BASE_URL}/api/streamers/connect/onboard",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 403


class TestWebhook:
    """Stripe webhook endpoint tests"""
    
    def test_webhook_endpoint_exists(self):
        """Test POST /api/webhook/stripe is exposed"""
        response = requests.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b"test",
            headers={"Content-Type": "application/json"}
        )
        # Should return 400 (invalid webhook) not 404
        assert response.status_code != 404, "Webhook endpoint should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
