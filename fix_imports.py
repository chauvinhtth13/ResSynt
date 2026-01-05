"""
Quick fix script to replace incorrect imports
"""
import os
import re
from pathlib import Path

# Base directory
base_dir = Path(r"c:\Users\duy.pham\Documents\GitHub\ResSynt")

# Pattern to find
old_import = "from backends.audit_log.utils.site_utils"
new_import = "from backends.studies.study_43en.utils.site_utils"

# Find all Python files
def fix_imports(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        # Skip logs and __pycache__
        if 'logs' in root or '__pycache__' in root or 'node_modules' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if old_import in content:
                        new_content = content.replace(old_import, new_import)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"✅ Fixed: {filepath}")
                        count += 1
                except Exception as e:
                    print(f"❌ Error in {filepath}: {e}")
    
    return count

if __name__ == "__main__":
    print("🔍 Searching and fixing incorrect imports...")
    
    # Fix in backends directory
    backends_dir = base_dir / "backends"
    count = fix_imports(backends_dir)
    
    print(f"\n✨ Fixed {count} files!")
