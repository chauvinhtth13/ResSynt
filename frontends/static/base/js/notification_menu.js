// static/js/components/notification_menu.js

/**
 * ========================================================================
 * NOTIFICATION MENU - MODERN MATERIAL DESIGN
 * Handles all notification interactions
 * ========================================================================
 */

(function() {
    'use strict';
    
    // ==========================================
    // CONFIG
    // ==========================================
    const CONFIG = {
        selectors: {
            markReadBtn: '.mark-read-btn',
            markAllBtn: '#markAllReadBtn',
            notifItem: '.notification-item',
            badge: '#unreadBadge',
            headerCount: '#unreadCountHeader',
            unreadDot: '.notification-unread-dot'
        },
        endpoints: {
            markRead: '/studies/43en/api/notification/read/',
            markAllRead: '/studies/43en/api/notification/read-all/'
        },
        classes: {
            unread: 'notification-item--unread',
            loading: 'is-loading'
        }
    };
    
    // ==========================================
    // UTILITIES
    // ==========================================
    const Utils = {
        /**
         * Get CSRF token
         */
        getCSRFToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                   document.querySelector('meta[name="csrf-token"]')?.content || '';
        },
        
        /**
         * Show toast notification
         */
        showToast(type, message) {
            if (window.toastr) {
                toastr[type](message);
            } else {
                console.log(`[${type.toUpperCase()}] ${message}`);
            }
        },
        
        /**
         * Update badge count
         */
        updateBadgeCount(count) {
            const badge = document.querySelector(CONFIG.selectors.badge);
            const headerCount = document.querySelector(CONFIG.selectors.headerCount);
            
            if (count > 0) {
                if (badge) {
                    badge.textContent = count;
                } else {
                    this.createBadge(count);
                }
                
                if (headerCount) {
                    headerCount.textContent = count;
                }
            } else {
                badge?.remove();
                headerCount?.remove();
            }
        },
        
        /**
         * Create badge element
         */
        createBadge(count) {
            const btn = document.getElementById('notificationDropdownButton');
            if (!btn) return;
            
            const badge = document.createElement('span');
            badge.id = 'unreadBadge';
            badge.className = 'notification-badge';
            badge.textContent = count;
            
            const srText = document.createElement('span');
            srText.className = 'visually-hidden';
            srText.textContent = 'unread notifications';
            badge.appendChild(srText);
            
            btn.appendChild(badge);
        }
    };
    
    // ==========================================
    // NOTIFICATION HANDLERS
    // ==========================================
    const NotificationHandlers = {
        /**
         * Mark single notification as read
         */
        async markAsRead(notifId, itemElement) {
            try {
                const response = await fetch(CONFIG.endpoints.markRead, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': Utils.getCSRFToken()
                    },
                    body: JSON.stringify({ notif_id: notifId })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update UI
                    itemElement.classList.remove(CONFIG.classes.unread);
                    itemElement.querySelector(CONFIG.selectors.unreadDot)?.remove();
                    itemElement.querySelector('.mark-read-btn')?.remove();
                    
                    // Update badge
                    Utils.updateBadgeCount(data.unread_count);
                    
                    console.log(' Marked as read:', notifId);
                } else {
                    throw new Error(data.message || 'Failed to mark as read');
                }
            } catch (error) {
                console.error(' Error marking as read:', error);
                Utils.showToast('error', 'Không thể đánh dấu đã đọc');
            }
        },
        
        /**
         * Mark all notifications as read
         */
        async markAllAsRead() {
            const markAllBtn = document.querySelector(CONFIG.selectors.markAllBtn);
            if (!markAllBtn) return;
            
            // Show loading
            markAllBtn.disabled = true;
            markAllBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
            
            try {
                const response = await fetch(CONFIG.endpoints.markAllRead, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': Utils.getCSRFToken()
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update all items
                    document.querySelectorAll(`.${CONFIG.classes.unread}`).forEach(item => {
                        item.classList.remove(CONFIG.classes.unread);
                    });
                    
                    // Remove all unread indicators
                    document.querySelectorAll(CONFIG.selectors.unreadDot).forEach(dot => dot.remove());
                    document.querySelectorAll('.mark-read-btn').forEach(btn => btn.remove());
                    
                    // Update badge
                    Utils.updateBadgeCount(0);
                    
                    // Hide button
                    markAllBtn.style.display = 'none';
                    
                    // Show success
                    Utils.showToast('success', `Đã đánh dấu ${data.marked_count} thông báo đã đọc`);
                    
                    console.log(' Marked all as read:', data.marked_count);
                } else {
                    throw new Error(data.message || 'Failed to mark all as read');
                }
            } catch (error) {
                console.error(' Error marking all as read:', error);
                Utils.showToast('error', 'Không thể đánh dấu tất cả');
                
                // Restore button
                markAllBtn.disabled = false;
                markAllBtn.innerHTML = '<i class="bi bi-check2-all"></i>';
            }
        }
    };
    
    // ==========================================
    // EVENT LISTENERS
    // ==========================================
    const EventHandlers = {
        init() {
            // Mark single as read
            document.addEventListener('click', (e) => {
                const btn = e.target.closest(CONFIG.selectors.markReadBtn);
                if (!btn) return;
                
                e.stopPropagation();
                e.preventDefault();
                
                const notifId = btn.dataset.notifId;
                const itemElement = btn.closest(CONFIG.selectors.notifItem);
                
                if (!notifId || !itemElement) return;
                
                // Disable button
                btn.disabled = true;
                btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                
                NotificationHandlers.markAsRead(notifId, itemElement);
            });
            
            // Mark all as read
            const markAllBtn = document.querySelector(CONFIG.selectors.markAllBtn);
            if (markAllBtn) {
                markAllBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    NotificationHandlers.markAllAsRead();
                });
            }
            
            console.log('🔔 Notification handlers initialized');
        }
    };
    
    // ==========================================
    // INITIALIZE
    // ==========================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => EventHandlers.init());
    } else {
        EventHandlers.init();
    }
})();