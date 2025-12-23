# backends/studies/study_43en/utils/audit_log_utils.py

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.utils.translation import gettext as _
from datetime import datetime, date

logger = logging.getLogger(__name__)


# ==========================================
# FIELD LABEL MAPPINGS
# ==========================================

FIELD_LABELS = {
    'SCRID': _('Mã sàng lọc'),
    'STUDYID': _('Mã nghiên cứu'),
    'SITEID': _('Mã cơ sở'),
    'INITIAL': _('Tên viết tắt'),
    'UPPER16AGE': _('Tuổi trên 16'),
    'INFPRIOR2OR48HRSADMIT': _('Nhiễm khuẩn trước/sau 48h'),
    'ISOLATEDKPNFROMINFECTIONORBLOOD': _('Phân lập KPN'),
    'KPNISOUNTREATEDSTABLE': _('KPN chưa điều trị ổn định'),
    'CONSENTTOSTUDY': _('Đồng ý tham gia'),
    'SCREENINGFORMDATE': _('Ngày sàng lọc'),
    'UNRECRUITED_REASON': _('Lý do không tuyển'),
    'SUBJID': _('Mã bệnh nhân'),
    'USUBJID': _('Mã bệnh nhân duy nhất'),
}


# ==========================================
# VALUE FORMATTERS
# ==========================================

def format_value_for_display(field_name: str, value: Any) -> str:
    """
    Format giá trị để hiển thị trong audit log
    Xử lý: boolean, date, None, và các giá trị đặc biệt
    """
    # Handle None/empty
    if value is None or value == '':
        return '<em class="text-muted">Trống</em>'
    
    # Handle boolean
    if isinstance(value, bool):
        return 'Có' if value else 'Không'
    
    # Handle string boolean representations
    if isinstance(value, str):
        if value.lower() in ['true', '1', 'yes']:
            return 'Có'
        if value.lower() in ['false', '0', 'no']:
            return 'Không'
    
    # Handle dates
    if isinstance(value, (date, datetime)):
        return value.strftime('%d/%m/%Y')
    
    # Handle date strings
    if isinstance(value, str) and len(value) == 10:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass
    
    return str(value)


def normalize_value(val: Any) -> str:
    """
    Chuẩn hóa giá trị để so sánh
    """
    if val is None:
        return ''
    if val is True or val == '1' or val == 1:
        return '1'
    if val is False or val == '0' or val == 0:
        return '0'
    
    v = str(val).strip()
    if not v or v.lower() in ['null', 'none', 'na', 'trống', 'n/a', 'undefined']:
        return ''
    if v.lower() in ['no', 'false']:
        return '0'
    if v.lower() in ['yes', 'true']:
        return '1'
    
    # Normalize dates to YYYY-MM-DD
    if v and len(v) >= 8:
        # Try DD/MM/YYYY format
        if '/' in v:
            try:
                parts = v.split('/')
                if len(parts) == 3 and len(parts[2]) == 4:
                    return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except:
                pass
    
    return v.lower()


# ==========================================
# CHANGE DETECTION
# ==========================================

def compute_changes_from_history(
    current_record: Any,
    previous_record: Any,
    excluded_fields: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Tính toán thay đổi giữa 2 historical records
    
    Args:
        current_record: Historical record hiện tại
        previous_record: Historical record trước đó
        excluded_fields: Danh sách fields không cần track
    
    Returns:
        List of changes với format:
        [{
            'field': 'UPPER16AGE',
            'label': 'Tuổi trên 16',
            'old_value': False,
            'new_value': True,
            'old_display': 'Không',
            'new_display': 'Có'
        }]
    """
    if excluded_fields is None:
        excluded_fields = [
            'history_id', 'history_date', 'history_change_reason',
            'history_type', 'history_user_id', 'id'
        ]
    
    changes = []
    
    # Get all fields from current record
    current_fields = {
        f.name: getattr(current_record, f.name, None)
        for f in current_record._meta.fields
        if f.name not in excluded_fields
    }
    
    # Compare with previous record
    for field_name, new_value in current_fields.items():
        if not previous_record:
            # Nếu không có previous record (first entry), skip
            continue
        
        old_value = getattr(previous_record, field_name, None)
        
        # Normalize và compare
        old_normalized = normalize_value(old_value)
        new_normalized = normalize_value(new_value)
        
        if old_normalized != new_normalized:
            changes.append({
                'field': field_name,
                'label': FIELD_LABELS.get(field_name, field_name),
                'old_value': old_value,
                'new_value': new_value,
                'old_display': format_value_for_display(field_name, old_value),
                'new_display': format_value_for_display(field_name, new_value),
            })
    
    return changes


def parse_change_reason(change_reason: str) -> Dict[str, str]:
    """
    Parse change_reason string thành dictionary
    
    Handles formats:
    - "Field1: reason1 | Field2: reason2"
    - JSON string
    - Plain text
    """
    if not change_reason:
        return {}
    
    # Try JSON first
    if change_reason.strip().startswith('{'):
        try:
            return json.loads(change_reason)
        except json.JSONDecodeError:
            pass
    
    # Parse pipe-separated format
    reasons = {}
    if '|' in change_reason:
        parts = change_reason.split('|')
        for part in parts:
            if ':' in part:
                field, reason = part.split(':', 1)
                reasons[field.strip()] = reason.strip()
    
    return reasons if reasons else {'_general': change_reason}


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def safe_json_loads(s: Any, default: Any = None) -> Any:
    """
    Chuyển đổi chuỗi JSON thành dictionary
    """
    if not s:
        return default if default is not None else {}
    
    if isinstance(s, dict):
        return s
    
    if isinstance(s, str) and s.strip() == '':
        return default if default is not None else {}
    
    try:
        return json.loads(s)
    except Exception as e:
        logger.error(f"Error parsing JSON '{s}': {e}")
        return default if default is not None else {}


def get_field_label(field_name: str) -> str:
    """
    Lấy label tiếng Việt cho field
    """
    return FIELD_LABELS.get(field_name, field_name)


# ==========================================
# VIEW HELPERS
# ==========================================

def prepare_audit_log_context(historical_record: Any) -> Dict[str, Any]:
    """
    Chuẩn bị context data cho audit log detail view
    
    Args:
        historical_record: Historical record cần hiển thị
    
    Returns:
        Dictionary chứa:
        - record: Historical record
        - changes: List of changes
        - reasons: Parsed change reasons
        - metadata: User, date, action type
    """
    # Get previous record
    previous_records = (
        historical_record.instance.history
        .filter(history_date__lt=historical_record.history_date)
        .order_by('-history_date')
    )
    previous_record = previous_records.first() if previous_records.exists() else None
    
    # Compute changes
    changes = compute_changes_from_history(historical_record, previous_record)
    
    # Parse reasons
    reasons = parse_change_reason(historical_record.history_change_reason or '')
    
    # Match reasons with changes
    for change in changes:
        field_name = change['field']
        # Try multiple key formats
        reason = (
            reasons.get(field_name) or
            reasons.get(change['label']) or
            reasons.get(field_name.upper()) or
            reasons.get(field_name.lower()) or
            reasons.get('_general')
        )
        change['reason'] = reason or ''
    
    return {
        'record': historical_record,
        'changes': changes,
        'reasons': reasons,
        'metadata': {
            'user_id': historical_record.history_user_id,
            'date': historical_record.history_date,
            'action': historical_record.get_history_type_display(),
        }
    }