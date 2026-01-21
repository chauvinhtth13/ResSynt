"""
Script để xóa các LAB_Microbiology records có SPECIMENID sai
(chứa nhiều ID ghép với nhau như "626317 626316 142967")

Chạy script này TRƯỚC khi import lại dữ liệu
"""

import os
import sys
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

# Import model
from backends.studies.study_43en.models.patient import LAB_Microbiology

# ==========================================
# CẤU HÌNH
# ==========================================
STUDY_DATABASE = 'db_study_43en'


def find_and_delete_invalid_specimens():
    """
    Tìm và xóa các LAB_Microbiology records có SPECIMENID chứa:
    - Khoảng trắng (dấu cách)
    - Newlines
    - Nhiều số ID ghép với nhau
    """
    print(f"\n{'='*80}")
    print("TÌM VÀ XÓA CÁC LAB_MICROBIOLOGY RECORDS VỚI SPECIMENID SAI")
    print(f"{'='*80}\n")
    
    # Get all records
    all_labs = LAB_Microbiology.objects.using(STUDY_DATABASE).all()
    
    invalid_records = []
    
    for lab in all_labs:
        specimen_id = lab.SPECIMENID
        
        if specimen_id:
            # Check if contains whitespace (space, tab, newline)
            if re.search(r'\s', str(specimen_id)):
                invalid_records.append({
                    'id': lab.id,
                    'specimen_id': specimen_id,
                    'usubjid': lab.USUBJID_id,
                    'reason': 'Chứa khoảng trắng/newline'
                })
    
    print(f"📊 Tổng số records: {all_labs.count()}")
    print(f"❌ Số records không hợp lệ: {len(invalid_records)}")
    
    if not invalid_records:
        print("\n✅ Không có record nào cần xóa!")
        return
    
    print("\n📋 Danh sách records không hợp lệ:")
    for i, rec in enumerate(invalid_records, 1):
        print(f"  {i}. ID: {rec['id']} | USUBJID: {rec['usubjid']}")
        print(f"     SPECIMENID: '{rec['specimen_id'][:50]}...' [{rec['reason']}]")
    
    # Confirm delete
    print(f"\n⚠️  Sẽ xóa {len(invalid_records)} records")
    confirm = input("Bạn có chắc chắn muốn xóa? (yes/no): ").strip()
    
    if confirm.lower() in ['yes', 'y']:
        deleted_count = 0
        for rec in invalid_records:
            try:
                LAB_Microbiology.objects.using(STUDY_DATABASE).filter(id=rec['id']).delete()
                deleted_count += 1
                print(f"  ✅ Đã xóa ID: {rec['id']}")
            except Exception as e:
                print(f"  ❌ Lỗi xóa ID {rec['id']}: {e}")
        
        print(f"\n🎉 Đã xóa {deleted_count}/{len(invalid_records)} records")
    else:
        print("\n❌ Đã hủy xóa.")


if __name__ == "__main__":
    find_and_delete_invalid_specimens()
