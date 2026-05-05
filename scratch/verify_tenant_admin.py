import asyncio
import httpx
from uuid import UUID

GATEWAY_URL = "http://127.0.0.1:5600"
SUPERADMIN_ID = "00000000-0000-0000-0000-aaaaaaaaaaaa"

async def test_tenant_admin_creation():
    headers = {
        "X-Internal-Token": "change-me-in-local-env",
        "X-User-ID": SUPERADMIN_ID
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Login to get superadmin token
        print("Logging in as superadmin...")
        login_resp = await client.post(
            f"{GATEWAY_URL}/api/v1/auth/login",
            json={"username": "superadmin", "password": "Pass1234"}
        )
        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Create tenant with admin info
        print("\nCreating tenant with custom admin...")
        tenant_key = "auto_admin_tenant"
        payload = {
            "name": "Auto Admin Tenant",
            "tenant_key": tenant_key,
            "admin_username": "tenant_boss",
            "admin_email": "boss@auto.com",
            "admin_password": "SpecialPassword123"
        }
        resp = await client.post(f"{GATEWAY_URL}/api/v1/tenants", json=payload, headers=auth_headers)
        print(f"Create tenant status: {resp.status_code}")
        if resp.status_code != 201:
            print(f"Error: {resp.text}")
            return
        
        tenant = resp.json()
        print(f"Tenant created: {tenant['id']}")

        # 3. Try to login with the NEW tenant admin
        print("\nTrying to login with the new tenant admin...")
        login_resp = await client.post(
            f"{GATEWAY_URL}/api/v1/auth/login",
            json={"username": "tenant_boss", "password": "SpecialPassword123"}
        )
        print(f"Login status: {login_resp.status_code}")
        if login_resp.status_code == 200:
            print("✅ Login successful for the new tenant admin!")
            new_token = login_resp.json()["access_token"]
            
            # 4. Verify the new user's profile
            print("\nVerifying profile of the new tenant admin...")
            profile_resp = await client.get(f"{GATEWAY_URL}/api/v1/users/me", headers={"Authorization": f"Bearer {new_token}"})
            profile = profile_resp.json()
            print(f"Profile: {profile}")
            if profile["username"] == "tenant_boss" and profile["is_admin"] is True:
                print("✅ Profile verification successful.")
            else:
                print("❌ Profile mismatch.")
        else:
            print(f"❌ Login failed: {login_resp.text}")

if __name__ == "__main__":
    asyncio.run(test_tenant_admin_creation())
