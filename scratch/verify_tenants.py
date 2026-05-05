import asyncio
import httpx
from uuid import UUID

USER_SERVICE_URL = "http://127.0.0.1:5601"
INTERNAL_TOKEN = "change-me-in-local-env"
# Superadmin ID from seed_demo_data.py
SUPERADMIN_ID = "00000000-0000-0000-0000-aaaaaaaaaaaa"

async def test_tenant_creation():
    headers = {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-ID": SUPERADMIN_ID
    }
    
    async with httpx.AsyncClient() as client:
        # 1. List tenants
        print("Listing tenants...")
        resp = await client.get(f"{USER_SERVICE_URL}/api/v1/tenants", headers=headers)
        print(f"List tenants status: {resp.status_code}")
        print(f"Tenants: {resp.json()}")

        # 2. Create a tenant
        print("\nCreating a new tenant...")
        payload = {
            "name": "New Test Tenant 2",
            "tenant_key": "test_tenant_2",
            "contact_person": "Tester",
            "contact_phone": "1234567890"
        }
        resp = await client.post(f"{USER_SERVICE_URL}/api/v1/tenants", json=payload, headers=headers)
        print(f"Create tenant status: {resp.status_code}")
        if resp.status_code != 201:
            print(f"Error: {resp.text}")
            return
        
        tenant = resp.json()
        tenant_id = tenant["id"]
        print(f"Created tenant ID: {tenant_id}")

        # 3. Verify root dept was created
        print("\nVerifying root department...")
        resp = await client.get(f"{USER_SERVICE_URL}/api/v1/depts/tree?tenant_id={tenant_id}", headers=headers)
        depts = resp.json()
        print(f"Departments in tenant: {depts}")
        if any(d["name"] == "New Test Tenant总部" for d in depts):
            print("✅ Root department created successfully.")
        else:
            print("❌ Root department NOT found.")

        # 4. Verify roles were created
        print("\nVerifying roles...")
        resp = await client.get(f"{USER_SERVICE_URL}/api/v1/roles?tenant_id={tenant_id}", headers=headers)
        roles = resp.json()
        print(f"Roles in tenant: {roles}")
        role_keys = [r["role_key"] for r in roles]
        if "admin" in role_keys and "user" in role_keys:
            print("✅ Default roles created successfully.")
        else:
            print("❌ Default roles NOT found.")

if __name__ == "__main__":
    asyncio.run(test_tenant_creation())
