# CSS Optimization Report - Management Report

## Overview

This document summarizes the CSS optimization performed on `management_report.html` to reduce class duplication and improve maintainability.

## Files Created/Modified

### New File
- `frontends/static/studies/study_43en/css/dashboard-utilities.css`

### Modified File
- `frontends/templates/studies/study_43en/base/management_report.html`

---

## Duplicate Patterns Identified & Resolved

### 1. Stat Cards (4 instances)
**Before:**
```html
<div class="card h-100 border-0 shadow-sm border-start border-4 border-primary">
    <p class="text-uppercase fw-bold text-muted small mb-1">Label</p>
    <h2 class="fw-bold mb-0 text-primary">Value</h2>
```

**After:**
```html
<div class="card stat-card stat-card--primary">
    <p class="stat-card__label">Label</p>
    <h2 class="stat-card__value text-primary">Value</h2>
```

### 2. Chart/Data Cards (7 instances)
**Before:**
```html
<div class="card border-0 shadow-sm h-100">
    <div class="card-header bg-white border-bottom">
```

**After:**
```html
<div class="card chart-card chart-card--full-height">
    <div class="chart-card__header">
```

### 3. Card Header Flex Layout (6 instances)
**Before:**
```html
<div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
    <h6 class="mb-0 fw-bold">
        <i class="bi bi-graph-up text-primary me-2"></i>
        Title
    </h6>
```

**After:**
```html
<div class="header-flex">
    <h6 class="chart-card__title">
        <i class="bi bi-graph-up text-primary"></i>
        Title
    </h6>
```

### 4. Site Filter Dropdowns (5 instances)
**Before:**
```html
<select class="form-select form-select-sm site-filter-select" 
        data-chart="enrollment"
        style="width: auto; min-width: 120px;">
```

**After:**
```html
<select class="site-filter site-filter-select" data-chart="enrollment">
```

### 5. Filter Input Groups (6 instances)
**Before:**
```html
<div class="input-group input-group-sm" style="width: auto;">
    <label class="input-group-text">Label</label>
    <select class="form-select" style="min-width: 100px;">
```

**After:**
```html
<div class="filter-group">
    <label class="input-group-text">Label</label>
    <select class="form-select">
```

### 6. Loading Containers (5 instances)
**Before:**
```html
<div id="chartLoading" class="text-center py-5">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
    <p class="text-muted mt-2">Loading chart data...</p>
</div>
```

**After:**
```html
<div id="chartLoading" class="loading-container">
    <div class="spinner-border loading-spinner--primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
    <p class="loading-text">Loading chart data...</p>
</div>
```

### 7. Dashboard Header Section
**Before:**
```html
<div class="rounded-3 mb-4 bg-navy-blue-900 text-white p-4 shadow-sm">
    <div class="d-flex justify-content-between align-items-center mb-3 gap-3">
    ...
    <div class="d-flex flex-wrap justify-content-between gap-3 gap-lg-4 pt-2 border-top border-secondary border-opacity-25">
```

**After:**
```html
<div class="dashboard-header">
    <div class="dashboard-header__top">
    ...
    <div class="dashboard-header__stats">
```

### 8. Icon Boxes (2 instances)
**Before:**
```html
<div class="bg-white bg-opacity-10 rounded-3 d-flex align-items-center justify-content-center"
     style="width: 45px; height: 45px; flex-shrink: 0;">
    <i class="bi bi-geo-alt-fill text-white fs-5"></i>
</div>
```

**After:**
```html
<div class="icon-box icon-box--light">
    <i class="bi bi-geo-alt-fill text-white"></i>
</div>
```

### 9. Alert Notes (2 instances)
**Before:**
```html
<div class="alert alert-info mt-3">
    <small><i class="bi bi-info-circle me-1"></i>Note text</small>
</div>
```

**After:**
```html
<div class="alert-note alert-note--info">
    <small><i class="bi bi-info-circle"></i>Note text</small>
</div>
```

### 10. Table Scroll Containers (2 instances)
**Before:**
```html
<div class="table-responsive" style="max-height: 470px; overflow-y: auto;">
```

**After:**
```html
<div class="table-scroll">
```

---

## CSS Architecture (BEM Methodology)

The new CSS follows the BEM (Block Element Modifier) naming convention:

```
.block {}            /* Component root */
.block__element {}   /* Child element */
.block--modifier {}  /* Variation/state */
```

### Examples:
- `.stat-card` (Block)
- `.stat-card__label` (Element)
- `.stat-card--primary` (Modifier)

---

## Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| HTML File Size | ~832 lines | ~761 lines | -71 lines (8.5%) |
| Inline Styles | ~25 instances | ~5 instances | -80% |
| Class Repetition | High | Minimal | Significantly reduced |
| Maintainability | Scattered | Centralized | Improved |

### Key Improvements:
1. **Reduced Duplication**: Common patterns now use single, reusable classes
2. **Removed Inline Styles**: Most `style=""` attributes replaced with CSS classes
3. **Better Organization**: CSS follows BEM methodology for clarity
4. **Easier Updates**: Change once in CSS, applies everywhere
5. **Responsive Design**: Mobile-first responsive utilities included
6. **Custom Scrollbars**: Consistent scrollbar styling across browsers

---

## Usage Guide

### Include the CSS file:
```html
<link rel="stylesheet" href="{% static 'studies/study_43en/css/dashboard-utilities.css' %}">
```

### Available Classes:

| Class | Description |
|-------|-------------|
| `.stat-card` | Summary statistic card |
| `.stat-card--{color}` | Color variant (primary, success, info, warning, danger) |
| `.chart-card` | Data/chart container card |
| `.chart-card__header` | Card header section |
| `.header-flex` | Flexbox header layout |
| `.site-filter` | Site dropdown styling |
| `.filter-group` | Input group for filters |
| `.filter-controls` | Filter controls wrapper |
| `.loading-container` | Loading spinner container |
| `.loading-spinner--{color}` | Spinner color variant |
| `.icon-box` | Icon container box |
| `.dashboard-header` | Main header section |
| `.header-stat` | Header stat block |
| `.alert-note` | Alert/note styling |
| `.table-scroll` | Scrollable table container |

---

## Compatibility

- Bootstrap 5.x compatible
- CSS custom properties (CSS variables) used for theming
- Works with existing Django template tags
- CSP nonce not required for external CSS files
