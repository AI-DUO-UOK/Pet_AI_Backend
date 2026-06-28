import os
import sys
from dotenv import load_dotenv

# Add backend directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Get credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env file.")
    sys.exit(1)

try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except ImportError:
    print("❌ Error: supabase package is not installed. Please run: pip install supabase")
    sys.exit(1)

def create_admin():
    email = "admin@petai.com"
    password = "AdminPass!234"
    
    print(f"⏳ Attempting to create admin user: {email}...")
    
    try:
        # Create user using Supabase Admin API (requires service_role key)
        user_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "user_metadata": {
                "role": "admin",
                "full_name": "System Admin"
            },
            "email_confirm": True
        })
        
        print("✅ Admin user created successfully in Supabase Auth!")
        print(f"User ID: {user_response.user.id}")
        
        # Verify the trigger created the record in public.users
        try:
            db_response = supabase.table("users").select("*").eq("id", user_response.user.id).execute()
            if db_response.data:
                print("✅ Trigger verified: Admin record exists in public.users table.")
                print(f"Database Record: {db_response.data[0]}")
            else:
                # Fallback: Manually insert if trigger didn't run
                print("⚠️ Trigger did not create public.users record. Inserting manually...")
                supabase.table("users").insert({
                    "id": user_response.user.id,
                    "email": email,
                    "role": "admin",
                    "full_name": "System Admin"
                }).execute()
                print("✅ Admin record inserted manually into public.users table.")
        except Exception as db_err:
            print(f"⚠️ Error verifying/inserting into public.users: {db_err}")
            
    except Exception as e:
        # Check if user already exists
        if "already exists" in str(e) or "already registered" in str(e) or "conflict" in str(e).lower():
            print("ℹ️ Admin user already exists in Supabase Auth.")
            # Let's verify or update the role in public.users
            try:
                # Find user in auth.users is not directly possible without listing, but we can check public.users
                users_resp = supabase.table("users").select("*").eq("email", email).execute()
                if users_resp.data:
                    user_rec = users_resp.data[0]
                    if user_rec.get("role") != "admin":
                        print(f"⚠️ User exists but has role '{user_rec.get('role')}'. Updating to 'admin'...")
                        supabase.table("users").update({"role": "admin"}).eq("id", user_rec.get("id")).execute()
                        print("✅ Role updated to 'admin'.")
                    else:
                        print("✅ Admin user already has correct 'admin' role in database.")
                else:
                    print("❌ Admin user exists in Auth but not in public.users. Please delete the user from Supabase Auth and run this script again.")
            except Exception as check_err:
                print(f"❌ Error checking/updating existing user: {check_err}")
        else:
            print(f"❌ Failed to create admin user: {e}")

if __name__ == "__main__":
    create_admin()
