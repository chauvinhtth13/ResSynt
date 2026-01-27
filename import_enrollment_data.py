"""
Script Import Dữ Liệu Enrollment và các CRF liên quan

Target Database: db_study_43en
Target Schema: data

Import vào các bảng:
- ENR_CASE (Enrollment)
- PERSONAL_DATA (PII - tên, phone, địa chỉ)
- CLI_CASE (Clinical - admission date)
- DISCH_CASE (Discharge - discharge date)

Mapping:
- Hospital site: HTD → 003, CRH → 011
- Study ID: 43EN-003-A-001 → 003-A-001 (bỏ 43EN-)
- Ward: Match với danh sách ward có sẵn
- Address: Parse tự động vào các trường old address
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

# Import models sau khi setup Django
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.models.patient import ENR_CASE
from backends.studies.study_43en.models.patient.PER_DATA import PERSONAL_DATA
from backends.studies.study_43en.models.patient import CLI_CASE
from backends.studies.study_43en.models.patient import DISCH_CASE

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'
STUDYID = '43EN'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
}

# Ward mapping - normalize ward names
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
        'NHIỄM VIỆT – ANH': 'Nhiễm Việt – Anh',
        'NOI A': 'Nội A',
        'NỘI A': 'Nội A',
        'NOI B': 'Nội B',
        'NỘI B': 'Nội B',
        'CAP CUU': 'Cấp cứu',
        'CẤP CỨU': 'Cấp cứu',
        'HSCC': 'Hồi sức tích cực – Chống độc Người lớn',
        'HOI SUC': 'Hồi sức tích cực – Chống độc Người lớn',
        'HỒI SỨC': 'Hồi sức tích cực – Chống độc Người lớn',
        'ICU': 'Hồi sức tích cực – Chống độc Người lớn',
    },
    '011': {
        # 4B1: Ngoại Tiêu Hóa
        '4B1': '4B1: Ngoại Tiêu Hóa',
        '4B1 NGOAI TIEU HOA': '4B1: Ngoại Tiêu Hóa',
        '4B1: NGOẠI TIÊU HÓA': '4B1: Ngoại Tiêu Hóa',
        'NGOAI TIEU HOA': '4B1: Ngoại Tiêu Hóa',
        'NGOẠI TIÊU HÓA': '4B1: Ngoại Tiêu Hóa',
        
        # 4B3: Ngoại Gan - Mật - Tụy
        '4B3': '4B3: Ngoại Gan - Mật - Tụy',
        '4B3 NGOAI GAN MAT TUY': '4B3: Ngoại Gan - Mật - Tụy',
        '4B3: NGOẠI GAN MẬT TỤY': '4B3: Ngoại Gan - Mật - Tụy',
        'NGOAI GAN MAT TUY': '4B3: Ngoại Gan - Mật - Tụy',
        'NGOẠI GAN MẬT TỤY': '4B3: Ngoại Gan - Mật - Tụy',
        'NGOẠI GAN - MẬT - TỤY': '4B3: Ngoại Gan - Mật - Tụy',
        
        # 5B1: Ngoại Tiết Niệu
        '5B1': '5B1: Ngoại Tiết Niệu',
        '5B1 NGOAI TIET NIEU': '5B1: Ngoại Tiết Niệu',
        '5B1: NGOẠI TIẾT NIỆU': '5B1: Ngoại Tiết Niệu',
        'NGOAI TIET NIEU': '5B1: Ngoại Tiết Niệu',
        'NGOẠI TIẾT NIỆU': '5B1: Ngoại Tiết Niệu',
        
        # 6B1: Tai Mũi Họng
        '6B1': '6B1: Tai Mũi Họng',
        '6B1 TAI MUI HONG': '6B1: Tai Mũi Họng',
        '6B1: TAI MŨI HỌNG': '6B1: Tai Mũi Họng',
        'TAI MUI HONG': '6B1: Tai Mũi Họng',
        'TAI MŨI HỌNG': '6B1: Tai Mũi Họng',
        
        # 8B1: Nội Phổi
        '8B1': '8B1: Nội Phổi',
        '8B1 NOI PHOI': '8B1: Nội Phổi',
        '8B1: NỘI PHỔI': '8B1: Nội Phổi',
        'NOI PHOI': '8B1: Nội Phổi',
        'NỘI PHỔI': '8B1: Nội Phổi',
        
        # 8B3: Nội Tiêu Hóa
        '8B3': '8B3: Nội Tiêu Hóa',
        '8B3 NOI TIEU HOA': '8B3: Nội Tiêu Hóa',
        '8B3: NỘI TIÊU HÓA': '8B3: Nội Tiêu Hóa',
        'NOI TIEU HOA': '8B3: Nội Tiêu Hóa',
        'NỘI TIÊU HÓA': '8B3: Nội Tiêu Hóa',
        
        # Bệnh Nhiệt Đới
        'BENH NHIET DOI': 'Bệnh Nhiệt Đới',
        'BỆNH NHIỆT ĐỚI': 'Bệnh Nhiệt Đới',
        'BND': 'Bệnh Nhiệt Đới',
        
        # Nội Tiết
        'NOI TIET': 'Nội Tiết',
        'NỘI TIẾT': 'Nội Tiết',
    }
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """
    Parse date string từ CSV
    Formats: Wed 03-Jul-2024, 01-Jan-1974, 02-Jul-2024, 14-Oct-25, 01-Jan-46
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Remove day name prefix (Wed, Thu, etc.)
    date_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', date_str, flags=re.IGNORECASE)
    
    formats = [
        '%d-%b-%Y',   # 03-Jul-2024
        '%d-%b-%y',   # 03-Jul-24, 14-Oct-25
        '%d/%m/%Y',   # 03/07/2024
        '%d/%m/%y',   # 03/07/24
        '%Y-%m-%d',   # 2024-07-03
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            
            # Xử lý năm 2 chữ số: 
            # - Năm 00-30 → 2000-2030 (admission/discharge dates)
            # - Năm 31-99 → 1931-1999 (birth dates for older patients)
            # Nhưng datetime đã tự xử lý: 00-68 → 2000-2068, 69-99 → 1969-1999
            # Ta cần điều chỉnh cho DOB: nếu năm > 2025 thì trừ 100
            if fmt == '%d-%b-%y' and parsed.year > 2025:
                # Likely a birth year like 46 → 1946, not 2046
                parsed = parsed.replace(year=parsed.year - 100)
            
            return parsed.date()
        except ValueError:
            continue
    
    print(f"    ⚠️  Không parse được date: '{date_str}'")
    return None


def parse_dob(dob_str):
    """
    Parse date of birth và trả về (day, month, year)
    Xử lý đặc biệt cho năm 2 chữ số:
    - 46 → 1946 (không phải 2046)
    - 74 → 1974
    - 81 → 1981
    """
    if not dob_str or not dob_str.strip():
        return None, None, None
    
    dob_str = dob_str.strip()
    
    # Remove day name prefix if any
    dob_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', dob_str, flags=re.IGNORECASE)
    
    formats = [
        '%d-%b-%Y',   # 01-Jan-1974
        '%d-%b-%y',   # 01-Jan-74, 7-Mar-74
        '%d/%m/%Y',   # 01/01/1974
        '%d/%m/%y',   # 01/01/74
        '%Y-%m-%d',   # 1974-01-01
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(dob_str, fmt)
            year = parsed.year
            
            # Xử lý năm 2 chữ số cho DOB:
            # Nếu năm > năm hiện tại, đó là năm của thế kỷ trước
            current_year = datetime.now().year
            if year > current_year:
                year = year - 100
            
            # Validation: tuổi phải hợp lý (16-120)
            age = current_year - year
            if age < 0 or age > 120:
                print(f"    ⚠️  Năm sinh không hợp lệ: {year} (tuổi: {age})")
                continue
            
            return parsed.day, parsed.month, year
        except ValueError:
            continue
    
    print(f"    ⚠️  Không parse được DOB: '{dob_str}'")
    return None, None, None


def get_site_id(hospital_site):
    """Map hospital site to SITEID"""
    site = hospital_site.strip().upper()
    return SITE_MAPPING.get(site, site)


def get_current_max_subjid_number(siteid):
    """
    Lấy số thứ tự lớn nhất hiện tại của SUBJID cho site
    Returns: int (0 nếu chưa có record nào)
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
            return int(last_case.SUBJID.split('-')[-1])
        except (ValueError, IndexError):
            pass
            
    return 0


def normalize_ward(ward_str, siteid):
    """
    Normalize ward name to match database values
    """
    if not ward_str:
        return None
    
    ward_upper = ward_str.strip().upper()
    ward_upper = re.sub(r'[–-]', ' ', ward_upper)  # Replace dashes
    ward_upper = re.sub(r'\s+', ' ', ward_upper)   # Normalize spaces
    
    site_wards = WARD_MAPPING.get(siteid, {})
    
    # Try exact match first
    if ward_upper in site_wards:
        return site_wards[ward_upper]
    
    # Try partial match
    for key, value in site_wards.items():
        if key in ward_upper or ward_upper in key:
            return value
    
    # Return original if no match
    return ward_str.strip()


def convert_study_id_to_usubjid(study_id):
    """
    Convert Study ID to USUBJID
    43EN-003-A-001 → 003-A-001
    """
    if not study_id:
        return None
    
    study_id = study_id.strip()
    
    # Remove 43EN- prefix
    if study_id.startswith('43EN-'):
        return study_id[5:]  # Remove first 5 characters
    
    return study_id


def parse_gender(gender_str):
    """Convert gender string to model choice"""
    if not gender_str:
        return None
    
    gender = gender_str.strip().lower()
    if gender in ['male', 'nam', 'm']:
        return 'Male'
    elif gender in ['female', 'nữ', 'nu', 'f']:
        return 'Female'
    return 'Other'


def parse_phone(phone_str):
    """
    Parse phone numbers, có thể có 2 số cách nhau bằng dấu ","
    """
    if not phone_str or not phone_str.strip():
        return None
    
    # Normalize: giữ nguyên format, chỉ strip
    return phone_str.strip()


def parse_address(address_str):
    """
    Parse địa chỉ vào các trường old address
    
    Logic:
    - Bắt đầu bằng "thành phố" hoặc "Tp" → PROVINCECITY
    - Bắt đầu bằng "quận" hoặc "huyện" → DISTRICT
    - Bắt đầu bằng "phường" hoặc "xã" → WARD
    - Có số → HOUSE_NUMBER
    - Còn lại → STREET
    
    Returns:
        dict với các key: HOUSE_NUMBER, STREET, WARD, DISTRICT, PROVINCECITY
    """
    result = {
        'HOUSE_NUMBER': None,
        'STREET': None,
        'WARD': None,
        'DISTRICT': None,
        'PROVINCECITY': None,
    }
    
    if not address_str or not address_str.strip():
        return result
    
    # Normalize address: remove newlines, extra spaces
    address = address_str.replace('\n', ', ').replace('\r', '')
    address = re.sub(r',\s*,', ',', address)  # Remove double commas
    address = re.sub(r'\s+', ' ', address).strip()
    
    # Split by comma
    parts = [p.strip() for p in address.split(',') if p.strip()]
    
    remaining_parts = []
    
    for part in parts:
        part_lower = part.lower().strip()
        
        # Check for city/province
        if any(x in part_lower for x in ['thành phố', 'tp.', 'tphcm', 'hcm', 'tp ', 'tỉnh']):
            result['PROVINCECITY'] = part
        
        # Check for district
        elif any(x in part_lower for x in ['quận', 'huyện', 'thị xã']):
            result['DISTRICT'] = part
        
        # Check for ward
        elif any(x in part_lower for x in ['phường', 'xã', 'thị trấn', 'khóm', 'khu phố', 'ấp']):
            # Nếu đã có ward, ghép vào
            if result['WARD']:
                result['WARD'] = f"{result['WARD']}, {part}"
            else:
                result['WARD'] = part
        
        else:
            remaining_parts.append(part)
    
    # Process remaining parts
    for part in remaining_parts:
        # Check if part has numbers (likely house number/address)
        if re.search(r'\d', part):
            # Check if it looks like a street address with number
            if any(x in part.lower() for x in ['đường', 'street', 'phố']):
                # Has both number and street indicator
                if result['HOUSE_NUMBER']:
                    result['STREET'] = part
                else:
                    result['HOUSE_NUMBER'] = part
            elif result['HOUSE_NUMBER'] is None:
                result['HOUSE_NUMBER'] = part
            elif result['STREET'] is None:
                result['STREET'] = part
        else:
            # No numbers - likely street name
            if result['STREET'] is None:
                result['STREET'] = part
            elif result['HOUSE_NUMBER'] is None:
                result['HOUSE_NUMBER'] = part
    
    return result


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_csv_to_db(csv_file):
    """Import enrollment data từ CSV vào database"""
    
    total = 0
    success = 0
    error = 0
    skipped = 0
    # Track SUBJID counter per site for this import session
    subjid_counters = {}
    
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU ENROLLMENT VÀ CÁC CRF LIÊN QUAN")
    print(f"{'='*80}")
    print(f"📁 File CSV: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"{'='*80}\n")
    
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        print(f"📋 Các cột trong CSV: {reader.fieldnames}\n")
        
        for row in reader:
            total += 1
            
            study_id_raw = row.get('Study ID', '').strip()
            if not study_id_raw or study_id_raw.lower() == 'study id':
                print(f"⏭️  Dòng {total}: Bỏ qua - Header hoặc dòng trống")
                skipped += 1
                continue
            
            try:
                # Parse basic info
                hospital_site = row.get('Hospital site', '').strip()
                siteid = get_site_id(hospital_site)
                usubjid = convert_study_id_to_usubjid(study_id_raw)

                if not usubjid:
                    print(f"⚠️  Dòng {total}: Không có Study ID hợp lệ")
                    skipped += 1
                    continue

                # Check if SCR_CASE exists
                try:
                    scr_case = SCR_CASE.objects.using(STUDY_DATABASE).get(USUBJID=usubjid)
                except SCR_CASE.DoesNotExist:
                    # Nếu không tìm thấy SCR_CASE, thử tạo SUBJID/USUBJID theo logic đánh số lại cho từng site
                    
                    # Initialize counter from DB if not in session
                    if siteid not in subjid_counters:
                         subjid_counters[siteid] = get_current_max_subjid_number(siteid)

                    # Increment
                    subjid_counters[siteid] += 1
                    subjid_number = subjid_counters[siteid]
                    
                    new_subjid = f"A-{subjid_number:03d}"
                    new_usubjid = f"{siteid}-{new_subjid}"
                    # Thử tìm lại SCR_CASE với USUBJID mới
                    try:
                        scr_case = SCR_CASE.objects.using(STUDY_DATABASE).get(USUBJID=new_usubjid)
                        usubjid = new_usubjid
                    except SCR_CASE.DoesNotExist:
                        print(f"⚠️  {usubjid}: SCR_CASE không tồn tại - Bỏ qua (đã thử mapping sang {new_usubjid})")
                        skipped += 1
                        continue

                # Parse dates
                icf_date = parse_date(row.get('ICF Date', ''))
                admission_date = parse_date(row.get('Admission Date', ''))
                discharge_date = parse_date(row.get('Discharge Date', ''))

                # Parse DOB
                day_of_birth, month_of_birth, year_of_birth = parse_dob(row.get('DoB', ''))

                # Parse other fields
                gender = parse_gender(row.get('Gender', ''))
                ward = normalize_ward(row.get('Ward', ''), siteid)
                patient_name = row.get("Patient's Name", '').strip() or None
                phone = parse_phone(row.get('Phone No.', ''))
                patient_id = row.get('Patient ID', '').strip() or None  # MEDRECORDID
                address_parts = parse_address(row.get('Address', ''))

                # ==========================================
                # 1. CREATE/UPDATE ENR_CASE
                # ==========================================
                enr_case, enr_created = ENR_CASE.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=scr_case,
                    defaults={
                        'ENRDATE': icf_date,
                        'RECRUITDEPT': ward,
                        'DAYOFBIRTH': day_of_birth,
                        'MONTHOFBIRTH': month_of_birth,
                        'YEAROFBIRTH': year_of_birth,
                        'SEX': gender,
                    }
                )

                if not enr_created:
                    # Update existing
                    updated = False
                    if icf_date and not enr_case.ENRDATE:
                        enr_case.ENRDATE = icf_date
                        updated = True
                    if ward and not enr_case.RECRUITDEPT:
                        enr_case.RECRUITDEPT = ward
                        updated = True
                    if day_of_birth and not enr_case.DAYOFBIRTH:
                        enr_case.DAYOFBIRTH = day_of_birth
                        enr_case.MONTHOFBIRTH = month_of_birth
                        enr_case.YEAROFBIRTH = year_of_birth
                        updated = True
                    if gender and not enr_case.SEX:
                        enr_case.SEX = gender
                        updated = True

                    if updated:
                        enr_case.save(using=STUDY_DATABASE)

                # ==========================================
                # 2. CREATE/UPDATE PERSONAL_DATA (PII)
                # ==========================================
                personal_data, pd_created = PERSONAL_DATA.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_case,
                    defaults={
                        'FULLNAME': patient_name,
                        'PHONE': phone,
                        'MEDRECORDID': patient_id,
                        'HOUSE_NUMBER': address_parts['HOUSE_NUMBER'],
                        'STREET': address_parts['STREET'],
                        'WARD': address_parts['WARD'],
                        'DISTRICT': address_parts['DISTRICT'],
                        'PROVINCECITY': address_parts['PROVINCECITY'],
                        'PRIMARY_ADDRESS': 'old',  # Sử dụng old address
                    }
                )

                if not pd_created:
                    # Update existing if fields are empty
                    updated = False
                    if patient_name and not personal_data.FULLNAME:
                        personal_data.FULLNAME = patient_name
                        updated = True
                    if phone and not personal_data.PHONE:
                        personal_data.PHONE = phone
                        updated = True
                    if patient_id and not personal_data.MEDRECORDID:
                        personal_data.MEDRECORDID = patient_id
                        updated = True
                    if address_parts['HOUSE_NUMBER'] and not personal_data.HOUSE_NUMBER:
                        personal_data.HOUSE_NUMBER = address_parts['HOUSE_NUMBER']
                        updated = True
                    if address_parts['STREET'] and not personal_data.STREET:
                        personal_data.STREET = address_parts['STREET']
                        updated = True
                    if address_parts['WARD'] and not personal_data.WARD:
                        personal_data.WARD = address_parts['WARD']
                        updated = True
                    if address_parts['DISTRICT'] and not personal_data.DISTRICT:
                        personal_data.DISTRICT = address_parts['DISTRICT']
                        updated = True
                    if address_parts['PROVINCECITY'] and not personal_data.PROVINCECITY:
                        personal_data.PROVINCECITY = address_parts['PROVINCECITY']
                        updated = True

                    if updated:
                        personal_data.PRIMARY_ADDRESS = 'old'
                        personal_data.save(using=STUDY_DATABASE)

                # ==========================================
                # 3. CREATE/UPDATE CLI_CASE (Clinical)
                # ==========================================
                if admission_date:
                    cli_case, cli_created = CLI_CASE.objects.using(STUDY_DATABASE).get_or_create(
                        USUBJID=enr_case,
                        defaults={
                            'ADMISDATE': admission_date,
                            'ADMISDEPT': ward,
                        }
                    )

                    if not cli_created:
                        if admission_date and not cli_case.ADMISDATE:
                            cli_case.ADMISDATE = admission_date
                            cli_case.save(using=STUDY_DATABASE)

                # ==========================================
                # 4. CREATE/UPDATE DISCH_CASE (Discharge)
                # ==========================================
                if discharge_date:
                    disch_case, disch_created = DISCH_CASE.objects.using(STUDY_DATABASE).get_or_create(
                        USUBJID=enr_case,
                        defaults={
                            'DISCHDATE': discharge_date,
                            'STUDYID': STUDYID,
                            'SITEID': siteid,
                            'SUBJID': scr_case.SUBJID,
                            'INITIAL': scr_case.INITIAL,
                        }
                    )

                    if not disch_created:
                        if discharge_date and not disch_case.DISCHDATE:
                            disch_case.DISCHDATE = discharge_date
                            disch_case.save(using=STUDY_DATABASE)

                success += 1
                enr_status = "🆕" if enr_created else "📝"
                print(f"{enr_status} {usubjid} | Site: {siteid} | Ward: {ward} | "
                      f"ICF: {icf_date} | Adm: {admission_date} | Disch: {discharge_date}")

            except Exception as e:
                error += 1
                print(f"❌ Dòng {total} ({study_id_raw}): Lỗi - {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Kết quả tổng hợp
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ IMPORT")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Thành công:       {success}")
    print(f"  ⚠️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*80}\n")
    
    # Thống kê
    print("📊 THỐNG KÊ:")
    for site_name, site_id in SITE_MAPPING.items():
        enr_count = ENR_CASE.objects.using(STUDY_DATABASE).filter(
            USUBJID__SITEID=site_id
        ).count()
        print(f"   {site_name} (Site {site_id}): {enr_count} enrollments")
    
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
        os.path.join(project_root, "data_import", "Book1.csv"),
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
    print("SCRIPT IMPORT DỮ LIỆU ENROLLMENT")
    print("="*80)
    print(f"📁 CSV File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 IMPORT VÀO CÁC BẢNG:")
    print(f"   - ENR_CASE (Enrollment)")
    print(f"   - PERSONAL_DATA (PII: Tên, SĐT, Địa chỉ)")
    print(f"   - CLI_CASE (Clinical: Admission Date)")
    print(f"   - DISCH_CASE (Discharge: Discharge Date)")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_csv_to_db(csv_file)
    else:
        print("\n❌ Đã hủy import.")