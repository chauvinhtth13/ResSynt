"""
Script Import Đầy Đủ: Sample, Lab, Discharge và Follow-up từ CSV

Target Database: db_study_43en

Import vào các bảng:
- SAM_CASE (Sample Collection - 4 visits V1, V2, V3, V4)
- LAB_Microbiology (Lab Culture Results)
- DISCH_CASE (Discharge info + Death status)
- FU_CASE_28 (Follow-up Day 28)
- FU_CASE_90 (Follow-up Day 90)

Lưu ý quan trọng:
1. 4 visits: V1→Sample1, V2→Sample2, V3→Sample3, V4→Sample4
2. Stool/Rectal → import vào STOOL field
3. Tất cả samples đều KPN+ (Klebsiella positive)
4. Death=YES → update DISCH_CASE.DEATHATDISCH='Yes'
5. Follow-up D28/D90 → tạo FU_CASE_28/FU_CASE_90
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
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.models.patient import ENR_CASE
from backends.studies.study_43en.models.patient import SAM_CASE
from backends.studies.study_43en.models.patient import LAB_Microbiology
from backends.studies.study_43en.models.patient import DISCH_CASE
from backends.studies.study_43en.models.patient import FU_CASE_28
from backends.studies.study_43en.models.patient import FU_CASE_90

# ==========================================
# FIX: Set PostgreSQL search_path to include 'data' schema
# ==========================================
from django.db import connections

def set_search_path():
    """Set PostgreSQL search_path to use 'data' schema for db_study_43en"""
    try:
        # Get connection to the study database
        conn = connections[STUDY_DATABASE]
        with conn.cursor() as cursor:
            cursor.execute("SET search_path TO data, public;")
        print(f"✅ Database '{STUDY_DATABASE}' search_path set to: data, public\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not set search_path: {e}\n")

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'
STUDYID = 'KLEB-NET'

SITE_MAPPING = {
    'HTD': '003',
    'CRH': '011',
}

# Specimen Location Mapping (Vietnamese to Model Choices)
SPECIMEN_MAPPING = {
    # BLOOD
    'máu': 'BLOOD',
    'mau': 'BLOOD',
    'blood': 'BLOOD',
    'cấy máu': 'BLOOD',
    'cay mau': 'BLOOD',
    
    # URINE
    'nước tiểu': 'URINE',
    'nuoc tieu': 'URINE',
    'urine': 'URINE',
    'cấy nước tiểu': 'URINE',
    'cay nuoc tieu': 'URINE',
    
    # SPUTUM
    'đàm': 'SPUTUM',
    'dam': 'SPUTUM',
    'sputum': 'SPUTUM',
    'cấy đàm': 'SPUTUM',
    'cay dam': 'SPUTUM',
    
    # BRONCHIAL (BAL / DMB - Dịch Màng Bụng)
    'bal': 'BRONCHIAL',
    'dmb': 'PERITONEAL_FLUID',  # DMB = Dịch Màng Bụng
    'dịch màng bụng': 'PERITONEAL_FLUID',
    'dich mang bung': 'PERITONEAL_FLUID',
    'cấy dmb': 'PERITONEAL_FLUID',
    'cay dmb': 'PERITONEAL_FLUID',
    'dịch rửa phế quản': 'BRONCHIAL',
    'dich rua phe quan': 'BRONCHIAL',
    'dịch rửa phế quản – phế nang': 'BRONCHIAL',
    'dịch rửa phế quản phế nang': 'BRONCHIAL',
    'bronchial': 'BRONCHIAL',
    'cấy bal': 'BRONCHIAL',
    'cay bal': 'BRONCHIAL',
    
    # CSF (Cerebrospinal Fluid)
    'dịch não tuỷ': 'CSF',
    'dich nao tuy': 'CSF',
    'dịch não tủy': 'CSF',
    'dich nao tuy': 'CSF',
    'csf': 'CSF',
    'cấy dịch não tuỷ': 'CSF',
    'cay dich nao tuy': 'CSF',
    
    # PERITONEAL_FLUID
    'dịch ổ bụng': 'PERITONEAL_FLUID',
    'dich o bung': 'PERITONEAL_FLUID',
    'dịch dẫn lưu ổ bụng': 'PERITONEAL_FLUID',
    'dich dan luu o bung': 'PERITONEAL_FLUID',
    'dịch mật ổ bụng': 'PERITONEAL_FLUID',
    'dich mat o bung': 'PERITONEAL_FLUID',
    'dịch tụy': 'PERITONEAL_FLUID',
    'dich tuy': 'PERITONEAL_FLUID',
    'peritoneal': 'PERITONEAL_FLUID',
    'cấy dịch ổ bụng': 'PERITONEAL_FLUID',
    'cay dich o bung': 'PERITONEAL_FLUID',
    
    # PLEURAL_FLUID
    'dịch màng phổi': 'PLEURAL_FLUID',
    'dich mang phoi': 'PLEURAL_FLUID',
    'pleural': 'PLEURAL_FLUID',
    'cấy dịch màng phổi': 'PLEURAL_FLUID',
    'cay dich mang phoi': 'PLEURAL_FLUID',
    
    # WOUND
    'mủ': 'WOUND',
    'mu': 'WOUND',
    'mủ vết thương': 'WOUND',
    'mu vet thuong': 'WOUND',
    'mủ áp xe gan': 'WOUND',
    'mu ap xe gan': 'WOUND',
    'dịch vết thương': 'WOUND',
    'dich vet thuong': 'WOUND',
    'wound': 'WOUND',
    'pus': 'WOUND',
    'cấy mủ': 'WOUND',
    'cay mu': 'WOUND',
    
    # Drainage fluids → OTHER
    'dịch dẫn lưu': 'OTHER',
    'dich dan luu': 'OTHER',
    'dịch mật': 'OTHER',
    'dich mat': 'OTHER',
    'cấy dịch': 'OTHER',
    'cay dich': 'OTHER',
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_date(date_str):
    """Parse date string từ CSV"""
    if not date_str or str(date_str).strip() in ['', 'nan', 'NaT', 'None']:
        return None
    
    date_str = str(date_str).strip()
    date_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+', '', date_str, flags=re.IGNORECASE)
    
    if ' 00:00:00' in date_str:
        date_str = date_str.replace(' 00:00:00', '')
    
    formats = [
        '%Y-%m-%d',
        '%d-%b-%Y',
        '%d-%b-%y',
        '%d/%m/%Y',
        '%d/%m/%y',
        '%m/%d/%Y',
        '%m/%d/%y',
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if fmt in ['%d-%b-%y', '%d/%m/%y', '%m/%d/%y'] and parsed.year > 2025:
                parsed = parsed.replace(year=parsed.year - 100)
            return parsed.date()
        except ValueError:
            continue
    
    print(f"    ⚠️  Không parse được date: '{date_str}'")
    return None


def parse_yes_no(value):
    """Convert YES/NO to boolean"""
    if not value or str(value).strip() in ['', 'nan']:
        return False
    val_upper = str(value).strip().upper()
    return val_upper in ['YES', 'Y', 'TRUE', '1']


def convert_study_id_to_usubjid(study_id):
    """Convert Study ID to USUBJID (43EN-003-A-001 → 003-A-001)"""
    if not study_id or str(study_id).strip() in ['', 'nan']:
        return None
    
    study_id = str(study_id).strip()
    if study_id.startswith('43EN-'):
        return study_id[5:]
    return study_id


def map_specimen_location(specimen_str):
    """
    Map specimen name to SpecimenLocationChoices
    Returns: (choice_value, other_detail)
    """
    if not specimen_str or str(specimen_str).strip() in ['', 'nan']:
        return None, None
    
    specimen_lower = str(specimen_str).strip().lower()
    
    # Try exact match first
    if specimen_lower in SPECIMEN_MAPPING:
        return SPECIMEN_MAPPING[specimen_lower], None
    
    # Try partial match
    for key, value in SPECIMEN_MAPPING.items():
        if key in specimen_lower or specimen_lower in key:
            return value, None
    
    # No match → OTHER
    return 'OTHER', specimen_str.strip()


def parse_multiple_samples(sample_ids_str, culture_types_str, dates_str=None):
    """
    Parse multiple sample IDs, culture types, and dates from single cells
    
    FIXED: Handle newlines in ALL fields (sample IDs, culture types, AND dates)
    
    Args:
        sample_ids_str: "625497 625498 625509" or "626317\n626316\n142967" or single ID
        culture_types_str: "Cấy máu Cấy máu Cấy DMB" or "Cấy máu\nCấy máu\nCấy mủ" or single type
        dates_str: "6/12/2024\n6/12/2024\n8/12/2024" or single date
    
    Returns:
        List of tuples: [(sample_id, specimen_location, other_detail, date), ...]
    
    Example:
        Input: "625497\n625498", "Cấy máu\nCấy nước tiểu", "6/12/2024\n7/12/2024"
        Output: [
            ("625497", "BLOOD", None, date(2024, 12, 6)),
            ("625498", "URINE", None, date(2024, 12, 7))
        ]
    """
    if not sample_ids_str or str(sample_ids_str).strip() in ['', 'nan']:
        return []
    
    # Parse sample IDs - split by BOTH newlines AND whitespace
    sample_ids_raw = str(sample_ids_str).strip()
    sample_ids_raw = sample_ids_raw.replace('\n', ' ').replace('\r', ' ')
    sample_ids = [s.strip() for s in sample_ids_raw.split() if s.strip()]
    
    # Parse culture types - split by newlines first, then by "Cấy" keyword
    culture_types = []
    if culture_types_str and str(culture_types_str).strip() not in ['', 'nan']:
        culture_str = str(culture_types_str).strip()
        
        # First try splitting by newlines
        if '\n' in culture_str:
            culture_types = [t.strip() for t in culture_str.split('\n') if t.strip()]
        else:
            # Split by "Cấy" and keep it
            parts = re.split(r'(Cấy|cấy)', culture_str, flags=re.IGNORECASE)
            current_type = ""
            for part in parts:
                if re.match(r'(Cấy|cấy)', part, re.IGNORECASE):
                    if current_type:
                        culture_types.append(current_type.strip())
                    current_type = part
                else:
                    current_type += part
            if current_type:
                culture_types.append(current_type.strip())
    
    # If no culture types parsed, try simple split
    if not culture_types and culture_types_str:
        culture_str = str(culture_types_str).replace('\n', ' ')
        culture_types = [t.strip() for t in culture_str.split() if t.strip()]
    
    # Parse dates - split by newlines
    dates = []
    if dates_str and str(dates_str).strip() not in ['', 'nan']:
        dates_raw = str(dates_str).strip()
        if '\n' in dates_raw:
            dates = [d.strip() for d in dates_raw.split('\n') if d.strip()]
        else:
            # Single date
            dates = [dates_raw.strip()]
    
    # Match sample IDs with culture types and dates
    results = []
    for i, sample_id in enumerate(sample_ids):
        # Skip empty or invalid sample IDs
        if not sample_id or sample_id in ['nan', '']:
            continue
        
        # Get corresponding culture type (or reuse first if fewer types than IDs)
        if i < len(culture_types):
            culture_type = culture_types[i]
        elif culture_types:
            culture_type = culture_types[0]  # Reuse first type
        else:
            culture_type = "Unknown"
        
        # Get corresponding date (or reuse first if fewer dates than IDs)
        if i < len(dates):
            date_str = dates[i]
        elif dates:
            date_str = dates[0]  # Reuse first date
        else:
            date_str = None
        
        # Parse the date
        sample_date = parse_date(date_str) if date_str else None
        
        # Map to specimen location
        specimen_location, other_detail = map_specimen_location(culture_type)
        
        if specimen_location:
            results.append((sample_id.strip(), specimen_location, other_detail, sample_date))
    
    return results


# ==========================================
# MAIN IMPORT FUNCTION
# ==========================================

def import_complete_data(csv_file):
    """Import đầy đủ Sample, Lab, Discharge và Follow-up từ CSV"""
    
    import pandas as pd
    
    # ⚡ FIX: Set search_path for PostgreSQL to use 'data' schema
    set_search_path()
    
    # Đọc file
    if csv_file.endswith('.xlsx') or csv_file.endswith('.xls'):
        df = pd.read_excel(csv_file)
    elif csv_file.endswith('.ods'):
        df = pd.read_excel(csv_file, engine='odf')
    else:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # Counters
    stats = {
        'total': 0,
        'sam_v1': 0, 'sam_v2': 0, 'sam_v3': 0, 'sam_v4': 0,
        'lab': 0,
        'disch': 0,
        'fu28': 0,
        'fu90': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU IMPORT DỮ LIỆU ĐẦY ĐỦ")
    print(f"{'='*80}")
    print(f"📁 File: {csv_file}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"📊 Số dòng: {len(df)}")
    print(f"📋 Các cột: {df.columns.tolist()}")
    print(f"{'='*80}\n")
    
    for idx, row in df.iterrows():
        stats['total'] += 1
        row_dict = row.to_dict()
        
        # Get Study ID
        study_id_raw = row_dict.get('Study ID', '')
        if not study_id_raw or str(study_id_raw).strip() in ['', 'nan']:
            stats['skipped'] += 1
            continue
        
        # Skip header rows
        if 'DD-MMM-YYYY' in str(study_id_raw) or '43EN-003-A-_' in str(study_id_raw):
            stats['skipped'] += 1
            continue
        
        usubjid = convert_study_id_to_usubjid(study_id_raw)
        
        try:
            # Check ENR_CASE exists
            try:
                enr_case = ENR_CASE.objects.using(STUDY_DATABASE).get(USUBJID__USUBJID=usubjid)
                # Get SITEID directly from ENR_CASE's related SCR_CASE USUBJID field
                siteid = enr_case.USUBJID_id.split('-')[0]  # Extract from "003-A-001" -> "003"
            except ENR_CASE.DoesNotExist:
                print(f"⚠️  {usubjid}: ENR_CASE không tồn tại - Bỏ qua")
                stats['skipped'] += 1
                continue
            
            print(f"\n📋 Processing: {usubjid}")
            
            # ==========================================
            # 1. IMPORT SAM_CASE (4 VISITS)
            # ==========================================
            # Visit mapping: V1→Sample1, V2→Sample2, V3→Sample3, V4→Sample4
            visits = [
                ('1', 'V1', '1'),
                ('2', 'V2', '2'),
                ('3', 'V3', '3'),
                ('4', 'V4', '4'),
            ]
            
            for sample_type, visit_suffix, visit_num in visits:
                # Get sample data for this visit
                throat = parse_yes_no(row_dict.get(f'Throat {visit_suffix}', ''))
                throat_date = parse_date(row_dict.get(f'Throat {visit_suffix} Date', ''))
                
                stool_rectal = parse_yes_no(row_dict.get(f'Stool/Rectal {visit_suffix}', ''))
                stool_date = parse_date(row_dict.get(f'Stool/Rectal {visit_suffix} Date', ''))
                
                blood = parse_yes_no(row_dict.get(f'Blood {visit_suffix}', ''))
                blood_date = parse_date(row_dict.get(f'Blood {visit_suffix} Date', ''))
                
                # Check if any sample collected
                any_sample = throat or stool_rectal or blood
                
                # Always create SAM_CASE record (even if no samples)
                sam_case, created = SAM_CASE.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_case,
                    SAMPLE_TYPE=sample_type,
                    defaults={
                        'SAMPLE': any_sample,
                        'SAMPLE_STATUS': 'collected' if any_sample else 'not_collected',
                        'REASONIFNO': 'Not collected during this visit' if not any_sample else None,
                        
                        # Throat
                        'THROATSWAB': throat,
                        'THROATSWABDATE': throat_date if throat else None,
                        'CULTRES_3': 'Pos' if throat else None,
                        'KLEBPNEU_3': throat,  # All KPN+
                        
                        # Stool (from Stool/Rectal)
                        'STOOL': stool_rectal,
                        'STOOLDATE': stool_date if stool_rectal else None,
                        'CULTRES_1': 'Pos' if stool_rectal else None,
                        'KLEBPNEU_1': stool_rectal,  # All KPN+
                        
                        # Blood
                        'BLOOD': blood,
                        'BLOODDATE': blood_date if blood else None,
                    }
                )
                
                if created:
                    stats[f'sam_v{visit_num}'] += 1
                    status = "✅" if any_sample else "⭕"
                    print(f"  {status} SAM_CASE V{visit_num}: Blood={blood}, Throat={throat}, Stool={stool_rectal}")
            
            # ==========================================
            # 2. IMPORT LAB_Microbiology (Multiple Culture Results)
            # ==========================================
            sample_ids_str = row_dict.get('Sample ID', '')
            culture_types_str = row_dict.get('Culture Sample Type', '')
            kpn_dates_str = row_dict.get('K.pneumoniae Date', '')
            
            # Parse multiple samples (with dates)
            samples = parse_multiple_samples(sample_ids_str, culture_types_str, kpn_dates_str)
            
            if samples:
                for sample_id, specimen_location, other_specimen, sample_date in samples:
                    # Skip if no date
                    if not sample_date:
                        print(f"    ⚠️  {sample_id}: Không có ngày, bỏ qua")
                        continue
                    
                    # Check if already exists
                    existing_lab = LAB_Microbiology.objects.using(STUDY_DATABASE).filter(
                        USUBJID=enr_case,
                        SPECIMENID=sample_id,
                        SPECSAMPLOC=specimen_location
                    ).first()
                    
                    if not existing_lab:
                        lab_case = LAB_Microbiology(
                            USUBJID=enr_case,
                            STUDYID=STUDYID,
                            SITEID=siteid,
                            SUBJID=usubjid.split('-')[1] if '-' in usubjid else usubjid,
                            INITIAL=usubjid.split('-')[2] if usubjid.count('-') >= 2 else None,
                            
                            SPECIMENID=sample_id,
                            SPECSAMPLOC=specimen_location,
                            OTHERSPECIMEN=other_specimen,
                            SPECSAMPDATE=sample_date,  # Use individual sample date
                            
                            # All Positive and KPN
                            RESULT='Positive',
                            RESULTDETAILS='Klebsiella pneumoniae',
                            IFPOSITIVE='Kpneumoniae',
                            IS_KLEBSIELLA=True,
                        )
                        lab_case.save(using=STUDY_DATABASE)
                        stats['lab'] += 1
                        print(f"  🔬 LAB_CASE: {sample_id} - {specimen_location}")
            
            # ==========================================
            # 3. UPDATE DISCH_CASE (Death Status)
            # ==========================================
            death_status = parse_yes_no(row_dict.get('Death', ''))
            
            if death_status:
                disch_case, disch_created = DISCH_CASE.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_case,
                    defaults={
                        'STUDYID': STUDYID,
                        'SITEID': siteid,
                        'SUBJID': usubjid.split('-')[1] if '-' in usubjid else usubjid,  # Extract "A" from "003-A-001"
                        'INITIAL': usubjid.split('-')[2] if usubjid.count('-') >= 2 else None,  # Extract "001"
                        'DEATHATDISCH': 'Yes',
                        'DISCHSTATUS': 'Died',
                        'DEATHCAUSE': 'Sepsis due to Klebsiella pneumoniae (imported from CSV)',
                    }
                )
                
                # Update if already exists
                if not disch_created:
                    if disch_case.DEATHATDISCH != 'Yes':
                        disch_case.DEATHATDISCH = 'Yes'
                        disch_case.DISCHSTATUS = 'Died'
                        if not disch_case.DEATHCAUSE:
                            disch_case.DEATHCAUSE = 'Sepsis due to Klebsiella pneumoniae (imported from CSV)'
                        disch_case.save(using=STUDY_DATABASE)
                
                stats['disch'] += 1
                print(f"  💀 DISCH_CASE updated with death status")
            
            # ==========================================
            # 4. IMPORT FU_CASE_28 (Follow-up Day 28)
            # ==========================================
            fu28_assessed = parse_yes_no(row_dict.get('Follow-up D28', ''))
            fu28_date = parse_date(row_dict.get('D28 Real Date', ''))
            
            if fu28_assessed and fu28_date:
                # Determine outcome based on death status
                if death_status:
                    outcome = 'Deceased'
                    dead = 'Yes'
                else:
                    outcome = 'Alive'
                    dead = 'No'
                
                fu28, fu28_created = FU_CASE_28.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_case,
                    defaults={
                        'EvaluatedAtDay28': 'Yes',
                        'EvaluateDate': fu28_date,
                        'Outcome28Days': outcome,
                        'Dead': dead,
                        'DeathDate': fu28_date if death_status else None,
                        'DeathReason': 'Sepsis due to Klebsiella pneumoniae' if death_status else None,
                    }
                )
                
                # Update if already exists
                if not fu28_created:
                    fu28.EvaluatedAtDay28 = 'Yes'
                    fu28.EvaluateDate = fu28_date
                    fu28.Outcome28Days = outcome
                    fu28.Dead = dead
                    if death_status:
                        fu28.DeathDate = fu28_date
                        fu28.DeathReason = 'Sepsis due to Klebsiella pneumoniae'
                    fu28.save(using=STUDY_DATABASE)
                
                stats['fu28'] += 1
                print(f"  📅 FU_CASE_28 created/updated")
            
            # ==========================================
            # 5. IMPORT FU_CASE_90 (Follow-up Day 90)
            # ==========================================
            fu90_assessed = parse_yes_no(row_dict.get('Follow-up D90', ''))
            fu90_date = parse_date(row_dict.get('D90 Real Date', ''))
            
            if fu90_assessed and fu90_date:
                # Determine outcome based on death status
                if death_status:
                    outcome = 'Deceased'
                    dead = 'Yes'
                else:
                    outcome = 'Alive'
                    dead = 'No'
                
                fu90, fu90_created = FU_CASE_90.objects.using(STUDY_DATABASE).get_or_create(
                    USUBJID=enr_case,
                    defaults={
                        'EvaluatedAtDay90': 'Yes',
                        'EvaluateDate': fu90_date,
                        'Outcome90Days': outcome,
                        'Dead': dead,
                        'DeathDate': fu90_date if death_status else None,
                        'DeathReason': 'Sepsis due to Klebsiella pneumoniae' if death_status else None,
                    }
                )
                
                # Update if already exists
                if not fu90_created:
                    fu90.EvaluatedAtDay90 = 'Yes'
                    fu90.EvaluateDate = fu90_date
                    fu90.Outcome90Days = outcome
                    fu90.Dead = dead
                    if death_status:
                        fu90.DeathDate = fu90_date
                        fu90.DeathReason = 'Sepsis due to Klebsiella pneumoniae'
                    fu90.save(using=STUDY_DATABASE)
                
                stats['fu90'] += 1
                print(f"  📅 FU_CASE_90 created/updated")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"❌ Lỗi tại dòng {stats['total']} ({study_id_raw}): {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ==========================================
    # KẾT QUẢ TỔNG HỢP
    # ==========================================
    print(f"\n{'='*80}")
    print(f"KẾT QUẢ IMPORT")
    print(f"{'='*80}")
    print(f"  📊 Tổng số dòng:         {stats['total']}")
    print(f"\n  📦 SAM_CASE:")
    print(f"     - Visit 1 (Sample 1): {stats['sam_v1']}")
    print(f"     - Visit 2 (Sample 2): {stats['sam_v2']}")
    print(f"     - Visit 3 (Sample 3): {stats['sam_v3']}")
    print(f"     - Visit 4 (Sample 4): {stats['sam_v4']}")
    print(f"\n  🔬 LAB_CASE:             {stats['lab']}")
    print(f"  💀 DISCH_CASE (death):   {stats['disch']}")
    print(f"  📅 FU_CASE_28:           {stats['fu28']}")
    print(f"  📅 FU_CASE_90:           {stats['fu90']}")
    print(f"\n  ⚠️  Bỏ qua:              {stats['skipped']}")
    print(f"  ❌ Lỗi:                  {stats['errors']}")
    print(f"{'='*80}\n")
    
    # Thống kê theo site
    print("📊 THỐNG KÊ THEO SITE:")
    for site_name, site_id in SITE_MAPPING.items():
        sam_count = SAM_CASE.objects.using(STUDY_DATABASE).filter(
            USUBJID__USUBJID__SITEID=site_id
        ).count()
        lab_count = LAB_Microbiology.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id
        ).count()
        disch_count = DISCH_CASE.objects.using(STUDY_DATABASE).filter(
            SITEID=site_id,
            DEATHATDISCH='Yes'
        ).count()
        fu28_count = FU_CASE_28.objects.using(STUDY_DATABASE).filter(
            USUBJID__USUBJID__SITEID=site_id
        ).count()
        fu90_count = FU_CASE_90.objects.using(STUDY_DATABASE).filter(
            USUBJID__USUBJID__SITEID=site_id
        ).count()
        
        print(f"\n   {site_name} (Site {site_id}):")
        print(f"     - Samples: {sam_count}")
        print(f"     - Lab cultures: {lab_count}")
        print(f"     - Deaths: {disch_count}")
        print(f"     - FU D28: {fu28_count}")
        print(f"     - FU D90: {fu90_count}")
    
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
    print("SCRIPT IMPORT ĐẦY ĐỦ - SAMPLE, LAB, DISCHARGE & FOLLOW-UP")
    print("="*80)
    print(f"📁 File: {file_path}")
    print(f"🗄️  Database: {STUDY_DATABASE}")
    print(f"\n📋 IMPORT VÀO CÁC BẢNG:")
    print(f"   1. SAM_CASE (4 visits: V1, V2, V3, V4)")
    print(f"      - Always create record (mark NO if not collected)")
    print(f"   2. LAB_Microbiology (Multiple culture results per row)")
    print(f"      - Parse multiple Sample IDs: '625497 625498 625509'")
    print(f"      - Parse multiple Culture Types: 'Cấy máu Cấy máu Cấy DMB'")
    print(f"   3. DISCH_CASE (Death status)")
    print(f"   4. FU_CASE_28 (Follow-up Day 28)")
    print(f"   5. FU_CASE_90 (Follow-up Day 90)")
    print(f"\n📋 LƯU Ý:")
    print(f"   ✅ Tất cả samples đều KPN+ (Klebsiella positive)")
    print(f"   ✅ Stool/Rectal → STOOL field")
    print(f"   ✅ No sample → mark as 'NO' (not blank)")
    print(f"   ✅ Multiple samples per cell → create multiple LAB records")
    print(f"   ✅ Death = YES → update DISCH_CASE")
    print(f"   ✅ 4 visits: V1→Sample1, V2→Sample2, V3→Sample3, V4→Sample4")
    print(f"\n📋 SPECIMEN MAPPING:")
    print(f"   - Máu → BLOOD")
    print(f"   - Nước tiểu → URINE")
    print(f"   - Đàm → SPUTUM")
    print(f"   - BAL → BRONCHIAL")
    print(f"   - Dịch não tuỷ → CSF")
    print(f"   - Dịch ổ bụng/màng bụng/tụy → PERITONEAL_FLUID")
    print(f"   - Mủ/Dịch vết thương → WOUND")
    print(f"   - Còn lại → OTHER")
    print("="*80)
    
    confirm = input("\n⚠️  Bạn có chắc chắn muốn import? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        import_complete_data(file_path)
    else:
        print("\n❌ Đã hủy import.")