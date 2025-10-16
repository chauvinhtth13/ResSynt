import json
import logging

logger = logging.getLogger(__name__)

def safe_json_loads(s, default=None):
    """Chuyển đổi chuỗi JSON thành dictionary hoặc trả về dictionary nếu đầu vào đã là dictionary."""
    if not s:
        logger.debug(f"safe_json_loads: Input is empty or None, returning default: {default}")
        return default if default is not None else {}
    if isinstance(s, dict):
        logger.debug(f"safe_json_loads: Input is already a dictionary: {s}")
        return s
    if isinstance(s, str) and s.strip() == '':
        logger.debug(f"safe_json_loads: Input string is empty, returning default: {default}")
        return default if default is not None else {}
    try:
        result = json.loads(s)
        logger.debug(f"safe_json_loads: Successfully parsed JSON: {result}")
        return result
    except Exception as e:
        logger.error(f"safe_json_loads: Error parsing JSON '{s}': {e}")
        return default if default is not None else {}

def normalize_value(val):
    """Chuẩn hóa giá trị để so sánh."""
    if val is None:
        return ''
    if val is True:
        return '1'
    if val is False:
        return '0'
    v = str(val).strip()
    if not v or v.lower() in ['null', 'none', 'na', 'trống', 'n/a', 'undefined']:
        return ''
    if v.lower() in ['no', 'false']:
        return '0'
    if v.lower() in ['yes', 'true']:
        return '1'
    return v.lower()

def find_reason_and_label(field, reasons_dict):
    """Tìm lý do và label từ reasons_dict, hỗ trợ lồng sâu."""
    reasons = {}
    if isinstance(reasons_dict, dict):
        for k, v in reasons_dict.items():
            if isinstance(v, dict) and 'reason' in v:
                reason_val = v.get('reason')
                # Recurse nếu reason lồng
                while isinstance(reason_val, dict) and 'reason' in reason_val:
                    reason_val = reason_val.get('reason')
                reasons[k] = reason_val
            else:
                reasons[k] = v
    reason = None
    label = field
    for possible_key in [field, field.upper(), field.lower()]:
        if possible_key in reasons:
            reason = reasons[possible_key]
            if isinstance(reasons_dict.get(possible_key), dict):
                # Lấy label từ dict gốc
                item = reasons_dict.get(possible_key)
                while isinstance(item, dict) and 'label' in item:
                    label = item.get('label', field)
                    break
            break
    return reason, label