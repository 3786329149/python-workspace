import asyncio
import httpx
from uuid import UUID

# Gateway URL
GATEWAY_URL = "http://127.0.0.1:5600"
# Superadmin ID
SUPERADMIN_ID = "00000000-0000-0000-0000-aaaaaaaaaaaa"

async def test_tenant_via_gateway():
    # We need to bypass JWT for now or use a test token.
    # But wait, the gateway enforces JWT.
    # Do I have a way to generate a JWT?
    # I can use auth-service to login if I know the credentials.
    # Or I can use internal token if the gateway allows it (it doesn't usually for external calls).
    
    # Actually, the user-service itself checks for the header.
    # Let's try to login as superadmin first.
    
    async with httpx.AsyncClient() as client:
        print("Logging in as superadmin...")
        login_resp = await client.post(
            f"{GATEWAY_URL}/api/v1/auth/login",
            json={"username": "superadmin", "password": "Pass1234"}
        )
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.text}")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. List tenants
        print("\nListing tenants via Gateway...")
        resp = await client.get(f"{GATEWAY_URL}/api/v1/tenants", headers=headers)
        print(f"List tenants status: {resp.status_code}")
        print(f"Tenants: {resp.json()}")

        # 2. Create a tenant
        print("\nCreating a new tenant via Gateway...")
        payload = {
            "name": "Gateway Test Tenant",
            "tenant_key": "gw_tenant",
            "contact_person": "GW Tester",
            "contact_phone": "0987654321"
        }
        resp = await client.post(f"{GATEWAY_URL}/api/v1/tenants", json=payload, headers=headers)
        print(f"Create tenant status: {resp.status_code}")
        if resp.status_code == 201:
            print("✅ Tenant created successfully via Gateway.")
        else:
            print(f"❌ Create failed: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_tenant_via_gateway())
