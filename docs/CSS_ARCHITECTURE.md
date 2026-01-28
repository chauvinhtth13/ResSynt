# CSS Architecture - ResSynt Platform

## 📁 Thứ tự Load CSS

```
Bootstrap 5 → base.css → [page-specific].css
```

### Chi tiết:
1. **Bootstrap 5** (`bootstrap/css/bootstrap.css`) - Framework foundation
2. **base.css** (`base/css/base.css`) - Custom theme, extends Bootstrap
3. **Page-specific CSS** - Chỉ cho trang cụ thể:
   - `dashboard.css` - Dashboard layout & sidebar
   - `authentication.css` - Login/Register pages
   - `select_study.css` - Study selection page
   - `crf-forms.css` - Clinical Research Forms

---

## 🎨 CSS Variables Hierarchy

### Bootstrap 5 Variables (Sử dụng trực tiếp)
```css
/* Colors */
--bs-primary: #0d6efd
--bs-success: #198754
--bs-warning: #ffc107
--bs-danger: #dc3545
--bs-info: #0dcaf0

/* Typography */
--bs-body-font-family
--bs-body-font-size

/* Spacing & Sizing */
--bs-border-radius: 0.375rem
--bs-border-radius-sm: 0.25rem
--bs-border-radius-lg: 0.5rem
--bs-border-radius-xl: 1rem

/* Shadows */
--bs-box-shadow
--bs-box-shadow-sm
--bs-box-shadow-lg

/* Borders */
--bs-border-color
--bs-border-color-translucent
```

### base.css Variables (Custom Theme)
```css
/* Midnight Navy Color Scale */
--color-midnight-navy-50 → --color-midnight-navy-950

/* Accent Colors (Neon Theme) */
--color-accent-cyan: rgb(0, 245, 255)
--color-accent-purple: rgb(168, 85, 247)
--color-accent-pink: rgb(255, 110, 199)
--color-accent-teal: rgb(0, 191, 166)

/* Glass Morphism */
--glass-bg-primary
--glass-border
--blur-glass

/* Timing Functions */
--ease-out-expo
--ease-out-quad
--duration-fast: 150ms
--duration-normal: 200ms
--duration-slow: 300ms

/* Border Radius (Maps to Bootstrap) */
--radius-sm → --bs-border-radius-sm
--radius-md → --bs-border-radius
--radius-lg → --bs-border-radius-lg
--radius-xl → --bs-border-radius-xl
```

### dashboard.css Variables
```css
/* Sidebar Specific */
--sidebar-width: 18rem
--sidebar-bg: var(--color-midnight-navy-900)
--sidebar-text-default: rgba(255, 255, 255, 0.75)
```

### crf-forms.css Variables
```css
/* CRF Gradients */
--crf-gradient-primary
--crf-gradient-success (uses --bs-success)
--crf-gradient-danger (uses --bs-danger)
--crf-card-radius (uses --bs-border-radius-lg)
```

---

## 🔧 Best Practices

### ✅ DO
- Sử dụng Bootstrap utility classes khi có thể (`.d-flex`, `.mb-3`, `.text-primary`)
- Tham chiếu Bootstrap variables: `var(--bs-primary)`, `var(--bs-border-radius)`
- Kế thừa từ base.css cho custom theme variables
- Chỉ override khi cần thiết cho design system riêng

### ❌ DON'T
- Không định nghĩa lại colors đã có trong Bootstrap
- Không hardcode values khi có CSS variable
- Không viết CSS trùng lặp giữa các files
- Không override Bootstrap `.card`, `.btn` trực tiếp - tạo class mới như `.crf-card`

---

## 📊 File Sizes (Optimized)

| File | Lines | Purpose |
|------|-------|---------|
| bootstrap.css | ~12,000 | Framework (minify in production) |
| base.css | ~1,450 | Theme foundation |
| dashboard.css | ~1,100 | Dashboard layout |
| authentication.css | ~830 | Auth pages |
| select_study.css | ~540 | Study selection |
| crf-forms.css | ~2,150 | CRF forms |

---

## 🔄 Migration Notes (v2.0)

### Changes Made:
1. ✅ Removed duplicate `.sidebar-footer` (3 → 1 definition)
2. ✅ Removed unused classes: `.btn-notification`, `.text-accent-purple/pink/teal`, `.bg-glass`, `.bg-navy-blue-950`
3. ✅ Updated `:root` to reference Bootstrap variables
4. ✅ Removed duplicate keyframes in crf-forms.css
5. ✅ `.card` styles now extend Bootstrap (not override)

### Saved:
- ~100+ duplicate CSS lines removed
- Better maintainability with CSS variable references
