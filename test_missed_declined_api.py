"""
Script Import Dữ Liệu Screening - PHIÊN BẢN HOÀN CHỈNH

CSV Format:
Hospital site,Screening Code,Patient's Initials,Screening Date,Eligibility,Recruited,Unrecruited Reason,Study ID

Site Mapping:
- HTD → 003
- CRH → 011
- NHTD → 020  ← ADDED

QUAN TRỌNG - FORMAT DỮ LIỆU:
1. SCRID: PS-{SITEID}-{NUMBER}
   - HTD: PS-003-0001, PS-003-0002...
   - CRH: PS-011-0001, PS-011-0002...
   - NHTD: PS-020-0001, PS-020-0002...  ← ADDED

2. USUBJID: {SITEID}-{SUBJID} (KHÔNG CÓ 43EN)
   - CSV input: 43EN-003-A-001 hoặc 43EN-020-A-001
   - Database: 003-A-001 hoặc 020-A-001 ✅

Target Database: db_study_43en
"""

import os
import sys
import csv
import re
from datetime import datetime

# ==========================================
# SETUP DJANGO ENVIRONMENT
# ==========================================

script_path = os.path.abspath(__file__)
project_root = os.path.dirname(script_path)

while not os.path.exists(os.path.join(project_root, 'manage.py')):
    parent = os.path.dirname(project_root)
    if parent == project_root:
        project_root = os.path.dirname(script_path)
        break
    project_root = parent

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import environ
    env = environ.Env()
    env_file = os.path.join(project_root, '.env')
    if os.path.exists(env_file):
        environ.Env.read_env(env_file)
        print(f"✅ Loaded .env from: {env_file}")
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()


import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from backends.api.studies.study_43en.services import dashboard

User = get_user_model()

print("\n" + "="*70)
print("TESTING MISSED/DECLINED REASONS API")
print("="*70 + "\n")

# Create a fake request
factory = RequestFactory()
request = factory.get('/api/missed-declined-reasons/?site=all')

# Get a user (adjust username as needed)
try:
    user = User.objects.first()
    if not user:
        print("❌ No users found in database!")
        sys.exit(1)
    
    request.user = user
    print(f"✅ Using user: {user.username}")
    
    # Set required middleware attributes
    request.user_sites = set(['003', '020', '011'])
    request.can_access_all_sites = True
    
    print("✅ Request prepared\n")
    
except Exception as e:
    print(f"❌ Error getting user: {e}")
    sys.exit(1)

# Call the API function
print("Calling get_missed_declined_reasons_api()...\n")

try:
    response = dashboard.get_missed_declined_reasons_api(request)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        
        print("\n✅ API RESPONSE SUCCESS!")
        print("\nResponse Data:")
        print(json.dumps(data, indent=2))
        
        # Check data structure
        if 'success' in data and data['success']:
            print("\n✅ Response indicates success")
            
            if 'data' in data:
                patient_data = data['data'].get('patient', {})
                contact_data = data['data'].get('contact', {})
                
                print(f"\nPatient Total: {patient_data.get('total', 0)}")
                print(f"Contact Total: {contact_data.get('total', 0)}")
                
                print("\nPatient Reasons:")
                for reason, count in patient_data.get('reasons', {}).items():
                    print(f"  - {reason}: {count}")
                
                print("\nContact Reasons:")
                for reason, count in contact_data.get('reasons', {}).items():
                    print(f"  - {reason}: {count}")
            else:
                print("⚠️  No 'data' key in response")
        else:
            print(f"❌ Response indicates failure: {data.get('error', 'Unknown error')}")
    
    else:
        print(f"❌ HTTP {response.status_code}")
        print(f"Response: {response.content}")
        
except AttributeError as e:
    print(f"\n❌ FUNCTION NOT FOUND!")
    print(f"Error: {e}")
    print("\n💡 The function 'get_missed_declined_reasons_api' does not exist in dashboard module.")
    print("   Please check if you've added it to the correct file.")
    
except Exception as e:
    print(f"\n❌ ERROR CALLING API!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")