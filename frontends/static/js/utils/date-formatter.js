// frontends/static/js/utils/date-formatter.js
/**
 * Simple Date Formatter
 * Format dates to DD/MM/YYYY consistently
 */

'use strict';

(() => {
  /**
   * Format date to DD/MM/YYYY
   * @param {Date|string|number} date - Date to format
   * @returns {string} Formatted date (DD/MM/YYYY) or empty string
   */
  const formatDate = (date) => {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    
    return `${day}/${month}/${year}`;
  };

  /**
   * Format datetime to DD/MM/YYYY HH:MM
   * @param {Date|string|number} date - Date to format
   * @returns {string} Formatted datetime (DD/MM/YYYY HH:MM) or empty string
   */
  const formatDateTime = (date) => {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  };

  /**
   * Format time to HH:MM
   * @param {Date|string|number} date - Date to format
   * @returns {string} Formatted time (HH:MM) or empty string
   */
  const formatTime = (date) => {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return `${hours}:${minutes}`;
  };

  /**
   * Parse DD/MM/YYYY string to Date
   * @param {string} dateStr - Date string (DD/MM/YYYY)
   * @returns {Date|null} Date object or null
   */
  const parseDate = (dateStr) => {
    if (!dateStr) return null;
    
    const parts = dateStr.split('/');
    if (parts.length !== 3) return null;
    
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const year = parseInt(parts[2], 10);
    
    const date = new Date(year, month, day);
    return isNaN(date.getTime()) ? null : date;
  };

  /**
   * Get relative time (e.g., "2 giờ trước")
   * @param {Date|string|number} date - Date to compare
   * @param {string} lang - Language ('vi' or 'en')
   * @returns {string} Relative time string
   */
  const getRelativeTime = (date, lang = 'vi') => {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const diff = Date.now() - d.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (lang === 'vi') {
      if (seconds < 60) return 'Vừa xong';
      if (minutes < 60) return `${minutes} phút trước`;
      if (hours < 24) return `${hours} giờ trước`;
      return `${days} ngày trước`;
    } else {
      if (seconds < 60) return 'Just now';
      if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
      if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
      return `${days} day${days > 1 ? 's' : ''} ago`;
    }
  };

  /**
   * Auto-format date elements on page load
   */
  const autoFormatDates = () => {
    // Format dates (DD/MM/YYYY)
    document.querySelectorAll('[data-format-date]').forEach(el => {
      const dateValue = el.getAttribute('data-format-date');
      if (dateValue) {
        el.textContent = formatDate(dateValue);
      }
    });
    
    // Format datetimes (DD/MM/YYYY HH:MM)
    document.querySelectorAll('[data-format-datetime]').forEach(el => {
      const dateValue = el.getAttribute('data-format-datetime');
      if (dateValue) {
        el.textContent = formatDateTime(dateValue);
      }
    });
    
    // Format times (HH:MM)
    document.querySelectorAll('[data-format-time]').forEach(el => {
      const dateValue = el.getAttribute('data-format-time');
      if (dateValue) {
        el.textContent = formatTime(dateValue);
      }
    });
    
    // Format relative times
    document.querySelectorAll('[data-format-relative]').forEach(el => {
      const dateValue = el.getAttribute('data-format-relative');
      const lang = el.getAttribute('data-lang') || 'vi';
      if (dateValue) {
        el.textContent = getRelativeTime(dateValue, lang);
      }
    });
    
    // Auto-format all datepicker input fields (convert yyyy-mm-dd to dd/mm/yyyy)
    document.querySelectorAll('input.datepicker, input[type="text"].datepicker').forEach(el => {
      const val = el.value;
      if (val && /^\d{4}-\d{2}-\d{2}/.test(val)) {
        // Value is in yyyy-mm-dd format, convert to dd/mm/yyyy
        const formatted = formatDate(val);
        if (formatted) {
          el.value = formatted;
        }
      }
    });
  };

  // Public API
  window.DateFormatter = {
    formatDate,
    formatDateTime,
    formatTime,
    parseDate,
    getRelativeTime,
    autoFormatDates
  };

  // Auto-format on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoFormatDates);
  } else {
    autoFormatDates();
  }
})();
