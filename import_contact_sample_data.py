"""
Script Import Contact Sample Data từ CSV

Target Database: db_study_43en

Import vào bảng:
- SAM_CONTACT (Sample Collection - 3 visits V1, V2, V3)

CSV Format (Book6.csv):
- Contact Study ID: 43EN-xxx-B-yyy-z (e.g., 43EN-003-B-001-1)
- Throat V1, Throat V1 Date
- Stool/Rectal V1, Stool/Rectal V1 Date
- Blood V1, Blood V1 Date
- Throat V2, Throat V2 Date
- Stool/Rectal V2, Stool/Rectal V2 Date
- Throat V3, Throat V3 Date
- Stool/Rectal V3, Stool/Rectal V3 Date

Important Notes:
1. Contact ID format: 43EN-SITEID-B-SEQNUM-SUFFIX (e.g., 43EN-003-B-001-1)
2. Need to convert to ENR_CONTACT.USUBJID format: SITEID-B-SEQNUM-SUFFIX (e.g., 003-B-001-1)
3. Stool/Rectal → import vào STOOL field (not rectal swab since CSV doesn't distinguish)
4. CSV only has V1, V2, V3 (no V4 for contacts)
"""

import os
import sys
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
    print("⚠️  django-environ not installed.")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Import models
from backends.studies.study_43en.models.contact import SCR_CONTACT
from backends.studies.study_43en.models.contact import ENR_CONTACT
from backends.studies.study_43en.models.contact import SAM_CONTACT

# ==========================================
# FIX: Set PostgreSQL search_path to include 'data' schema
# ==========================================
from django.db import connections

STUDY_DATABASE = 'db_study_43en'

def set_search_path():
    """Set PostgreSQL search_path to use 'data' schema for db_study_43en"""
    try:
        conn = connections[STUDY_DATABASE]
        with conn.cursor() as cursor:
            cursor.execute("SET search_path TO data, public;")
        print(f"✅ Database '{STUDY_DATABASE}' search_path set to: data, public\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not set search_path: {e}\n")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """Parse date string từ CSV, supports multiple formats"""
    if not date_str or str(date_str).strip() in ['', 'nan', 'NaT', 'None']:
        return None
    
    date_str = str(date_str).strip()
    
    # Remove time component if present
    if ' 00:00:00' in date_str:
        date_str = date_str.replace(' 00:00:00', '')
    
    formats = [
        '%Y-%m-%d',      # 2025-01-15
        '%d-%b-%Y',      # 15-Jan-2025
        '%d-%b-%y',      # 15-Jan-25
        '%d/%m/%Y',      # 15/01/2025
        '%d/%m/%y',      # 15/01/25
        '%m/%d/%Y',      # 01/15/2025
        '%m/%d/%y',      # 01/15/25
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # Fix 2-digit year: if year > 2025, subtract 100
            if fmt in ['%d-%b-%y', '%d/%m/%y', '%m/%d/%y'] and parsed.year > 2025:
                parsed = parsed.replace(year=parsed.year - 100)
            return parsed.date()
        except ValueError:
            continue
    
    print(f"    ⚠️  Cannot parse date: '{date_str}'")
    return None


def parse_yes_no(value):
    """Convert YES/NO to boolean"""
    if not value or str(value).strip() in ['', 'nan']:
        return False
    val_upper = str(value).strip().upper()
    return val_upper in ['YES', 'Y', 'TRUE', '1']


def convert_contact_study_id_to_usubjid(study_id):
    """
    Convert Contact Study ID to USUBJID format
    
    Example: 43EN-003-B-001-1 → 003-B-001-1
    
    Contact ID format: 43EN-SITEID-B-SEQNUM-SUFFIX
    """
    if not study_id or str(study_id).strip() in ['', 'nan']:
        return None
    
    study_id = str(study_id).strip()
    if study_id.startswith('43EN-'):
        return study_id[5:]  # Remove '43EN-' prefix
    return study_id


def extract_siteid_from_contact_id(contact_usubjid):
    """
    Extract SITEID from Contact USUBJID
    
    Example: 003-B-001-1 → 003
    """
    if not contact_usubjid:
        return None
    parts = contact_usubjid.split('-')
    if len(parts) >= 1:
        return parts[0]
    return None


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_contact_sample_data(csv_file):
    """Import Contact Sample data từ CSV vào SAM_CONTACT"""
    
    import pandas as pd
    
    # Set search_path for PostgreSQL
    set_search_path()
    
    # Read CSV file
    if csv_file.endswith('.xlsx') or csv_file.endswith('.xls'):
        df = pd.read_excel(csv_file)
    elif csv_file.endswith('.ods'):
        df = pd.read_excel(csv_file, engine='odf')
    else:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # Statistics counters
    stats = {
        'total': 0,
        'sam_v1': 0, 
        'sam_v2': 0, 
        'sam_v3': 0,
        'skipped': 0,
        'not_found': 0,
        'errors': 0
    }
    
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU IMPORT CONTACT SAMPLE DATA")
    print(f"{'='*80}")
    print(f"📁 File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Số dòng: {len(df)}")
    print(f"📋 Các cột: {df.columns.tolist()}")
    print(f"{'='*80}\n")
    
    for idx, row in df.iterrows():
        stats['total'] += 1
        row_dict = row.to_dict()
        
        # Get Contact Study ID
        study_id_raw = row_dict.get('Contact Study ID', '')
        if not study_id_raw or str(study_id_raw).strip() in ['', 'nan']:
            stats['skipped'] += 1
            continue
        
        # Skip header/template rows
        if 'DD-MMM-YYYY' in str(study_id_raw) or '43EN-xxx-B-yyy-z' in str(study_id_raw):
            stats['skipped'] += 1
            continue
        
        # Convert to USUBJID format
        contact_usubjid = convert_contact_study_id_to_usubjid(study_id_raw)
        if not contact_usubjid:
            stats['skipped'] += 1
            continue
        
        try:
            # Check if SCR_CONTACT exists first (USUBJID is stored on SCR_CONTACT)
            try:
                scr_contact = SCR_CONTACT.objects.using(STUDY_DATABASE).get(USUBJID=contact_usubjid)
            except SCR_CONTACT.DoesNotExist:
                print(f"⚠️  {contact_usubjid}: SCR_CONTACT không tồn tại - Bỏ qua")
                stats['not_found'] += 1
                continue

            # Then get ENR_CONTACT by passing the SCR_CONTACT object (USUBJID is a OneToOneField)
            try:
                enr_contact = ENR_CONTACT.objects.using(STUDY_DATABASE).get(USUBJID=scr_contact)
            except ENR_CONTACT.DoesNotExist:
                print(f"⚠️  {contact_usubjid}: ENR_CONTACT không tồn tại (chưa enroll) - Bỏ qua")
                stats['not_found'] += 1
                continue

            print(f"\n📋 Processing: {contact_usubjid}")
            
            # ==========================================
            # IMPORT SAM_CONTACT (3 VISITS: V1, V2, V3)
            # ==========================================
            # Visit mapping: V1→Sample1, V2→Sample2, V3→Sample3
            
            visits = [
                ('1', 'V1', '1'),  # (SAMPLE_TYPE, CSV suffix, stat key)
                ('2', 'V2', '2'),
                ('3', 'V3', '3'),
            ]
            
            for sample_type, visit_suffix, visit_num in visits:
                # Get sample data for this visit from CSV
                throat = parse_yes_no(row_dict.get(f'Throat {visit_suffix}', ''))
                throat_date = parse_date(row_dict.get(f'Throat {visit_suffix} Date', ''))
                
                # Stool/Rectal → import as STOOL
                stool_rectal = parse_yes_no(row_dict.get(f'Stool/Rectal {visit_suffix}', ''))
                stool_date = parse_date(row_dict.get(f'Stool/Rectal {visit_suffix} Date', ''))
                
                # Blood (V1 only for contacts based on CSV structure)
                blood = parse_yes_no(row_dict.get(f'Blood {visit_suffix}', ''))
                blood_date = parse_date(row_dict.get(f'Blood {visit_suffix} Date', ''))
                
                # Check if any sample was collected
                any_sample = throat or stool_rectal or blood
                
                # Create or update SAM_CONTACT record
                sam_contact, created = SAM_CONTACT.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_contact,
                    SAMPLE_TYPE=sample_type,
                    defaults={
                        'SAMPLE': any_sample,
                        'SAMPLE_STATUS': 'collected' if any_sample else 'not_collected',
                        'REASONIFNO': 'Not collected during this visit' if not any_sample else None,
                        
                        # Throat swab
                        'THROATSWAB': throat,
                        'THROATSWABDATE': throat_date if throat else None,
                        'CULTRES_3': 'Pos' if throat else None,  # Assume positive if collected
                        'KLEBPNEU_3': throat,  # Assume KPN+ if collected
                        
                        # Stool (from Stool/Rectal column)
                        'STOOL': stool_rectal,
                        'STOOLDATE': stool_date if stool_rectal else None,
                        'CULTRES_1': 'Pos' if stool_rectal else None,
                        'KLEBPNEU_1': stool_rectal,
                        
                        # Blood
                        'BLOOD': blood,
                        'BLOODDATE': blood_date if blood else None,
                    }
                )
                
                if not created:
                    # Update existing record
                    updated = False
                    
                    if throat and not sam_contact.THROATSWAB:
                        sam_contact.THROATSWAB = True
                        sam_contact.THROATSWABDATE = throat_date
                        sam_contact.CULTRES_3 = 'Pos'
                        sam_contact.KLEBPNEU_3 = True
                        updated = True
                    
                    if stool_rectal and not sam_contact.STOOL:
                        sam_contact.STOOL = True
                        sam_contact.STOOLDATE = stool_date
                        sam_contact.CULTRES_1 = 'Pos'
                        sam_contact.KLEBPNEU_1 = True
                        updated = True
                    
                    if blood and not sam_contact.BLOOD:
                        sam_contact.BLOOD = True
                        sam_contact.BLOODDATE = blood_date
                        updated = True
                    
                    if updated:
                        # Update overall status
                        sam_contact.SAMPLE = sam_contact.THROATSWAB or sam_contact.STOOL or sam_contact.BLOOD
                        if sam_contact.SAMPLE:
                            sam_contact.SAMPLE_STATUS = 'collected'
                        sam_contact.save(using=STUDY_DATABASE)
                
                if created or updated:
                    stats[f'sam_v{visit_num}'] += 1
                    status = "✅" if any_sample else "⭕"
                    print(f"  {status} SAM_CONTACT V{visit_num}: Throat={throat}, Stool={stool_rectal}, Blood={blood}")
        
        except Exception as e:
            stats['errors'] += 1
            print(f"❌ Lỗi tại dòng {stats['total']} ({study_id_raw}): {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ==========================================
    # KẾT QUẢ TỔNG HỢP
    # ==========================================
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ IMPORT CONTACT SAMPLE")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:         {stats['total']}")
    print(f"\n  📦 SAM_CONTACT:")
    print(f"     - Visit 1 (Sample 1): {stats['sam_v1']}")
    print(f"     - Visit 2 (Sample 2): {stats['sam_v2']}")
    print(f"     - Visit 3 (Sample 3): {stats['sam_v3']}")
    print(f"\n  ⚠️  Bỏ qua:              {stats['skipped']}")
    print(f"  ❓ Không tìm thấy:       {stats['not_found']}")
    print(f"  ❌ Lỗi:                  {stats['errors']}")
    print(f"{'='*80}\n")
    
    # Statistics by site
    print("📊 THỐNG KÊ THEO SITE:")
    site_mapping = {
        'HTD': '003',
        'CRH': '011',
        'NHTD': '020',
    }
    
    for site_name, site_id in site_mapping.items():
        try:
            # Safer approach: find SCR_CONTACT entries for site, then related ENR_CONTACT, then SAM_CONTACT
            scr_qs = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(USUBJID__startswith=f"{site_id}-B-")
            enr_qs = ENR_CONTACT.objects.using(STUDY_DATABASE).filter(USUBJID__in=scr_qs)

            sam_count = SAM_CONTACT.objects.using(STUDY_DATABASE).filter(
                USUBJID__in=enr_qs
            ).count()

            sam_with_samples = SAM_CONTACT.objects.using(STUDY_DATABASE).filter(
                USUBJID__in=enr_qs,
                SAMPLE=True
            ).count()

            print(f"\n   {site_name} (Site {site_id}):")
            print(f"     - Total SAM_CONTACT: {sam_count}")
            print(f"     - With samples: {sam_with_samples}")
        except Exception as e:
            print(f"     - Error getting stats: {e}")
    
    print()
    
    if stats['errors'] > 0:
        print("⚠️  Có lỗi xảy ra. Vui lòng kiểm tra log.")
    else:
        print("🎉 Import hoàn tất thành công!")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print(f"\n📂 Project root: {project_root}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(script_dir, "Book1.csv"),
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        print("\n❌ Không tìm thấy file tự động.")
        print("📁 Đã tìm trong các đường dẫn:")
        for p in possible_paths:
            print(f"   - {p}")
        
        file_path = input("\n📁 Nhập đường dẫn file: ").strip()
        
        if not os.path.exists(file_path):
            print(f"\n❌ File không tồn tại: {file_path}")
            sys.exit(1)
    
    print("\n" + "="*80)
    print("SCRIPT IMPORT CONTACT SAMPLE DATA")
    print("="*80)
    print(f"📁 File: {file_path}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 IMPORT VÀO BẢNG:")
    print(f"   - SAM_CONTACT (3 visits: V1, V2, V3)")
    print(f"\n📋 MAPPING:")
    print(f"   - Contact Study ID: 43EN-xxx-B-yyy-z → xxx-B-yyy-z")
    print(f"   - Throat → THROATSWAB, THROATSWABDATE")
    print(f"   - Stool/Rectal → STOOL, STOOLDATE")
    print(f"   - Blood → BLOOD, BLOODDATE")
    print(f"\n📋 LƯU Ý:")
    print(f"   ✅ Tất cả samples giả định KPN+ nếu được thu thập")
    print(f"   ✅ Visit 1 = Sample 1, Visit 2 = Sample 2, Visit 3 = Sample 3")
    print(f"   ✅ No sample → mark as 'not_collected'")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_contact_sample_data(file_path)
    else:
        print("\n❌ Đã hủy import.")
