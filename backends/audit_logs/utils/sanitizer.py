# backends/audit_logs/utils/sanitizer.py
"""
BASE Security Sanitizer - Shared across all studies

Prevents XSS, SQL injection, CSV injection, etc.

PERFORMANCE: Regex patterns are pre-compiled at module load time
"""
import re
import html
import unicodedata
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# Pre-compile regex patterns for better performance
_XSS_PATTERNS = [
    re.compile(r'<\s*script[^>]*>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<\s*/\s*script\s*>', re.IGNORECASE),
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),
    re.compile(r'<\s*iframe', re.IGNORECASE),
    re.compile(r'<\s*object', re.IGNORECASE),
    re.compile(r'<\s*embed', re.IGNORECASE),
    re.compile(r'<\s*img[^>]*(on\w+|src\s*=\s*["\']?\s*javascript)', re.IGNORECASE),
    re.compile(r'<\s*svg[^>]*on\w+', re.IGNORECASE),
    re.compile(r'<\s*body[^>]*on\w+', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'vbscript\s*:', re.IGNORECASE),
    re.compile(r'data\s*:\s*text/html', re.IGNORECASE),
    re.compile(r'&#\d+;'),
    re.compile(r'\\u[0-9a-f]{4}', re.IGNORECASE),
    re.compile(r'<\s*meta[^>]*http-equiv', re.IGNORECASE),
]

_SQL_PATTERNS = [
    re.compile(r'union\s+select', re.IGNORECASE),
    re.compile(r'select\s+.*\s+from', re.IGNORECASE),
    re.compile(r'insert\s+into', re.IGNORECASE),
    re.compile(r'update\s+.*\s+set', re.IGNORECASE),
    re.compile(r'delete\s+from', re.IGNORECASE),
    re.compile(r'drop\s+(table|database)', re.IGNORECASE),
    re.compile(r'create\s+(table|database)', re.IGNORECASE),
    re.compile(r'alter\s+table', re.IGNORECASE),
    re.compile(r"'--"),
    re.compile(r'--'),
    re.compile(r'/\*.*?\*/'),
    re.compile(r"'\s*(or|and)\s+'", re.IGNORECASE),
    re.compile(r'xp_cmdshell', re.IGNORECASE),
    re.compile(r'sp_executesql', re.IGNORECASE),
    re.compile(r'0x[0-9a-f]+', re.IGNORECASE),
    re.compile(r'char\s*\(', re.IGNORECASE),
    re.compile(r'concat\s*\(', re.IGNORECASE),
    re.compile(r'benchmark\s*\(', re.IGNORECASE),
    re.compile(r'sleep\s*\(', re.IGNORECASE),
    re.compile(r'pg_sleep', re.IGNORECASE),
    re.compile(r'waitfor\s+delay', re.IGNORECASE),
    re.compile(r'load_file\s*\(', re.IGNORECASE),
    re.compile(r'into\s+(out|dump)file', re.IGNORECASE),
    re.compile(r'information_schema', re.IGNORECASE),
    re.compile(r'sys\.tables|sysobjects', re.IGNORECASE),
    re.compile(r'pg_catalog', re.IGNORECASE),
]

_CMD_PATTERNS = [
    re.compile(r"[;&|`$]"),
    re.compile(r"\$\{.*?\}"),
    re.compile(r"\$\(.*?\)"),
]

# Pre-compile control char removal regex
_CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')


class SecuritySanitizer:
    """Comprehensive security sanitizer"""
    
    # Enhanced XSS patterns (prevent bypasses)
    XSS_PATTERNS = [
        r'<\s*script[^>]*>',                       # <script> opening tag
        r'<\s*/\s*script\s*>',                     # </script> closing tag
        r'javascript\s*:',                          # javascript: protocol
        r'on\w+\s*=',                              # onclick=, onerror=, etc.
        r'<\s*iframe',                             # <iframe
        r'<\s*object',                             # <object
        r'<\s*embed',                              # <embed
        r'<\s*img[^>]*(on\w+|src\s*=\s*["\']?\s*javascript)',  # <img with events
        r'<\s*svg[^>]*on\w+',                      # SVG events
        r'<\s*body[^>]*on\w+',                     # Body events
        r'expression\s*\(',                        # CSS expression()
        r'vbscript\s*:',                           # vbscript: protocol
        r'data\s*:\s*text/html',                   # data:text/html
        r'&#\d+;',                                 # HTML entities
        r'\\u[0-9a-f]{4}',                         # Unicode escape
        r'<\s*meta[^>]*http-equiv',                # <meta http-equiv
    ]
    
    # More precise SQL patterns (require SQL context)
    SQL_PATTERNS = [
        r'union\s+select',                         # UNION SELECT
        r'select\s+.*\s+from',                     # SELECT ... FROM
        r'insert\s+into',                          # INSERT INTO
        r'update\s+.*\s+set',                      # UPDATE ... SET
        r'delete\s+from',                          # DELETE FROM
        r'drop\s+(table|database)',                # DROP TABLE/DATABASE
        r'create\s+(table|database)',              # CREATE TABLE/DATABASE
        r'alter\s+table',                          # ALTER TABLE
        r"'--",                                    # SQL comment with quote
        r'--',                                     # SQL comment
        r'/\*.*?\*/',                              # /* comment */
        r"'\s*(or|and)\s+'",                       # '1' or '1'='1
        r'xp_cmdshell',                            # SQL Server xp_cmdshell
        r'sp_executesql',                          # SQL Server sp_executesql
        # Additional bypass techniques
        r'0x[0-9a-f]+',                            # Hex encoding
        r'char\s*\(',                              # CHAR() function
        r'concat\s*\(',                            # CONCAT() function
        r'benchmark\s*\(',                         # MySQL benchmark attack
        r'sleep\s*\(',                             # Time-based blind SQLi
        r'pg_sleep',                               # PostgreSQL sleep
        r'waitfor\s+delay',                        # SQL Server waitfor
        r'load_file\s*\(',                         # MySQL file read
        r'into\s+(out|dump)file',                  # MySQL file write
        r'information_schema',                     # Schema discovery
        r'sys\.tables|sysobjects',                 # SQL Server sys tables
        r'pg_catalog',                             # PostgreSQL catalog
    ]
    
    CMD_PATTERNS = [
        r"[;&|`$]",      # Shell metacharacters
        r"\$\{.*?\}",    # ${...} expansion
        r"\$\(.*?\)",    # $(...) command substitution
    ]
    
    def __init__(self, min_length: int = 3, max_length: int = 1000):
        """
        Args:
            min_length: Minimum character length (default 3)
            max_length: Maximum character length (default 1000)
        """
        self.max_length = max_length
        self.min_length = min_length
        self.max_special_char_ratio = 0.3  # 30%
    
    def _is_safe_char(self, c: str) -> bool:
        """
        Check if character is safe (including Vietnamese)
        
        Returns True for:
        - ASCII alphanumeric
        - Whitespace
        - Vietnamese characters (U+00C0 to U+1EF9)
        - Common punctuation
        """
        # ASCII alphanumeric
        if c.isalnum():
            return True
        
        # Whitespace
        if c.isspace():
            return True
        
        # Vietnamese Unicode range
        if '\u00C0' <= c <= '\u1EF9':
            return True
        
        # Common punctuation
        if c in '.,;:!?\'"()-/':
            return True
        
        return False
    
    def sanitize(self, text: str, field_name: str = '') -> Dict:
        """
        Comprehensive sanitization
        
        Returns:
            {
                'valid': bool,
                'sanitized': str,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        if not text:
            return {
                'valid': False,
                'sanitized': '',
                'errors': ['Lý do không được để trống'],
                'warnings': []
            }
        
        original = text
        
        # 1. Length check
        if len(text) > self.max_length:
            errors.append(f'Lý do quá dài (tối đa {self.max_length} ký tự)')
            text = text[:self.max_length]
        
        # 2. Strip whitespace
        text = text.strip()
        
        if len(text) < self.min_length:
            errors.append(f'Lý do quá ngắn (tối thiểu {self.min_length} ký tự)')
        
        # 3. Unicode normalization (prevent Unicode attacks)
        text = unicodedata.normalize('NFKC', text)
        
        # 4. Remove null bytes & control characters (use pre-compiled pattern)
        text = text.replace('\x00', '')
        text = _CONTROL_CHARS_PATTERN.sub('', text)
        
        # 5. Check XSS patterns (use pre-compiled patterns)
        xss_detected = False
        for pattern in _XSS_PATTERNS:
            if pattern.search(text):
                errors.append('Lý do chứa mã HTML/JavaScript không hợp lệ')
                logger.warning(
                    "XSS ATTEMPT blocked: %s = %s", field_name, original[:100]
                )
                xss_detected = True
                break
        
        # 6. Check SQL patterns (use pre-compiled patterns)
        if not xss_detected:  # Skip if already detected malicious content
            for pattern in _SQL_PATTERNS:
                if pattern.search(text):
                    errors.append('Lý do chứa từ khóa SQL không hợp lệ')
                    logger.warning(
                        "SQL INJECTION ATTEMPT blocked: %s = %s", field_name, original[:100]
                    )
                    break
        
        # 7. Check command injection patterns (use pre-compiled patterns)
        for pattern in _CMD_PATTERNS:
            if pattern.search(text):
                errors.append('Lý do chứa ký tự đặc biệt không hợp lệ')
                logger.warning(
                    "CMD INJECTION ATTEMPT blocked: %s = %s", field_name, original[:100]
                )
                break
        
        # 8. Special character ratio check (Vietnamese-aware)
        unsafe_chars = sum(1 for c in text if not self._is_safe_char(c))
        
        if len(text) > 0:
            ratio = unsafe_chars / len(text)
            if ratio > self.max_special_char_ratio:
                errors.append(
                    f'Lý do chứa quá nhiều ký tự đặc biệt không an toàn '
                    f'({ratio*100:.0f}%, tối đa {self.max_special_char_ratio*100:.0f}%)'
                )
        
        # 9. HTML escape (always!)
        sanitized = html.escape(text, quote=True)
        
        # 10. CSV injection prevention
        if sanitized and sanitized[0] in ['=', '+', '-', '@', '\t', '\r']:
            sanitized = "'" + sanitized
            warnings.append('Thêm dấu nháy đơn để đảm bảo an toàn khi export')
        
        # 11. Check if modified
        if sanitized != original:
            warnings.append('Lý do đã được làm sạch để đảm bảo an toàn')
        
        return {
            'valid': len(errors) == 0,
            'sanitized': sanitized,
            'errors': errors,
            'warnings': warnings
        }
    
    def sanitize_dict(self, data: Dict[str, str]) -> Dict:
        """Sanitize multiple fields"""
        results = {}
        all_errors = {}
        all_warnings = []
        
        for field, value in data.items():
            result = self.sanitize(value, field)
            
            results[field] = result['sanitized']
            
            if result['errors']:
                all_errors[field] = result['errors']
            
            if result['warnings']:
                all_warnings.extend(result['warnings'])
        
        return {
            'valid': len(all_errors) == 0,
            'sanitized': results,
            'errors': all_errors,
            'warnings': list(set(all_warnings))  # Deduplicate
        }
