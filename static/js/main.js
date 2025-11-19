// Main JavaScript for FX Bot Monitor

// Utility Functions
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Format number as Thai Baht
function formatCurrency(amount) {
    return new Intl.NumberFormat('th-TH', {
        style: 'currency',
        currency: 'THB',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Format number with sign (+/-)
function formatPnL(amount) {
    const formatted = formatCurrency(Math.abs(amount));
    return amount >= 0 ? `+${formatted}` : `-${formatted}`;
}

// Format date/time
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('th-TH', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// Calculate days until expiry
function daysUntilExpiry(expiryDate) {
    const now = new Date();
    const expiry = new Date(expiryDate);
    const diffTime = expiry - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

// Show loading spinner
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border spinner-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
}

// Show error message
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="empty-state-title">เกิดข้อผิดพลาด</div>
                <div class="empty-state-text">${message}</div>
            </div>
        `;
    }
}

// Card click animation
function addCardClickEffect() {
    const cards = document.querySelectorAll('.account-card, .position-card, .package-card');
    cards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't trigger if clicking a button
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                return;
            }
            
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

// Pull to refresh functionality
let touchStartY = 0;
let touchEndY = 0;
let isPulling = false;

document.addEventListener('touchstart', function(e) {
    if (window.scrollY === 0) {
        touchStartY = e.touches[0].clientY;
        isPulling = true;
    }
}, { passive: true });

document.addEventListener('touchmove', function(e) {
    if (isPulling) {
        touchEndY = e.touches[0].clientY;
        const pullDistance = touchEndY - touchStartY;
        
        if (pullDistance > 80) {
            // Show refresh indicator
            const indicator = document.getElementById('refresh-indicator');
            if (indicator) {
                indicator.style.opacity = '1';
            }
        }
    }
}, { passive: true });

document.addEventListener('touchend', function() {
    if (isPulling) {
        const pullDistance = touchEndY - touchStartY;
        
        if (pullDistance > 80) {
            // Trigger refresh
            location.reload();
        }
        
        // Hide refresh indicator
        const indicator = document.getElementById('refresh-indicator');
        if (indicator) {
            indicator.style.opacity = '0';
        }
        
        isPulling = false;
        touchStartY = 0;
        touchEndY = 0;
    }
});

// File input preview for payment slip
function previewPaymentSlip(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const preview = document.getElementById('slip-preview');
            if (preview) {
                preview.innerHTML = `
                    <div class="slip-preview">
                        <img src="${e.target.result}" alt="Payment Slip">
                    </div>
                `;
            }
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}

// Package selection
function selectPackage(packageId) {
    // Remove selected class from all packages
    document.querySelectorAll('.package-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Add selected class to clicked package
    const selectedCard = document.querySelector(`[data-package-id="${packageId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // Store selected package (can be submitted with form)
    const hiddenInput = document.getElementById('selected-package');
    if (hiddenInput) {
        hiddenInput.value = packageId;
    }
}

// Bot control functions
function pauseBot(accountId) {
    if (confirm('คุณต้องการหยุดบอทและปิด Order ทั้งหมดใช่หรือไม่?')) {
        // Show loading state
        showToast('กำลังหยุดบอท...', 'info');
        
        // Make API call (to be implemented)
        // fetch(`/api/accounts/${accountId}/pause/`, { method: 'POST' })
        //     .then(response => response.json())
        //     .then(data => {
        //         showToast('หยุดบอทสำเร็จ', 'success');
        //         setTimeout(() => location.reload(), 1500);
        //     })
        //     .catch(error => {
        //         showToast('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'error');
        //     });
    }
}

function resumeBot(accountId) {
    if (confirm('คุณต้องการเปิดบอทใช่หรือไม่?')) {
        showToast('กำลังเปิดบอท...', 'info');
        
        // Make API call (to be implemented)
        // Similar to pauseBot
    }
}

// Initialize page
function initializePage() {
    addCardClickEffect();
    
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && currentPath.includes(href)) {
            item.classList.add('active');
        }
    });
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePage);
} else {
    initializePage();
}

// Export functions for use in templates
window.FXBot = {
    formatCurrency,
    formatPnL,
    formatDateTime,
    daysUntilExpiry,
    showLoading,
    showError,
    previewPaymentSlip,
    selectPackage,
    pauseBot,
    resumeBot,
    showToast
};
