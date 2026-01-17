import re
import os

# Files to process
files = [
    r'c:\Users\Admin\Documents\GitHub\ResSynt_DUY\frontends\templates\studies\study_43en\patient\form\clinical_form.html',
    r'c:\Users\Admin\Documents\GitHub\ResSynt_DUY\frontends\templates\studies\study_43en\patient\form\clinical_page1.html',
    r'c:\Users\Admin\Documents\GitHub\ResSynt_DUY\frontends\templates\studies\study_43en\patient\form\clinical_page2.html',
    r'c:\Users\Admin\Documents\GitHub\ResSynt_DUY\frontends\templates\studies\study_43en\patient\form\clinical_page3.html',
]

# Icon pattern to remove
icon_pattern = re.compile(r'<i class="fas [^"]+"\s*[^>]*></i>\s*')

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count icons before
        matches = icon_pattern.findall(content)
        count_before = len(matches)
        
        # Remove icons
        new_content = icon_pattern.sub('', content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f'{os.path.basename(filepath)}: Removed {count_before} icons')
    except Exception as e:
        print(f'{filepath}: ERROR - {e}')

print('\nDone!')
