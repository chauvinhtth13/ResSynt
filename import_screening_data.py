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

from backends.studies.study_43en.models.patient import SCR_CASE

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
    'NHTD': '020',  # ← ADDED
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """Parse date: 3-Jul-24, 13-Oct-25, 6-Nov-25"""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    formats = ['%d-%b-%y', '%d-%b-%Y', '%Y-%m-%d']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def parse_yes_no(value):
    """Convert YES/Yes/yes/NO/No/no to boolean"""
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


def parse_study_id(study_id_str):
    """
    Parse Study ID và XÓA prefix 43EN
    
    Input examples:
    - 43EN-003-A-001 → USUBJID: 003-A-001
    - 43EN-020-A-001 → USUBJID: 020-A-001  ← ADDED
    - 43DN-011-A-012 → USUBJID: 011-A-012 (fix typo)
    - 003-A-001      → USUBJID: 003-A-001
    - 020-A-001      → USUBJID: 020-A-001  ← ADDED
    
    Returns: (studyid, siteid, subjid, usubjid)
    """
    if not study_id_str or not study_id_str.strip():
        return None, None, None, None
    
    study_id_str = study_id_str.strip()
    
    # Pattern 1: 43EN-003-A-001 (with study prefix)
    match = re.match(r'(\w+)-(\d{3})-(A-\d{3})', study_id_str)
    if match:
        studyid = match.group(1)  # 43EN or 43DN
        siteid = match.group(2)   # 003, 011, 020
        subjid = match.group(3)   # A-001
        
        # Fix typo 43DN → 43EN
        if studyid == '43DN':
            print(f"    ⚠️  Fixed typo: 43DN → 43EN in {study_id_str}")
            studyid = '43EN'
        
        # CRITICAL: USUBJID = SITEID-SUBJID (XÓA 43EN prefix)
        usubjid = f"{siteid}-{subjid}"  # 003-A-001 or 020-A-001 (NOT 43EN-...)
        
        return studyid, siteid, subjid, usubjid
    
    # Pattern 2: 003-A-001 (already without prefix)
    match2 = re.match(r'(\d{3})-(A-\d{3})', study_id_str)
    if match2:
        siteid = match2.group(1)  # 003, 011, 020
        subjid = match2.group(2)  # A-001
        usubjid = study_id_str    # 003-A-001 or 020-A-001
        studyid = '43EN'
        
        return studyid, siteid, subjid, usubjid
    
    return None, None, None, None


def parse_eligibility_criteria(eligibility, recruited, unrecruited_reason):
    """Parse eligibility criteria"""
    criteria = {
        'UPPER16AGE': True,
        'INFPRIOR2OR48HRSADMIT': True,
        'ISOLATEDKPNFROMINFECTIONORBLOOD': True,
        'KPNISOUNTREATEDSTABLE': False,
        'CONSENTTOSTUDY': True,
        'UNRECRUITED_REASON': None,
    }
    
    is_eligible = eligibility and recruited
    
    if is_eligible:
        return criteria
    
    reason = (unrecruited_reason or '').strip().lower()
    
    if '1.' in reason or 'recovered without treatment' in reason or 'untreated' in reason:
        criteria['KPNISOUNTREATEDSTABLE'] = True
        criteria['CONSENTTOSTUDY'] = False
    elif '2.' in reason or 'after 48 hours' in reason or 'after 48h' in reason:
        criteria['INFPRIOR2OR48HRSADMIT'] = False
        criteria['CONSENTTOSTUDY'] = False
    elif '3.' in reason or 'age <16' in reason or 'age < 16' in reason:
        criteria['UPPER16AGE'] = False
        criteria['CONSENTTOSTUDY'] = False
    elif 'not able to get informed consent' in reason or 'does not want to participate' in reason:
        criteria['CONSENTTOSTUDY'] = False
    else:
        criteria['CONSENTTOSTUDY'] = False
    
    criteria['UNRECRUITED_REASON'] = unrecruited_reason if unrecruited_reason else None
    
    return criteria


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_csv_to_db(csv_file):
    """Import screening data - OPTIMIZED VERSION"""
    
    total = 0
    success = 0
    error = 0
    skipped = 0
    
    print(f"\n{'='*70}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU SCREENING - PHIÊN BẢN HOÀN CHỈNH")
    print(f"{'='*70}")
    print(f"📁 File CSV: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📋 Study ID: 43EN")
    print(f"\n🔑 FORMAT:")
    print(f"   - SCRID: PS-{{SITEID}}-{{NUMBER}} (e.g., PS-003-0001, PS-020-0001)")
    print(f"   - USUBJID: {{SITEID}}-{{SUBJID}} (e.g., 003-A-001, 020-A-001, KHÔNG CÓ 43EN)")
    print(f"{'='*70}\n")
    
    # Load existing SCRIDs to memory (OPTIMIZATION)
    print("🔍 Đang load dữ liệu hiện có từ database...")
    existing_scrids = set(
        SCR_CASE.objects.using(STUDY_DATABASE)
        .values_list('SCRID', 'SITEID')
    )
    print(f"✅ Loaded {len(existing_scrids)} existing records\n")
    
    # Batch data collection
    records_to_create = []
    
    # Read CSV
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        print(f"📋 Các cột: {reader.fieldnames}\n")
        
        for row in reader:
            total += 1
            
            # Skip header rows
            hospital_site = row.get('Hospital site', '').strip()
            if not hospital_site or hospital_site.startswith('Địa điểm'):
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
                
                # CRITICAL: SCRID = PS-{SITEID}-{NUMBER} để unique toàn database
                # HTD/PS0001 → PS-003-0001
                # CRH/PS0001 → PS-011-0001
                # NHTD/PS0001 → PS-020-0001  ← WORKS NOW
                screening_code_number = screening_code.replace('PS', '').strip()
                # Pad với zeros nếu cần (PS0001 → 0001, PS1 → 0001)
                if screening_code_number.isdigit():
                    screening_code_number = screening_code_number.zfill(4)
                scrid = f"PS-{siteid}-{screening_code_number}"
                
                initial = row.get("Patient's initials", row.get("Patient's Initials", '')).strip()
                screening_date = parse_date(row.get('Screening Date', ''))
                eligibility = parse_yes_no(row.get('Eligibility', ''))
                recruited = parse_yes_no(row.get('Recruited', ''))
                unrecruited_reason = row.get('Unrecruited Reason', '').strip() or None
                study_id_str = row.get('Study ID', '').strip()
                
                # Check if already exists (FAST in-memory lookup)
                if (scrid, siteid) in existing_scrids:
                    print(f"⏭️  {scrid} (Site {siteid}): Đã tồn tại - Bỏ qua")
                    skipped += 1
                    continue
                
                # Parse Study ID - XÓA 43EN prefix
                studyid_from_csv, siteid_from_csv, subjid_from_csv, usubjid_from_csv = parse_study_id(study_id_str)
                
                # Validate Study ID vs Hospital Site
                if usubjid_from_csv and siteid_from_csv and siteid_from_csv != siteid:
                    print(f"⚠️  Dòng {total}: SITEID không khớp - Study ID: {siteid_from_csv} vs Hospital: {siteid}")
                
                # Parse eligibility criteria
                criteria = parse_eligibility_criteria(eligibility, recruited, unrecruited_reason)
                is_eligible = eligibility and recruited
                
                # Create instance
                screening_case = SCR_CASE(
                    SCRID=scrid,
                    STUDYID='43EN',
                    SITEID=siteid,
                    INITIAL=initial,
                    SCREENINGFORMDATE=screening_date,
                    
                    # Eligibility criteria
                    UPPER16AGE=criteria['UPPER16AGE'],
                    INFPRIOR2OR48HRSADMIT=criteria['INFPRIOR2OR48HRSADMIT'],
                    ISOLATEDKPNFROMINFECTIONORBLOOD=criteria['ISOLATEDKPNFROMINFECTIONORBLOOD'],
                    KPNISOUNTREATEDSTABLE=criteria['KPNISOUNTREATEDSTABLE'],
                    CONSENTTOSTUDY=criteria['CONSENTTOSTUDY'],
                    
                    # Status
                    is_confirmed=is_eligible,
                    UNRECRUITED_REASON=criteria['UNRECRUITED_REASON'],
                )
                
                # Set Study ID if eligible (USUBJID đã xóa 43EN prefix)
                if is_eligible and usubjid_from_csv:
                    screening_case.SUBJID = subjid_from_csv
                    screening_case.USUBJID = usubjid_from_csv  # 003-A-001 or 020-A-001 (NOT 43EN-...)
                
                # Add to batch
                records_to_create.append(screening_case)
                
                # Mark as processed
                existing_scrids.add((scrid, siteid))
                
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
    
    # Bulk create (OPTIMIZATION)
    if records_to_create:
        print(f"\n💾 Đang lưu {len(records_to_create)} records vào database...")
        try:
            SCR_CASE.objects.using(STUDY_DATABASE).bulk_create(
                records_to_create,
                batch_size=100
            )
            success = len(records_to_create)
            print(f"✅ Đã lưu thành công {success} records!")
        except Exception as e:
            print(f"❌ Lỗi khi bulk create: {str(e)}")
            # Fallback: Save individually
            print("🔄 Đang lưu từng record...")
            success = 0
            for record in records_to_create:
                try:
                    record.save(using=STUDY_DATABASE)
                    success += 1
                except Exception as save_error:
                    error += 1
                    print(f"❌ Lỗi lưu {record.SCRID}: {str(save_error)}")
    
    # Results
    print(f"\n{'='*70}")
    print(f"KẾT QUẢ IMPORT")
    print(f"{'='*70}")
    print(f"  📊 Tổng số dòng:     {total}")
    print(f"  ✅ Thành công:       {success}")
    print(f"  ⚠️  Bỏ qua:          {skipped}")
    print(f"  ❌ Lỗi:              {error}")
    print(f"{'='*70}\n")
    
    # Statistics by site
    print("📊 THỐNG KÊ THEO SITE:")
    for site_name, site_id in SITE_MAPPING.items():
        total_site = SCR_CASE.objects.using(STUDY_DATABASE).filter(SITEID=site_id).count()
        confirmed_site = SCR_CASE.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id, is_confirmed=True
        ).count()
        
        # Get SCRID range
        first_scrid = (
            SCR_CASE.objects.using(STUDY_DATABASE)
            .filter(SITEID=site_id)
            .order_by('SCRID')
            .first()
        )
        last_scrid = (
            SCR_CASE.objects.using(STUDY_DATABASE)
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
        
        print(f"   {site_name} (Site {site_id}): {total_site} cases "
              f"({confirmed_site} recruited) | SCRID: {scrid_range}")
    
    print()
    
    if error > 0:
        print("⚠️  Có lỗi xảy ra. Vui lòng kiểm tra log.")
    elif success > 0:
        print("🎉 Import hoàn tất thành công!")
    else:
        print("ℹ️  Không có dữ liệu mới để import.")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print(f"\n📂 Project root: {project_root}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try to find CSV file
    possible_paths = [
        os.path.join(script_dir, "Book5.csv"),
        os.path.join(project_root, "Book5.csv"),
        os.path.join(script_dir, "Book1.csv"),
        os.path.join(project_root, "Book1.csv"),
    ]
    
    csv_file = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    if not csv_file:
        print("\n❌ Không tìm thấy file CSV.")
        csv_file = input("\n📁 Nhập đường dẫn file CSV: ").strip()
        
        if not os.path.exists(csv_file):
            print(f"\n❌ File không tồn tại: {csv_file}")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("SCRIPT IMPORT SCREENING - PHIÊN BẢN HOÀN CHỈNH")
    print("="*70)
    print(f"📁 CSV File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 SITE MAPPING:")
    for site_name, site_id in SITE_MAPPING.items():
        print(f"   {site_name} → Site {site_id}")
    print(f"\n⚡ FEATURES:")
    print(f"   - In-memory duplicate check")
    print(f"   - Bulk insert (batch_size=100)")
    print(f"   - SCRID: PS-{{SITEID}}-{{NUMBER}}")
    print(f"   - USUBJID: {{SITEID}}-{{SUBJID}} (XÓA 43EN prefix)")
    print("="*70)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_csv_to_db(csv_file)
    else:
        print("\n❌ Đã hủy import.")