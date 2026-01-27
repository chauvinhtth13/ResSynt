"""
Script Import Dữ Liệu Contact Screening từ CSV vào Database

Target Database: db_study_43en
Target Schema: data
Table: SCR_CONTACT

Site Mapping:
- HTD → 003
- CRH → 011
- NHTD → 020  ← ADDED

Logic:
- Eligibility=YES và Recruited=YES → is_confirmed=True, tạo SUBJID và USUBJID
- Khác → is_confirmed=False, không tạo SUBJID/USUBJID

Eligibility Criteria cho Contact:
1. LIVEIN5DAYS3MTHS - Lived together ≥5 days in last 3 months
2. MEALCAREONCEDAY - Shared meals/care ≥1 time per day  
3. CONSENTTOSTUDY - Consent to participate

Unrecruited Reasons:
1. Age < 18 years → Không có trường riêng, lưu vào UNRECRUITED_REASON
2. DO NOT live in the same household 5 days/week during last 3 months → LIVEIN5DAYS3MTHS = False
3. DO NOT share meals or provide direct care → MEALCAREONCEDAY = False

SUBJIDENROLLSTUDY: Patient Study ID (USUBJID của SCR_CASE)
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
    print("⚠️  django-environ not installed.")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Import models
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.models.contact import SCR_CONTACT

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'
STUDYID = '43EN'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
    'NHTD': '020',  # ← ADDED
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """Parse date string từ CSV"""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    date_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', date_str, flags=re.IGNORECASE)
    
    formats = [
        '%d-%b-%y',   # 3-Jul-24, 6-Nov-25
        '%d-%b-%Y',   # 3-Jul-2024
        '%d/%m/%Y',   # 03/07/2024
        '%d/%m/%y',   # 03/07/24
        '%Y-%m-%d',   # 2024-07-03
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if fmt in ['%d-%b-%y', '%d/%m/%y'] and parsed.year > 2025:
                parsed = parsed.replace(year=parsed.year - 100)
            return parsed.date()
        except ValueError:
            continue
    
    print(f"    ⚠️  Không parse được date: '{date_str}'")
    return None


def parse_yes_no(value):
    """Convert YES/NO/Yes/No to boolean"""
    if not value:
        return False
    return value.strip().upper() == 'YES'


def get_site_id(hospital_site):
    """Map hospital site to SITEID"""
    site = hospital_site.strip().upper()
    site = re.sub(r'[^A-Z0-9]', '', site)
    
    # Check exact matches first
    if site == 'NHTD':  # ← ADDED
        return SITE_MAPPING['NHTD']
    if site == 'CRH':
        return SITE_MAPPING['CRH']
    if site == 'HTD':
        return SITE_MAPPING['HTD']
    
    # Check partial matches
    if 'NHTD' in site:  # ← ADDED
        return SITE_MAPPING['NHTD']
    if 'CRH' in site:
        return SITE_MAPPING['CRH']
    if 'HTD' in site:
        return SITE_MAPPING['HTD']
    
    return SITE_MAPPING.get(site, site)


def convert_screening_code_contact(code, siteid):
    """
    Convert CS0001 → CS-003-0001 or CS-020-0001
    
    Args:
        code: Screening code từ CSV (eg. CS0001, CS001)
        siteid: Site ID (eg. 003, 011, 020)
    
    Returns:
        str: Formatted SCRID (eg. CS-003-0001, CS-020-0001)
    """
    if not code:
        return None
    
    code = code.strip()
    
    # Nếu đã có format CS-XXX-XXXX thì giữ nguyên
    if re.match(r'CS-\d{3}-\d{4}', code):
        return code
    
    # Extract số từ CS0001 hoặc CS001 → 0001
    match = re.match(r'CS(\d+)', code, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        return f"CS-{siteid}-{number:04d}"
    
    return code


def convert_patient_study_id(study_id):
    """
    Convert Patient Study ID to USUBJID của SCR_CASE
    43EN-003-A-001 → 003-A-001
    43EN-020-A-001 → 020-A-001  ← ADDED
    003-A-001 → 003-A-001
    020-A-001 → 020-A-001  ← ADDED
    """
    if not study_id:
        return None
    
    study_id = study_id.strip()
    
    # Remove 43EN prefix if present
    if study_id.startswith('43EN-'):
        return study_id[5:]  # Remove "43EN-"
    
    # Fix typo 43DN → 43EN
    if study_id.startswith('43DN-'):
        print(f"    ⚠️  Fixed typo: 43DN → 43EN in {study_id}")
        return study_id[5:]  # Remove "43DN-"
    
    return study_id


def get_next_contact_subjid(siteid, patient_number):
    """
    Lấy SUBJID tiếp theo cho contact
    Format: B-001-1, B-001-2, ... (B-{patient_number}-{index})
    Supports all sites: 003, 011, 020
    """
    last_contact = (
        SCR_CONTACT.objects
        .using(STUDY_DATABASE)
        .filter(SITEID=siteid)
        .exclude(SUBJID__isnull=True)
        .exclude(SUBJID__exact='')
        .filter(SUBJID__startswith=f'B-{patient_number}-')
        .order_by('-SUBJID')
        .first()
    )
    
    if last_contact and last_contact.SUBJID:
        try:
            last_index = int(last_contact.SUBJID.split('-')[-1])
            return f"B-{patient_number}-{last_index + 1}"
        except (ValueError, IndexError):
            pass
    
    return f"B-{patient_number}-1"


def parse_contact_eligibility_criteria(eligibility, recruited, unrecruited_reason):
    """
    Parse eligibility criteria cho Contact từ CSV
    
    Mapping lý do không tuyển:
    - "1. Age < 18 years" → Lưu vào UNRECRUITED_REASON, CONSENTTOSTUDY = False
    - "2. DO NOT live in the same household 5 days/week during last 3 months" 
      → LIVEIN5DAYS3MTHS = False
    - "3. DO NOT share meals or provide direct care"
      → MEALCAREONCEDAY = False
    
    Returns:
        dict: Các trường eligibility criteria
    """
    criteria = {
        'LIVEIN5DAYS3MTHS': True,      # Lived together ≥5 days in last 3 months
        'MEALCAREONCEDAY': True,        # Shared meals/care ≥1 time per day
        'CONSENTTOSTUDY': True,         # Consent to participate
        'UNRECRUITED_REASON': None,
    }

    is_eligible = eligibility and recruited

    if is_eligible:
        return criteria

    # Không đủ điều kiện → phân tích lý do
    reason = (unrecruited_reason or '').strip().lower()

    # Reason 1: Age < 18 years
    if '1.' in reason or 'age < 18' in reason or 'age <18' in reason or 'tuổi' in reason:
        criteria['CONSENTTOSTUDY'] = False

    # Reason 2: DO NOT live in the same household
    elif '2.' in reason or 'not live' in reason or 'do not live' in reason or 'household' in reason or 'sống' in reason:
        criteria['LIVEIN5DAYS3MTHS'] = False
        criteria['CONSENTTOSTUDY'] = False

    # Reason 3: DO NOT share meals or provide direct care
    elif '3.' in reason or 'not share' in reason or 'do not share' in reason or 'meals' in reason or 'care' in reason or 'bữa ăn' in reason:
        criteria['MEALCAREONCEDAY'] = False
        criteria['CONSENTTOSTUDY'] = False

    # Các lý do khác
    else:
        # Không match với các lý do cụ thể → lưu vào UNRECRUITED_REASON
        # Set CONSENTTOSTUDY = False để đánh dấu không tuyển
        criteria['CONSENTTOSTUDY'] = False

    # Luôn lưu lý do gốc vào UNRECRUITED_REASON
    criteria['UNRECRUITED_REASON'] = unrecruited_reason if unrecruited_reason else None

    return criteria


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_contact_csv_to_db(csv_file):
    """Import contact screening data từ CSV vào database"""
    
    total = 0
    success = 0
    error = 0
    skipped = 0
    
    # Track SUBJID đã sử dụng trong session
    used_subjids = {}  # {(siteid, patient_number): last_index}
    
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU CONTACT SCREENING")
    print(f"{'='*80}")
    print(f"📁 File CSV: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Schema: data")
    print(f"📋 Study ID: {STUDYID}")
    print(f"\n🔑 FORMAT:")
    print(f"   - SCRID: CS-{{SITEID}}-{{NUMBER}} (e.g., CS-003-0001, CS-020-0001)")
    print(f"   - USUBJID: {{SITEID}}-{{SUBJID}} (e.g., 003-B-001-1, 020-B-001-1)")
    print(f"   - Patient USUBJID: {{SITEID}}-{{SUBJID}} (e.g., 003-A-001, 020-A-001)")
    print(f"{'='*80}\n")
    
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        print(f"📋 Các cột trong CSV: {reader.fieldnames}\n")
        
        for row in reader:
            total += 1
            
            # Bỏ qua header phụ
            hospital_site = row.get('Hospital site', '').strip()
            if hospital_site.startswith('Địa điểm') or not hospital_site:
                print(f"⏭️  Dòng {total}: Bỏ qua - Header hoặc dòng trống")
                skipped += 1
                continue
            
            screening_code = row.get('Screening Code', '').strip()
            if not screening_code:
                print(f"⚠️  Dòng {total}: Bỏ qua - Không có Screening Code")
                skipped += 1
                continue
            
            # Lấy Patient Study ID (bắt buộc cho contact)
            patient_study_id_raw = row.get('Patient Study ID', '').strip()
            if not patient_study_id_raw:
                print(f"⚠️  Dòng {total} ({screening_code}): Bỏ qua - Không có Patient Study ID")
                skipped += 1
                continue
            
            try:
                # Parse dữ liệu
                siteid = get_site_id(hospital_site)
                scrid = convert_screening_code_contact(screening_code, siteid)
                initial = row.get("Contact's Initials", '') or row.get("Contact's initials", '') or row.get("Patient's Initials", '') or row.get("Patient's initials", '')
                initial = initial.strip() if initial else ''
                screening_date = parse_date(row.get('Screening Date', ''))
                eligibility = parse_yes_no(row.get('Eligibility', ''))
                recruited = parse_yes_no(row.get('Recruited', ''))
                unrecruited_reason = row.get('Unrecruited Reason', '').strip() or None
                
                # Convert Patient Study ID to USUBJID (remove 43EN prefix)
                patient_usubjid = convert_patient_study_id(patient_study_id_raw)
                
                # Kiểm tra SCR_CASE (Patient) tồn tại
                try:
                    related_patient = SCR_CASE.objects.using(STUDY_DATABASE).get(USUBJID=patient_usubjid)
                except SCR_CASE.DoesNotExist:
                    print(f"⚠️  {scrid}: Patient {patient_usubjid} không tồn tại - Bỏ qua")
                    skipped += 1
                    continue
                
                # Kiểm tra contact đã tồn tại chưa (theo SCRID và SITEID)
                existing = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(SCRID=scrid, SITEID=siteid).first()
                if existing:
                    print(f"⚠️  {scrid} (Site {siteid}): Đã tồn tại - Bỏ qua")
                    skipped += 1
                    continue
                
                # Parse eligibility criteria
                criteria = parse_contact_eligibility_criteria(eligibility, recruited, unrecruited_reason)
                
                is_eligible = eligibility and recruited
                
                # Tạo SUBJID và USUBJID nếu eligible
                subjid = None
                usubjid = None
                
                if is_eligible:
                    # Extract patient number từ patient_usubjid (003-A-001 → 001 or 020-A-001 → 001)
                    patient_parts = patient_usubjid.split('-')
                    patient_number = patient_parts[-1] if len(patient_parts) >= 3 else '001'
                    
                    # Track key
                    track_key = (siteid, patient_number)
                    
                    if track_key not in used_subjids:
                        # Lấy từ database
                        base_subjid = get_next_contact_subjid(siteid, patient_number)
                        used_subjids[track_key] = int(base_subjid.split('-')[-1])
                    else:
                        used_subjids[track_key] += 1
                    
                    subjid = f"B-{patient_number}-{used_subjids[track_key]}"
                    usubjid = f"{siteid}-{subjid}"  # 003-B-001-1 or 020-B-001-1
                
                # Tạo instance
                contact_screening = SCR_CONTACT(
                    SCRID=scrid,
                    STUDYID=STUDYID,
                    SITEID=siteid,
                    INITIAL=initial,
                    SCREENINGFORMDATE=screening_date,
                    SUBJIDENROLLSTUDY=related_patient,
                    SUBJID=subjid,
                    USUBJID=usubjid,
                    
                    # Eligibility criteria
                    LIVEIN5DAYS3MTHS=criteria['LIVEIN5DAYS3MTHS'],
                    MEALCAREONCEDAY=criteria['MEALCAREONCEDAY'],
                    CONSENTTOSTUDY=criteria['CONSENTTOSTUDY'],
                    
                    # Status
                    is_confirmed=is_eligible,
                    UNRECRUITED_REASON=criteria['UNRECRUITED_REASON'],
                )
                
                # Lưu vào database
                contact_screening.save(using=STUDY_DATABASE)
                
                success += 1
                status = "✅" if is_eligible else "⭕"
                usubjid_display = usubjid or 'N/A'
                print(f"{status} {scrid} | Site: {siteid} | Patient: {patient_usubjid} | "
                      f"Initial: {initial} | Eligible: {eligibility} | "
                      f"Recruited: {recruited} | USUBJID: {usubjid_display}")
                
            except Exception as e:
                error += 1
                print(f"❌ Dòng {total} ({screening_code}): Lỗi - {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Kết quả tổng hợp
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ IMPORT CONTACT SCREENING")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Thành công:       {success}")
    print(f"  ⚠️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*80}\n")
    
    # Thống kê theo site
    print("📊 THỐNG KÊ THEO SITE:")
    for site_name, site_id in SITE_MAPPING.items():
        total_site = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(SITEID=site_id).count()
        confirmed_site = SCR_CONTACT.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id, is_confirmed=True
        ).count()
        
        # Get SCRID range
        first_scrid = (
            SCR_CONTACT.objects.using(STUDY_DATABASE)
            .filter(SITEID=site_id)
            .order_by('SCRID')
            .first()
        )
        last_scrid = (
            SCR_CONTACT.objects.using(STUDY_DATABASE)
            .filter(SITEID=site_id)
            .order_by('-SCRID')
            .first()
        )
        
        scrid_range = 'N/A'
        if first_scrid and last_scrid:
            if first_scrid.SCRID == last_scrid.SCRID:
                scrid_range = first_scrid.SCRID
            else:
                scrid_range = f"{first_scrid.SCRID} - {last_scrid.SCRID}"
        
        print(f"   {site_name} (Site {site_id}): {total_site} contacts "
              f"({confirmed_site} recruited) | SCRID: {scrid_range}")
    
    print()
    
    if error > 0:
        print("⚠️  Có lỗi xảy ra. Vui lòng kiểm tra log.")
    elif success > 0:
        print("🎉 Import hoàn tất!")
    else:
        print("ℹ️  Không có dữ liệu mới.")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print(f"\n📂 Project root: {project_root}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(script_dir, "Book1.csv"),
        os.path.join(project_root, "Book1.csv"),
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
    print("SCRIPT IMPORT DỮ LIỆU CONTACT SCREENING - HỖ TRỢ 3 SITE")
    print("="*80)
    print(f"📁 CSV File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Schema: data")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print(f"\n📋 ELIGIBILITY CRITERIA:")
    print(f"   1. LIVEIN5DAYS3MTHS - Lived together ≥5 days in last 3 months")
    print(f"   2. MEALCAREONCEDAY - Shared meals/care ≥1 time per day")
    print(f"   3. CONSENTTOSTUDY - Consent to participate")
    print(f"\n📋 UNRECRUITED REASONS MAPPING:")
    print(f"   1. Age < 18 years → UNRECRUITED_REASON")
    print(f"   2. DO NOT live in same household → LIVEIN5DAYS3MTHS = False")
    print(f"   3. DO NOT share meals/care → MEALCAREONCEDAY = False")
    print(f"\n🔑 FORMAT:")
    print(f"   - SCRID: CS-{{SITEID}}-{{NUMBER}}")
    print(f"   - USUBJID: {{SITEID}}-{{SUBJID}} (XÓA 43EN prefix)")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_contact_csv_to_db(csv_file)
    else:
        print("\n❌ Đã hủy import.")