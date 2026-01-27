"""
Script UPDATE Lý Do Không Tuyển cho Contact Screening Đã Có Sẵn

Mục đích:
- UPDATE trường UNRECRUITED_REASON cho các record SCR_CONTACT đã tồn tại
- Chỉ cần SCRID và SITEID để tìm record
- KHÔNG cần Patient Study ID

CSV Format tối thiểu:
Hospital site,Screening Code,Unrecruited Reason
CRH,CS0001,1. DO NOT live in the same household...
HTD,CS0002,A. Contact does not want to participate...

Target Database: db_study_43en
"""

import os
import sys
import csv
import re

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

from backends.studies.study_43en.models.contact import SCR_CONTACT

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
    'NHTD': '020',
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_site_id(hospital_site):
    """Map hospital site to SITEID"""
    site = hospital_site.strip().upper()
    site = re.sub(r'[^A-Z0-9]', '', site)
    
    if site == 'NHTD':
        return SITE_MAPPING['NHTD']
    if site == 'CRH':
        return SITE_MAPPING['CRH']
    if site == 'HTD':
        return SITE_MAPPING['HTD']
    
    if 'NHTD' in site:
        return SITE_MAPPING['NHTD']
    if 'CRH' in site:
        return SITE_MAPPING['CRH']
    if 'HTD' in site:
        return SITE_MAPPING['HTD']
    
    return SITE_MAPPING.get(site, site)


def convert_screening_code_contact(code, siteid):
    """Convert CS0001 → CS-003-0001"""
    if not code:
        return None
    
    code = code.strip()
    
    # Nếu đã có format CS-XXX-XXXX thì giữ nguyên
    if re.match(r'CS-\d{3}-\d{4}', code):
        return code
    
    # Extract số từ CS0001 → 0001
    match = re.match(r'CS(\d+)', code, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        return f"CS-{siteid}-{number:04d}"
    
    return code


def parse_contact_eligibility_flags(unrecruited_reason):
    """
    Parse lý do để update các boolean flags
    
    Returns:
        dict: Các trường eligibility để update
    """
    flags = {
        'LIVEIN5DAYS3MTHS': True,
        'MEALCAREONCEDAY': True,
        'CONSENTTOSTUDY': True,
    }
    
    if not unrecruited_reason or not unrecruited_reason.strip():
        # Không có lý do → giữ nguyên flags
        return None
    
    reason = unrecruited_reason.strip()
    reason_lower = reason.lower()
    
    # Reason 1: DO NOT live in the same household
    if '1.' in reason or 'do not live' in reason_lower or 'household' in reason_lower:
        flags['LIVEIN5DAYS3MTHS'] = False
        flags['CONSENTTOSTUDY'] = False
    
    # Reason 2: DO NOT share meals or provide direct care
    elif '2.' in reason or 'do not share' in reason_lower or 'meals' in reason_lower or 'direct care' in reason_lower:
        flags['MEALCAREONCEDAY'] = False
        flags['CONSENTTOSTUDY'] = False
    
    # Reason 3: Age < 18 years
    elif '3.' in reason or 'age < 18' in reason_lower or 'age <18' in reason_lower:
        flags['CONSENTTOSTUDY'] = False
    
    # Reason A: Contact does not want to participate
    elif 'a.' in reason_lower or 'does not want' in reason_lower or 'not want' in reason_lower:
        flags['CONSENTTOSTUDY'] = False
    
    # Reason B: Contact not enough time/too busy
    elif 'b.' in reason_lower or 'not enough time' in reason_lower or 'too busy' in reason_lower or 'busy' in reason_lower:
        flags['CONSENTTOSTUDY'] = False
    
    # Reason C: Other reasons
    elif 'c.' in reason_lower or 'other' in reason_lower:
        flags['CONSENTTOSTUDY'] = False
    
    # Unknown reason
    else:
        flags['CONSENTTOSTUDY'] = False
    
    return flags


# ==========================================
# MAIN UPDATE FUNCTION
# ==========================================

def update_unrecruited_reasons(csv_file):
    """Update UNRECRUITED_REASON cho contact screening đã có sẵn"""
    
    total = 0
    updated = 0
    not_found = 0
    skipped = 0
    error = 0
    
    print(f"\n{'='*80}")
    print(f"UPDATE LÝ DO KHÔNG TUYỂN CHO CONTACT SCREENING")
    print(f"{'='*80}")
    print(f"📁 File CSV: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n🔑 Tìm record theo:")
    print(f"   - SCRID (CS-003-0001, CS-011-0002...)")
    print(f"   - SITEID (003, 011, 020)")
    print(f"\n✅ UPDATE:")
    print(f"   - UNRECRUITED_REASON ← từ CSV")
    print(f"   - Boolean flags (LIVEIN5DAYS3MTHS, MEALCAREONCEDAY, CONSENTTOSTUDY)")
    print(f"{'='*80}\n")
    
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        print(f"📋 Các cột trong CSV: {reader.fieldnames}\n")
        
        for row in reader:
            total += 1
            
            # Bỏ qua header phụ
            hospital_site = row.get('Hospital site', '').strip()
            if hospital_site.startswith('Địa điểm') or not hospital_site:
                skipped += 1
                continue
            
            screening_code = row.get('Screening Code', '').strip()
            if not screening_code:
                print(f"⚠️  Dòng {total}: Bỏ qua - Không có Screening Code")
                skipped += 1
                continue
            
            try:
                # Parse data
                siteid = get_site_id(hospital_site)
                scrid = convert_screening_code_contact(screening_code, siteid)
                unrecruited_reason = row.get('Unrecruited Reason', '').strip() or None
                
                # Tìm record trong database
                try:
                    contact = SCR_CONTACT.objects.using(STUDY_DATABASE).get(
                        SCRID=scrid,
                        SITEID=siteid
                    )
                except SCR_CONTACT.DoesNotExist:
                    print(f"❌ {scrid} (Site {siteid}): KHÔNG TÌM THẤY trong database")
                    not_found += 1
                    continue
                
                # Kiểm tra xem đã có lý do chưa
                has_reason_before = bool(contact.UNRECRUITED_REASON)
                
                # Update UNRECRUITED_REASON
                contact.UNRECRUITED_REASON = unrecruited_reason
                
                # Update boolean flags nếu có lý do
                if unrecruited_reason:
                    flags = parse_contact_eligibility_flags(unrecruited_reason)
                    if flags:
                        contact.LIVEIN5DAYS3MTHS = flags['LIVEIN5DAYS3MTHS']
                        contact.MEALCAREONCEDAY = flags['MEALCAREONCEDAY']
                        contact.CONSENTTOSTUDY = flags['CONSENTTOSTUDY']
                
                # Save
                contact.save(using=STUDY_DATABASE)
                
                updated += 1
                
                # Status display
                if has_reason_before:
                    status = "🔄"  # Đã có lý do, đang update
                else:
                    status = "✅"  # Mới thêm lý do
                
                reason_display = (unrecruited_reason[:60] + '...') if unrecruited_reason and len(unrecruited_reason) > 60 else (unrecruited_reason or 'N/A')
                
                print(f"{status} {scrid} | Site: {siteid} | Initial: {contact.INITIAL or 'N/A'} | "
                      f"Reason: {reason_display}")
                
            except Exception as e:
                error += 1
                print(f"❌ Dòng {total} ({screening_code}): Lỗi - {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Kết quả
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ UPDATE")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Đã update:        {updated}")
    print(f"  ❌ Không tìm thấy:   {not_found}")
    print(f"  ⏭️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*80}\n")
    
    # Thống kê sau update
    print("📊 THỐNG KÊ SAU UPDATE:")
    for site_name, site_id in SITE_MAPPING.items():
        total_site = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(SITEID=site_id).count()
        
        # Contacts có lý do
        with_reason = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id,
            UNRECRUITED_REASON__isnull=False
        ).exclude(UNRECRUITED_REASON__exact='').count()
        
        # Contacts không có lý do
        without_reason = total_site - with_reason
        
        print(f"   {site_name} (Site {site_id}): {total_site} contacts total")
        print(f"      - Có lý do:     {with_reason}")
        print(f"      - Không có lý do: {without_reason}")
    
    print()
    
    if error > 0:
        print("⚠️  Có lỗi xảy ra. Vui lòng kiểm tra log.")
    elif updated > 0:
        print("🎉 Update hoàn tất!")
    else:
        print("ℹ️  Không có dữ liệu nào được update.")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print(f"\n📂 Project root: {project_root}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(script_dir, "Book1.csv"),
        os.path.join(project_root, "Book1.csv"),
        os.path.join(script_dir, "contact_reasons.csv"),
        os.path.join(project_root, "contact_reasons.csv"),
    ]
    
    csv_file = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    if not csv_file:
        print("\n❌ Không tìm thấy file CSV tự động.")
        print("📁 Đã tìm trong các đường dẫn:")
        for p in possible_paths:
            print(f"   - {p}")
        
        csv_file = input("\n📁 Nhập đường dẫn file CSV: ").strip()
        
        if not os.path.exists(csv_file):
            print(f"\n❌ File không tồn tại: {csv_file}")
            sys.exit(1)
    
    print("\n" + "="*80)
    print("SCRIPT UPDATE LÝ DO KHÔNG TUYỂN - CONTACT SCREENING")
    print("="*80)
    print(f"📁 CSV File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 CSV FORMAT CẦN THIẾT:")
    print(f"   Hospital site | Screening Code | Unrecruited Reason")
    print(f"   CRH          | CS0001         | 1. DO NOT live in household...")
    print(f"   HTD          | CS0002         | A. Does not want to participate...")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print(f"\n⚡ CHỨC NĂNG:")
    print(f"   - Tìm contact theo SCRID + SITEID")
    print(f"   - Update UNRECRUITED_REASON từ CSV")
    print(f"   - Update boolean flags tự động")
    print(f"   - KHÔNG CẦN Patient Study ID")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn update? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        update_unrecruited_reasons(csv_file)
    else:
        print("\n❌ Đã hủy update.")