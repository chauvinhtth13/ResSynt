"""
Script Import Dữ Liệu Screening từ CSV vào Database

Target Database: db_study_43en
Target Schema: data
Table: SCR_CASE

Site Mapping:
- HTD → 003
- CRH → 011

Logic:
- Eligibility=YES và Recruited=YES → is_confirmed=True, tạo SUBJID và USUBJID
- Khác → is_confirmed=False, không tạo SUBJID/USUBJID
"""

import os
import sys
import csv
import re
from datetime import datetime

# ==========================================
# SETUP DJANGO ENVIRONMENT
# ==========================================

# Xác định project root (thư mục chứa manage.py)
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(script_path)

# Nếu script nằm trong subfolder, tìm project root
while not os.path.exists(os.path.join(project_root, 'manage.py')):
    parent = os.path.dirname(project_root)
    if parent == project_root:  # Đã đến root của filesystem
        # Fallback: giả sử script nằm trong project root
        project_root = os.path.dirname(script_path)
        break
    project_root = parent

# Thêm project root vào sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load .env file TRƯỚC KHI import Django settings
try:
    import environ
    env = environ.Env()
    
    # Tìm và load .env file
    env_file = os.path.join(project_root, '.env')
    if os.path.exists(env_file):
        environ.Env.read_env(env_file)
        print(f"✅ Loaded .env from: {env_file}")
    else:
        print(f"⚠️  .env file not found at: {env_file}")
        print("   Đảm bảo các biến môi trường đã được set.")
except ImportError:
    print("⚠️  django-environ not installed. Using os.environ directly.")

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
import django
django.setup()

# Import model sau khi setup Django
from backends.studies.study_43en.models.patient import SCR_CASE

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'
STUDYID = 'KLEB-NET'  # Điều chỉnh theo study của bạn

# Mapping site code
SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """
    Parse date string từ CSV
    Formats hỗ trợ: 
    - 3-Jul-24, 03-Jul-24
    - 6-Jan-26
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Format: D-Mon-YY hoặc DD-Mon-YY
    formats = [
        '%d-%b-%y',   # 3-Jul-24
        '%d-%b-%Y',   # 3-Jul-2024
        '%Y-%m-%d',   # 2024-07-03
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
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
    return SITE_MAPPING.get(site, site)


def convert_screening_code(code, siteid):
    """
    Convert PS0001 → PS-003-0001
    
    Args:
        code: Screening code từ CSV (eg. PS0001)
        siteid: Site ID (eg. 003)
    
    Returns:
        str: Formatted SCRID (eg. PS-003-0001)
    """
    if not code:
        return None
    
    code = code.strip()
    
    # Nếu đã có format PS-XXX-XXXX thì giữ nguyên
    if re.match(r'PS-\d{3}-\d{4}', code):
        return code
    
    # Extract số từ PS0001 → 0001
    match = re.match(r'PS(\d+)', code, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        return f"PS-{siteid}-{number:04d}"
    
    return code


def get_next_subjid(siteid):
    """
    Lấy SUBJID tiếp theo cho site
    Format: A-001, A-002, ...
    """
    last_case = (
        SCR_CASE.objects
        .using(STUDY_DATABASE)
        .filter(SITEID=siteid)
        .exclude(SUBJID__isnull=True)
        .exclude(SUBJID__exact='')
        .filter(SUBJID__startswith='A-')
        .order_by('-SUBJID')
        .first()
    )
    
    if last_case and last_case.SUBJID:
        try:
            last_number = int(last_case.SUBJID.split('-')[-1])
            return f"A-{last_number + 1:03d}"
        except (ValueError, IndexError):
            pass
    
    return "A-001"


def parse_eligibility_criteria(eligibility, recruited, unrecruited_reason):
    """
    Parse eligibility criteria từ CSV và map sang các trường boolean trong model.
    
    Mapping lý do không tuyển:
    - "1. The patient with a positive for K. pneumoniae culture recovered without treatment"
      → KPNISOUNTREATEDSTABLE = True (Exclusion criteria - phải là False để eligible)
    
    - "2. Infection onset after 48 hours of hospitalization"
      → INFPRIOR2OR48HRSADMIT = False
    
    - "3. Age <16 years"
      → UPPER16AGE = False
    
    - Các lý do khác → Lưu vào UNRECRUITED_REASON, các trường khác giữ mặc định
    
    Returns:
        dict: Các trường eligibility criteria
    """
    # Mặc định cho trường hợp đủ điều kiện (Eligibility=YES và Recruited=YES)
    criteria = {
        'UPPER16AGE': True,                          # Age ≥16 years
        'INFPRIOR2OR48HRSADMIT': True,              # Infection prior to or within 48h
        'ISOLATEDKPNFROMINFECTIONORBLOOD': True,    # KPN isolated (luôn True khi import)
        'KPNISOUNTREATEDSTABLE': False,             # KPN untreated and stable (Exclusion - phải False)
        'CONSENTTOSTUDY': True,                      # Consent to participate
        'UNRECRUITED_REASON': None,
    }
    
    is_eligible = eligibility and recruited
    
    if is_eligible:
        # Đủ điều kiện → giữ nguyên mặc định
        return criteria
    
    # Không đủ điều kiện → phân tích lý do
    reason = (unrecruited_reason or '').strip().lower()
    
    # Reason 1: KPN recovered without treatment → Exclusion criteria
    if '1.' in reason or 'recovered without treatment' in reason or 'untreated' in reason:
        criteria['KPNISOUNTREATEDSTABLE'] = True  # Exclusion = True → không đủ điều kiện
        criteria['CONSENTTOSTUDY'] = False
    
    # Reason 2: Infection onset after 48 hours
    elif '2.' in reason or 'after 48 hours' in reason or 'after 48h' in reason:
        criteria['INFPRIOR2OR48HRSADMIT'] = False
        criteria['CONSENTTOSTUDY'] = False
    
    # Reason 3: Age <16
    elif '3.' in reason or 'age <16' in reason or 'age < 16' in reason:
        criteria['UPPER16AGE'] = False
        criteria['CONSENTTOSTUDY'] = False
    
    # Các lý do khác
    else:
        # Không match với các lý do cụ thể → lưu vào UNRECRUITED_REASON
        # Set CONSENTTOSTUDY = False để đánh dấu không tuyển
        criteria['CONSENTTOSTUDY'] = False
    
    # Lưu lý do gốc
    criteria['UNRECRUITED_REASON'] = unrecruited_reason if unrecruited_reason else None
    
    return criteria


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_csv_to_db(csv_file):
    """Import screening data từ CSV vào database"""
    
    total = 0
    success = 0
    error = 0
    skipped = 0
    
    print(f"\n{'='*70}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU SCREENING")
    print(f"{'='*70}")
    print(f"📁 File CSV: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Schema: data")
    print(f"📋 Study ID: {STUDYID}")
    print(f"{'='*70}\n")
    
    # Đọc CSV
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # In header để debug
        print(f"📋 Các cột trong CSV: {reader.fieldnames}\n")
        
        for row in reader:
            total += 1
            
            # Bỏ qua dòng header phụ (dòng 2 trong CSV)
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
            
            try:
                # Parse dữ liệu
                siteid = get_site_id(hospital_site)
                scrid = convert_screening_code(screening_code, siteid)
                initial = row.get("Patient's Initials", '').strip()
                screening_date = parse_date(row.get('Screening Date', ''))
                eligibility = parse_yes_no(row.get('Eligibility', ''))
                recruited = parse_yes_no(row.get('Recruited', ''))
                unrecruited_reason = row.get('Unrecruited Reason', '').strip() or None
                
                # Kiểm tra record đã tồn tại chưa
                existing = SCR_CASE.objects.using(STUDY_DATABASE).filter(SCRID=scrid).first()
                if existing:
                    print(f"⚠️  {scrid}: Đã tồn tại - Bỏ qua")
                    skipped += 1
                    continue
                
                # Parse eligibility criteria từ CSV
                criteria = parse_eligibility_criteria(eligibility, recruited, unrecruited_reason)
                
                # Xác định is_eligible
                is_eligible = eligibility and recruited
                
                # Tạo instance
                screening_case = SCR_CASE(
                    SCRID=scrid,
                    STUDYID=STUDYID,
                    SITEID=siteid,
                    INITIAL=initial,
                    SCREENINGFORMDATE=screening_date,
                    
                    # Eligibility criteria - sử dụng giá trị từ parse_eligibility_criteria
                    UPPER16AGE=criteria['UPPER16AGE'],
                    INFPRIOR2OR48HRSADMIT=criteria['INFPRIOR2OR48HRSADMIT'],
                    ISOLATEDKPNFROMINFECTIONORBLOOD=criteria['ISOLATEDKPNFROMINFECTIONORBLOOD'],
                    KPNISOUNTREATEDSTABLE=criteria['KPNISOUNTREATEDSTABLE'],  # Sửa tên trường đúng
                    CONSENTTOSTUDY=criteria['CONSENTTOSTUDY'],
                    
                    # Status
                    is_confirmed=is_eligible,
                    UNRECRUITED_REASON=criteria['UNRECRUITED_REASON'],
                )
                
                # Nếu eligible, tạo SUBJID và USUBJID
                if is_eligible:
                    screening_case.SUBJID = get_next_subjid(siteid)
                    screening_case.USUBJID = f"{siteid}-{screening_case.SUBJID}"
                
                # Lưu vào database
                # Bypass model save() để tránh auto-generate logic
                screening_case.save(using=STUDY_DATABASE)
                
                success += 1
                status = "✅" if is_eligible else "⭕"
                usubjid_display = screening_case.USUBJID or 'N/A'
                print(f"{status} {scrid} | Site: {siteid} | Initial: {initial} | "
                      f"Date: {screening_date} | Eligible: {eligibility} | "
                      f"Recruited: {recruited} | USUBJID: {usubjid_display}")
                
            except Exception as e:
                error += 1
                print(f"❌ Dòng {total} ({screening_code}): Lỗi - {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Kết quả tổng hợp
    print(f"\n{'='*70}")
    print(f"KẾT QUẢ IMPORT")
    print(f"{'='*70}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Thành công:       {success}")
    print(f"  ⚠️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*70}\n")
    
    # Thống kê theo site
    print("📊 THỐNG KÊ THEO SITE:")
    for site_name, site_id in SITE_MAPPING.items():
        total_site = SCR_CASE.objects.using(STUDY_DATABASE).filter(SITEID=site_id).count()
        confirmed_site = SCR_CASE.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id, is_confirmed=True
        ).count()
        print(f"   {site_name} (Site {site_id}): {total_site} cases ({confirmed_site} recruited)")
    
    print()
    
    if error > 0:
        print("⚠️  Có lỗi xảy ra. Vui lòng kiểm tra log bên trên.")
    elif success > 0:
        print("🎉 Import hoàn tất thành công!")
    else:
        print("ℹ️  Không có dữ liệu mới để import.")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print(f"\n📂 Project root: {project_root}")
    
    # Xác định đường dẫn file CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Thử tìm file CSV
    possible_paths = [
        os.path.join(script_dir, "Book1.csv"),
        os.path.join(project_root, "Book1.csv"),
        os.path.join(project_root, "data_import", "Book1.csv"),
        os.path.join(script_dir, "Sheet_1.csv"),
    ]
    
    csv_file = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    # Nếu không tìm thấy, cho phép nhập đường dẫn
    if not csv_file:
        print("\n❌ Không tìm thấy file CSV tự động.")
        print("📁 Đã tìm trong các đường dẫn:")
        for p in possible_paths:
            print(f"   - {p}")
        
        csv_file = input("\n📁 Nhập đường dẫn file CSV: ").strip()
        
        if not os.path.exists(csv_file):
            print(f"\n❌ File không tồn tại: {csv_file}")
            sys.exit(1)
    
    # Hiển thị thông tin
    print("\n" + "="*70)
    print("SCRIPT IMPORT DỮ LIỆU SCREENING")
    print("="*70)
    print(f"📁 CSV File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Schema: data")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print("="*70)
    
    # Xác nhận trước khi import
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_csv_to_db(csv_file)
    else:
        print("\n❌ Đã hủy import.")