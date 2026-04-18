"""
View/Clip Iteration 7 Tests — Production Security Hardening
Tests:
- TOTP secret encryption at rest (Fernet)
- 10 one-time recovery codes on 2FA enable
- Login via recovery codes (one-time use)
- Recovery code regeneration endpoint
- Key rotation re-encrypts TOTP secrets
- Public /api/health and /api/ready probes
- X-Request-ID middleware
- Admin system health version 1.4.0
- Anomaly alerts (brute-force, new IP)
"""

import pytest
import requests
import os
import pyotp
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@viewclip.com"
ADMIN_PASSWORD = "Admin123!"


class TestPublicHealthEndpoints:
    """Test public health/ready probes (no auth required)"""
    
    def test_health_endpoint_public_no_auth(self):
        """GET /api/health is public, returns 200 with status:ok and version:1.4.0"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.4.0", f"Expected version 1.4.0, got {data.get('version')}"
        print(f"✓ /api/health returns {data}")
    
    def test_ready_endpoint_public_no_auth(self):
        """GET /api/ready is public, returns status:ready when DB healthy"""
        response = requests.get(f"{BASE_URL}/api/ready")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ready", f"Expected status:ready, got {data}"
        print(f"✓ /api/ready returns {data}")


class TestXRequestIDMiddleware:
    """Test X-Request-ID header middleware"""
    
    def test_response_has_x_request_id(self):
        """Every response carries X-Request-ID header"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert "X-Request-ID" in response.headers or "x-request-id" in response.headers
        req_id = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
        assert req_id is not None and len(req_id) > 0
        print(f"✓ Response has X-Request-ID: {req_id}")
    
    def test_x_request_id_echoed_back(self):
        """When client supplies X-Request-ID, it is echoed back"""
        custom_id = "test-custom-request-id-12345"
        response = requests.get(f"{BASE_URL}/api/health", headers={"X-Request-ID": custom_id})
        returned_id = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
        assert returned_id == custom_id, f"Expected {custom_id}, got {returned_id}"
        print(f"✓ X-Request-ID echoed back: {returned_id}")


class TestAdminSystemHealth:
    """Test admin system health endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token (assumes 2FA is disabled)"""
        response = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if data.get("require_2fa"):
                pytest.skip("2FA is enabled on admin account - disable it first")
            return data.get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_admin_system_health_version(self, admin_token):
        """GET /api/admin/system/health returns version 1.4.0"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.4.0", f"Expected 1.4.0, got {data.get('version')}"
        assert "firewall" in data
        assert "encryption" in data
        print(f"✓ Admin system health version: {data['version']}")


class TestTOTPEncryptionAndRecoveryCodes:
    """Test TOTP secret encryption at rest and recovery codes"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin token and ensure 2FA is disabled"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        
        if data.get("require_2fa"):
            pytest.skip("2FA is enabled - need to disable first")
        
        token = data.get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_2fa_enable_returns_recovery_codes(self, admin_session):
        """POST /api/admin/auth/2fa/enable returns 10 recovery codes"""
        # Setup 2FA
        setup_resp = admin_session.post(f"{BASE_URL}/api/admin/auth/2fa/setup")
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        secret = setup_data["secret"]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        # Enable 2FA
        enable_resp = admin_session.post(f"{BASE_URL}/api/admin/auth/2fa/enable", json={"code": code})
        assert enable_resp.status_code == 200, f"Enable failed: {enable_resp.text}"
        enable_data = enable_resp.json()
        
        # Verify recovery codes
        assert "recovery_codes" in enable_data, "Missing recovery_codes in response"
        recovery_codes = enable_data["recovery_codes"]
        assert len(recovery_codes) == 10, f"Expected 10 recovery codes, got {len(recovery_codes)}"
        assert "recovery_codes_warning" in enable_data
        
        print(f"✓ 2FA enable returned {len(recovery_codes)} recovery codes")
        print(f"  Warning: {enable_data['recovery_codes_warning']}")
        
        # Store for later tests
        self.__class__.totp_secret = secret
        self.__class__.recovery_codes = recovery_codes
        
        return recovery_codes
    
    def test_login_with_recovery_code_works(self, admin_session):
        """Login with recovery code succeeds (200, portal=staff)"""
        # First ensure 2FA is enabled and we have recovery codes
        if not hasattr(self.__class__, 'recovery_codes') or not self.__class__.recovery_codes:
            self.test_2fa_enable_returns_recovery_codes(admin_session)
        
        recovery_code = self.__class__.recovery_codes[0]
        
        # Login with recovery code
        login_resp = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": recovery_code
        })
        assert login_resp.status_code == 200, f"Recovery code login failed: {login_resp.text}"
        login_data = login_resp.json()
        assert login_data.get("portal") == "staff", f"Expected portal=staff, got {login_data.get('portal')}"
        assert "token" in login_data
        
        print(f"✓ Login with recovery code succeeded (portal={login_data['portal']})")
        
        # Store used code
        self.__class__.used_recovery_code = recovery_code
        return login_data
    
    def test_recovery_code_cannot_be_reused(self, admin_session):
        """Same recovery code must NOT work a second time (401)"""
        if not hasattr(self.__class__, 'used_recovery_code'):
            self.test_login_with_recovery_code_works(admin_session)
        
        used_code = self.__class__.used_recovery_code
        
        # Try to reuse the same recovery code
        login_resp = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": used_code
        })
        assert login_resp.status_code == 401, f"Expected 401 for reused code, got {login_resp.status_code}"
        print(f"✓ Reused recovery code correctly rejected (401)")
    
    def test_audit_log_recovery_used(self, admin_session):
        """audit_log contains action=admin.auth.recovery_used with meta.remaining"""
        audit_resp = admin_session.get(f"{BASE_URL}/api/admin/audit")
        assert audit_resp.status_code == 200
        audit_data = audit_resp.json()
        
        recovery_entries = [a for a in audit_data.get("audit", []) 
                          if a.get("action") == "admin.auth.recovery_used"]
        
        assert len(recovery_entries) > 0, "No admin.auth.recovery_used entries found"
        latest = recovery_entries[0]
        assert "meta" in latest
        assert "remaining" in latest["meta"], "Missing 'remaining' in meta"
        
        print(f"✓ audit_log has admin.auth.recovery_used with remaining={latest['meta']['remaining']}")


class TestRecoveryCodeRegeneration:
    """Test recovery code regeneration endpoint"""
    
    @pytest.fixture
    def admin_session_with_2fa(self):
        """Get admin session with 2FA enabled"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        
        if data.get("require_2fa"):
            # Need to login with TOTP
            if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
                pytest.skip("TOTP secret not available")
            
            totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
            code = totp.now()
            response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "totp_code": code
            })
            data = response.json()
        
        token = data.get("token")
        if not token:
            pytest.skip("Could not get admin token")
        
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_regenerate_recovery_codes(self, admin_session_with_2fa):
        """POST /api/admin/auth/2fa/recovery-codes/regenerate returns 10 fresh codes"""
        if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
            pytest.skip("TOTP secret not available")
        
        totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
        code = totp.now()
        
        regen_resp = admin_session_with_2fa.post(
            f"{BASE_URL}/api/admin/auth/2fa/recovery-codes/regenerate",
            json={"code": code}
        )
        assert regen_resp.status_code == 200, f"Regenerate failed: {regen_resp.text}"
        regen_data = regen_resp.json()
        
        assert "recovery_codes" in regen_data
        new_codes = regen_data["recovery_codes"]
        assert len(new_codes) == 10, f"Expected 10 codes, got {len(new_codes)}"
        
        print(f"✓ Regenerated {len(new_codes)} fresh recovery codes")
        
        # Store new codes
        self.__class__.new_recovery_codes = new_codes
        return new_codes
    
    def test_old_codes_invalidated_after_regenerate(self, admin_session_with_2fa):
        """Old recovery codes are invalidated after regeneration"""
        if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'recovery_codes'):
            pytest.skip("Original recovery codes not available")
        
        # Try to use an old code (that wasn't used before)
        old_codes = TestTOTPEncryptionAndRecoveryCodes.recovery_codes
        # Find an unused old code (skip index 0 which was used)
        old_code = old_codes[1] if len(old_codes) > 1 else old_codes[0]
        
        login_resp = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": old_code
        })
        
        # Should fail because codes were regenerated
        assert login_resp.status_code == 401, f"Old code should be rejected, got {login_resp.status_code}"
        print(f"✓ Old recovery code correctly rejected after regeneration (401)")


class TestKeyRotationReencryptsTOTP:
    """Test that key rotation re-encrypts TOTP secrets"""
    
    @pytest.fixture
    def admin_session_with_2fa(self):
        """Get admin session with 2FA enabled"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        
        if data.get("require_2fa"):
            if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
                pytest.skip("TOTP secret not available")
            
            totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
            code = totp.now()
            response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "totp_code": code
            })
            data = response.json()
        
        token = data.get("token")
        if not token:
            pytest.skip("Could not get admin token")
        
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_rotate_keys_includes_totp_counts(self, admin_session_with_2fa):
        """POST /api/admin/system/rotate-keys includes totp_rotated & totp_failed"""
        rotate_resp = admin_session_with_2fa.post(f"{BASE_URL}/api/admin/system/rotate-keys")
        assert rotate_resp.status_code == 200, f"Rotate keys failed: {rotate_resp.text}"
        rotate_data = rotate_resp.json()
        
        assert "totp_rotated" in rotate_data, "Missing totp_rotated in response"
        assert "totp_failed" in rotate_data, "Missing totp_failed in response"
        
        print(f"✓ Key rotation: totp_rotated={rotate_data['totp_rotated']}, totp_failed={rotate_data['totp_failed']}")
        return rotate_data
    
    def test_totp_still_works_after_key_rotation(self, admin_session_with_2fa):
        """Same TOTP authenticator still works after key rotation"""
        if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
            pytest.skip("TOTP secret not available")
        
        # First rotate keys
        self.test_rotate_keys_includes_totp_counts(admin_session_with_2fa)
        
        # Wait a moment for the rotation to complete
        time.sleep(1)
        
        # Now try to login with the same TOTP secret
        totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
        code = totp.now()
        
        login_resp = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": code
        })
        
        assert login_resp.status_code == 200, f"Login after key rotation failed: {login_resp.text}"
        login_data = login_resp.json()
        assert login_data.get("portal") == "staff"
        
        print(f"✓ TOTP login still works after key rotation (re-encryption seamless)")


class Test2FADisableAfterEncryption:
    """Test 2FA disable works after secret was stored encrypted"""
    
    @pytest.fixture
    def admin_session_with_2fa(self):
        """Get admin session with 2FA enabled"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        
        if data.get("require_2fa"):
            if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
                pytest.skip("TOTP secret not available")
            
            totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
            code = totp.now()
            response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "totp_code": code
            })
            data = response.json()
        
        token = data.get("token")
        if not token:
            pytest.skip("Could not get admin token")
        
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_2fa_disable_with_encrypted_secret(self, admin_session_with_2fa):
        """POST /api/admin/auth/2fa/disable works after secret was stored encrypted"""
        if not hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
            pytest.skip("TOTP secret not available")
        
        totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
        code = totp.now()
        
        disable_resp = admin_session_with_2fa.post(
            f"{BASE_URL}/api/admin/auth/2fa/disable",
            json={"code": code}
        )
        assert disable_resp.status_code == 200, f"Disable failed: {disable_resp.text}"
        disable_data = disable_resp.json()
        
        assert "message" in disable_data
        assert "disabled" in disable_data["message"].lower()
        
        print(f"✓ 2FA disabled successfully (decrypt path works)")
        
        # Verify 2FA is now disabled
        status_resp = admin_session_with_2fa.get(f"{BASE_URL}/api/admin/auth/2fa/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["enabled"] == False, "2FA should be disabled"
        
        print(f"✓ 2FA status confirmed disabled")


class TestAnomalyAlerts:
    """Test security anomaly alerts"""
    
    def test_brute_force_alert_after_3_failures(self):
        """3 failed admin login attempts creates brute_force notification"""
        # Create 3 failed login attempts
        for i in range(3):
            requests.post(f"{BASE_URL}/api/admin/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": "WrongPassword123!"
            })
            time.sleep(0.5)
        
        # Login successfully to check notifications
        login_resp = requests.post(f"{BASE_URL}/api/admin/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login to check notifications")
        
        token = login_resp.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check notifications
        notif_resp = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert notif_resp.status_code == 200
        notifs = notif_resp.json().get("notifications", [])
        
        # Look for security_anomaly with kind=brute_force
        brute_force_notifs = [n for n in notifs 
                             if n.get("type") == "security_anomaly" 
                             and n.get("data", {}).get("kind") == "brute_force"]
        
        assert len(brute_force_notifs) > 0, "No brute_force anomaly notification found"
        print(f"✓ Brute-force anomaly notification created: {brute_force_notifs[0]['title']}")


# Cleanup fixture to ensure 2FA is disabled at end
@pytest.fixture(scope="session", autouse=True)
def cleanup_2fa():
    """Ensure 2FA is disabled on admin account at end of test run"""
    yield
    
    # Try to disable 2FA
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login
    response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if response.status_code != 200:
        return
    
    data = response.json()
    
    if data.get("require_2fa"):
        # Need to login with TOTP
        if hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
            totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
            code = totp.now()
            response = session.post(f"{BASE_URL}/api/admin/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "totp_code": code
            })
            data = response.json()
    
    token = data.get("token")
    if not token:
        return
    
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Check if 2FA is enabled
    status_resp = session.get(f"{BASE_URL}/api/admin/auth/2fa/status")
    if status_resp.status_code == 200:
        status = status_resp.json()
        if status.get("enabled"):
            # Disable it
            if hasattr(TestTOTPEncryptionAndRecoveryCodes, 'totp_secret'):
                totp = pyotp.TOTP(TestTOTPEncryptionAndRecoveryCodes.totp_secret)
                code = totp.now()
                session.post(f"{BASE_URL}/api/admin/auth/2fa/disable", json={"code": code})
                print("\n✓ Cleanup: 2FA disabled on admin account")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
