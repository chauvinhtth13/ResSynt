"""
Script Import Dữ Liệu Contact Enrollment từ CSV/ODS vào Database

Target Database: db_study_43en
Target Schema: data

Import vào các bảng:
- ENR_CONTACT (Enrollment)
- PERSONAL_CONTACT_DATA (PII - tên, phone, địa chỉ)

Mapping:
- Hospital site: HTD → 003, CRH → 011
- Contact Study ID: 43EN-003-B-001-1 → 003-B-001-1 (bỏ 43EN-)
- Ward: Match với danh sách ward có sẵn

Lưu ý USUBJID của Contact:
- Format: 003-B-001-1
- Trong đó: 003 = SITEID, B-001-1 = SUBJID
- B-001-1 nghĩa là Contact thứ 1 của Patient A-001
- B-001-2 nghĩa là Contact thứ 2 của Patient A-001 (cùng 1 bệnh nhân có 2 người thân)
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
from backends.studies.study_43en.models.contact import SCR_CONTACT
from backends.studies.study_43en.models.contact import ENR_CONTACT
from backends.studies.study_43en.models.contact.PER_CONTACT_DATA import PERSONAL_CONTACT_DATA

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'
STUDYID = 'KLEB-NET'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
}

# Ward mapping
WARD_MAPPING = {
    '003': {
        'NHIEM A': 'Nhiễm A',
        'NHIỄM A': 'Nhiễm A',
        'NHIEM B': 'Nhiễm B',
        'NHIỄM B': 'Nhiễm B',
        'NHIEM C': 'Nhiễm C',
        'NHIỄM C': 'Nhiễm C',
        'NHIEM D': 'Nhiễm D',
        'NHIỄM D': 'Nhiễm D',
        'NHIEM E': 'Nhiễm E',
        'NHIỄM E': 'Nhiễm E',
        'NHIEM VIET ANH': 'Nhiễm Việt – Anh',
        'NHIỄM VIỆT ANH': 'Nhiễm Việt – Anh',
        'NOI A': 'Nội A',
        'NỘI A': 'Nội A',
        'NOI B': 'Nội B',
        'NỘI B': 'Nội B',
        'CAP CUU': 'Cấp cứu',
        'CẤP CỨU': 'Cấp cứu',
        'HSCC': 'Hồi sức tích cực – Chống độc Người lớn',
        'ICU': 'Hồi sức tích cực – Chống độc Người lớn',
    },
    '011': {
        '4B1': '4B1: Ngoại Tiêu Hóa',
        '4B3': '4B3: Ngoại Gan - Mật - Tụy',
        '5B1': '5B1: Ngoại Tiết Niệu',
        '6B1': '6B1: Tai Mũi Họng',
        '8B1': '8B1: Nội Phổi',
        '8B3': '8B3: Nội Tiêu Hóa',
        'BENH NHIET DOI': 'Bệnh Nhiệt Đới',
        'BỆNH NHIỆT ĐỚI': 'Bệnh Nhiệt Đới',
        'NOI TIET': 'Nội Tiết',
        'NỘI TIẾT': 'Nội Tiết',
    }
}

# Relationship mapping (Vietnamese to standardized)
RELATIONSHIP_MAPPING = {
    'vợ': 'Spouse',
    'vo': 'Spouse',
    'chồng': 'Spouse',
    'chong': 'Spouse',
    'con gái': 'Child',
    'con gai': 'Child',
    'con gái ruột': 'Child',
    'con gai ruot': 'Child',
    'con trai': 'Child',
    'con': 'Child',
    'cha': 'Parent',
    'mẹ': 'Parent',
    'me': 'Parent',
    'bố': 'Parent',
    'bo': 'Parent',
    'anh': 'Sibling',
    'chị': 'Sibling',
    'chi': 'Sibling',
    'em': 'Sibling',
    'cháu': 'Grandchild',
    'chau': 'Grandchild',
    'ông': 'Grandparent',
    'ong': 'Grandparent',
    'bà': 'Grandparent',
    'ba': 'Grandparent',
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """Parse date string từ CSV/ODS"""
    if not date_str or str(date_str).strip() in ['', 'nan', 'NaT', 'None']:
        return None
    
    date_str = str(date_str).strip()
    
    # Remove day name prefix
    date_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', date_str, flags=re.IGNORECASE)
    
    # Handle pandas Timestamp format (2024-07-03 00:00:00)
    if ' 00:00:00' in date_str:
        date_str = date_str.replace(' 00:00:00', '')
    
    formats = [
        '%Y-%m-%d',   # 2024-07-03
        '%d-%b-%Y',   # 03-Jul-2024
        '%d-%b-%y',   # 03-Jul-24
        '%d/%m/%Y',   # 03/07/2024
        '%d/%m/%y',   # 03/07/24
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


def parse_dob(dob_str):
    """Parse date of birth và trả về (day, month, year)"""
    if not dob_str or str(dob_str).strip() in ['', 'nan', 'NaT', 'None']:
        return None, None, None
    
    dob_str = str(dob_str).strip()
    
    # Remove time part
    if ' 00:00:00' in dob_str:
        dob_str = dob_str.replace(' 00:00:00', '')
    
    # Remove day name prefix
    dob_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', dob_str, flags=re.IGNORECASE)
    
    formats = [
        '%Y-%m-%d',   # 2024-07-03
        '%d-%b-%Y',   # 01-Jan-1974
        '%d-%b-%y',   # 01-Jan-74
        '%d/%m/%Y',   # 01/01/1974
        '%d/%m/%y',   # 01/01/74
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(dob_str, fmt)
            year = parsed.year
            
            current_year = datetime.now().year
            if year > current_year:
                year = year - 100
            
            return parsed.day, parsed.month, year
        except ValueError:
            continue
    
    print(f"    ⚠️  Không parse được DOB: '{dob_str}'")
    return None, None, None


def get_site_id(hospital_site):
    """Map hospital site to SITEID"""
    if not hospital_site or str(hospital_site).strip() in ['', 'nan']:
        return None
    site = str(hospital_site).strip().upper()
    return SITE_MAPPING.get(site, site)


def normalize_ward(ward_str, siteid):
    """Normalize ward name"""
    if not ward_str or str(ward_str).strip() in ['', 'nan']:
        return None
    
    ward_upper = str(ward_str).strip().upper()
    ward_upper = re.sub(r'[–-]', ' ', ward_upper)
    ward_upper = re.sub(r'\s+', ' ', ward_upper)
    
    site_wards = WARD_MAPPING.get(siteid, {})
    
    if ward_upper in site_wards:
        return site_wards[ward_upper]
    
    for key, value in site_wards.items():
        if key in ward_upper or ward_upper in key:
            return value
    
    return ward_str.strip()


def convert_contact_study_id(study_id):
    """
    Convert Contact Study ID to USUBJID
    43EN-003-B-001-1 → 003-B-001-1
    """
    if not study_id or str(study_id).strip() in ['', 'nan']:
        return None
    
    study_id = str(study_id).strip()
    
    if study_id.startswith('43EN-'):
        return study_id[5:]
    
    return study_id


def parse_gender(gender_str):
    """Convert gender string to model choice"""
    if not gender_str or str(gender_str).strip() in ['', 'nan']:
        return None
    
    gender = str(gender_str).strip().lower()
    if gender in ['male', 'nam', 'm']:
        return 'Male'
    elif gender in ['female', 'nữ', 'nu', 'f']:
        return 'Female'
    return None


def normalize_relationship(rel_str):
    """Normalize relationship to standardized value"""
    if not rel_str or str(rel_str).strip() in ['', 'nan']:
        return None
    
    rel_lower = str(rel_str).strip().lower()
    
    # Try exact match first
    if rel_lower in RELATIONSHIP_MAPPING:
        return RELATIONSHIP_MAPPING[rel_lower]
    
    # Try partial match
    for key, value in RELATIONSHIP_MAPPING.items():
        if key in rel_lower:
            return value
    
    # Return original if no match
    return rel_str.strip()


def parse_phone(phone_str):
    """Parse phone numbers"""
    if not phone_str or str(phone_str).strip() in ['', 'nan']:
        return None
    return str(phone_str).strip()


def parse_address(address_str):
    """Parse địa chỉ vào các trường old address"""
    result = {
        'HOUSE_NUMBER': None,
        'STREET': None,
        'WARD': None,
        'DISTRICT': None,
        'PROVINCECITY': None,
    }
    
    if not address_str or str(address_str).strip() in ['', 'nan']:
        return result
    
    address = str(address_str).replace('\n', ', ').replace('\r', '')
    address = re.sub(r',\s*,', ',', address)
    address = re.sub(r'\s+', ' ', address).strip()
    
    parts = [p.strip() for p in address.split(',') if p.strip()]
    
    remaining_parts = []
    
    for part in parts:
        part_lower = part.lower().strip()
        
        if any(x in part_lower for x in ['thành phố', 'tp.', 'tphcm', 'hcm', 'tp ', 'tỉnh']):
            result['PROVINCECITY'] = part
        elif any(x in part_lower for x in ['quận', 'huyện', 'thị xã']):
            result['DISTRICT'] = part
        elif any(x in part_lower for x in ['phường', 'xã', 'thị trấn', 'khóm', 'khu phố', 'ấp']):
            if result['WARD']:
                result['WARD'] = f"{result['WARD']}, {part}"
            else:
                result['WARD'] = part
        else:
            remaining_parts.append(part)
    
    for part in remaining_parts:
        if re.search(r'\d', part):
            if any(x in part.lower() for x in ['đường', 'street', 'phố']):
                if result['HOUSE_NUMBER']:
                    result['STREET'] = part
                else:
                    result['HOUSE_NUMBER'] = part
            elif result['HOUSE_NUMBER'] is None:
                result['HOUSE_NUMBER'] = part
            elif result['STREET'] is None:
                result['STREET'] = part
        else:
            if result['STREET'] is None:
                result['STREET'] = part
            elif result['HOUSE_NUMBER'] is None:
                result['HOUSE_NUMBER'] = part
    
    return result


def is_valid_row(row):
    """Check if row has valid data"""
    contact_id = row.get('Contact Study ID', '')
    if not contact_id or str(contact_id).strip() in ['', 'nan', 'NaN']:
        return False
    
    # Skip header rows
    if '43EN-003-B-_ _ _' in str(contact_id) or 'DD-MMM-YYYY' in str(contact_id):
        return False
    
    return True


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_contact_enrollment(file_path):
    """Import contact enrollment data từ CSV/ODS vào database"""
    
    import pandas as pd
    
    # Đọc file
    if file_path.endswith('.ods'):
        df = pd.read_excel(file_path, engine='odf')
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    total = 0
    success = 0
    error = 0
    skipped = 0
    
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU CONTACT ENROLLMENT")
    print(f"{'='*80}")
    print(f"📁 File: {file_path}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Số dòng trong file: {len(df)}")
    print(f"📋 Các cột: {df.columns.tolist()}")
    print(f"{'='*80}\n")
    
    # Process each row
    for idx, row in df.iterrows():
        total += 1
        
        # Convert row to dict
        row_dict = row.to_dict()
        
        # Check valid row
        if not is_valid_row(row_dict):
            hospital_site = row_dict.get('Hospital site', '')
            if str(hospital_site).strip() not in ['', 'nan', 'Địa điểm NC']:
                print(f"⏭️  Dòng {total}: Bỏ qua - Không có Contact Study ID")
            skipped += 1
            continue
        
        contact_study_id_raw = str(row_dict.get('Contact Study ID', '')).strip()
        
        try:
            # Parse data
            hospital_site = row_dict.get('Hospital site', '')
            siteid = get_site_id(hospital_site)
            
            if not siteid:
                print(f"⚠️  Dòng {total}: Không có Site ID hợp lệ")
                skipped += 1
                continue
            
            usubjid = convert_contact_study_id(contact_study_id_raw)
            
            if not usubjid:
                print(f"⚠️  Dòng {total}: Không có Contact Study ID hợp lệ")
                skipped += 1
                continue
            
            # Check if SCR_CONTACT exists
            try:
                scr_contact = SCR_CONTACT.objects.using(STUDY_DATABASE).get(USUBJID=usubjid)
            except SCR_CONTACT.DoesNotExist:
                print(f"⚠️  {usubjid}: SCR_CONTACT không tồn tại - Bỏ qua")
                skipped += 1
                continue
            
            # Parse other fields
            icf_date = parse_date(row_dict.get('ICF Date', ''))
            ward = normalize_ward(row_dict.get('Ward', ''), siteid)
            contact_name = row_dict.get("Close Contact's Name", '')
            contact_name = str(contact_name).strip() if contact_name and str(contact_name) != 'nan' else None
            relationship = normalize_relationship(row_dict.get('Relationship', ''))
            day_of_birth, month_of_birth, year_of_birth = parse_dob(row_dict.get('DoB', ''))
            gender = parse_gender(row_dict.get('Gender', ''))
            phone = parse_phone(row_dict.get('Phone No.', ''))
            # Note: Contact không lưu địa chỉ vào PERSONAL_CONTACT_DATA
            # (model chỉ có FULLNAME và PHONE)
            
            # ==========================================
            # 1. CREATE/UPDATE ENR_CONTACT
            # ==========================================
            enr_contact, enr_created = ENR_CONTACT.objects.using(STUDY_DATABASE).get_or_create(
                USUBJID=scr_contact,
                defaults={
                    'ENRDATE': icf_date,
                    'RELATIONSHIP': relationship,
                    'DAYOFBIRTH': day_of_birth,
                    'MONTHOFBIRTH': month_of_birth,
                    'YEAROFBIRTH': year_of_birth,
                    'SEX': gender,
                }
            )
            
            if not enr_created:
                updated = False
                if icf_date and not enr_contact.ENRDATE:
                    enr_contact.ENRDATE = icf_date
                    updated = True
                if relationship and not enr_contact.RELATIONSHIP:
                    enr_contact.RELATIONSHIP = relationship
                    updated = True
                if day_of_birth and not enr_contact.DAYOFBIRTH:
                    enr_contact.DAYOFBIRTH = day_of_birth
                    enr_contact.MONTHOFBIRTH = month_of_birth
                    enr_contact.YEAROFBIRTH = year_of_birth
                    updated = True
                if gender and not enr_contact.SEX:
                    enr_contact.SEX = gender
                    updated = True
                
                if updated:
                    enr_contact.save(using=STUDY_DATABASE)
            
            # ==========================================
            # 2. CREATE/UPDATE PERSONAL_CONTACT_DATA (PII)
            # Note: PERSONAL_CONTACT_DATA chỉ có FULLNAME và PHONE
            # Không có các trường địa chỉ như PERSONAL_DATA
            # ==========================================
            personal_data, pd_created = PERSONAL_CONTACT_DATA.objects.using(STUDY_DATABASE).get_or_create(
                USUBJID=enr_contact,
                defaults={
                    'FULLNAME': contact_name,
                    'PHONE': phone,
                }
            )
            
            if not pd_created:
                updated = False
                if contact_name and not personal_data.FULLNAME:
                    personal_data.FULLNAME = contact_name
                    updated = True
                if phone and not personal_data.PHONE:
                    personal_data.PHONE = phone
                    updated = True
                
                if updated:
                    personal_data.save(using=STUDY_DATABASE)
            
            success += 1
            enr_status = "🆕" if enr_created else "📝"
            print(f"{enr_status} {usubjid} | Site: {siteid} | Relationship: {relationship} | "
                  f"Gender: {gender} | ICF: {icf_date}")
            
        except Exception as e:
            error += 1
            print(f"❌ Dòng {total} ({contact_study_id_raw}): Lỗi - {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Kết quả tổng hợp
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ IMPORT CONTACT ENROLLMENT")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Thành công:       {success}")
    print(f"  ⚠️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*80}\n")
    
    # Thống kê
    print("📊 THỐNG KÊ:")
    for site_name, site_id in SITE_MAPPING.items():
        enr_count = ENR_CONTACT.objects.using(STUDY_DATABASE).filter(
            USUBJID__SITEID=site_id
        ).count()
        print(f"   {site_name} (Site {site_id}): {enr_count} contact enrollments")
    
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
        os.path.join(script_dir, "Book4.csv"),
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
    print("SCRIPT IMPORT DỮ LIỆU CONTACT ENROLLMENT")
    print("="*80)
    print(f"📁 File: {file_path}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 IMPORT VÀO CÁC BẢNG:")
    print(f"   - ENR_CONTACT (Contact Enrollment)")
    print(f"   - PERSONAL_CONTACT_DATA (PII: Tên, SĐT, Địa chỉ)")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print(f"\n📋 USUBJID FORMAT:")
    print(f"   003-B-001-1 = Contact thứ 1 của Patient A-001 tại Site 003")
    print(f"   003-B-001-2 = Contact thứ 2 của Patient A-001 tại Site 003")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_contact_enrollment(file_path)
    else:
        print("\n❌ Đã hủy import.")