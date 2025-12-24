/**
 * Optimized Live Update System for Account Detail Page
 * - Polls only open positions (fast endpoint)
 * - Detects closed positions and reloads full data
 * - Updates only changed values
 */

class AccountLiveUpdate {
    constructor(accountId) {
        this.accountId = accountId;
        this.updateInterval = 1000; // 1 second
        this.intervalId = null;
        this.openPositionIds = new Set();
        this.isFirstLoad = true;
    }

    async init() {
        // First load: Get full data (open + closed + stats)
        await this.loadFullData();
        this.isFirstLoad = false;
        
        // Start optimized polling (open positions only)
        this.startAutoUpdate();
    }

    async loadFullData() {
        try {
            const response = await fetch(`/api/bot/account/${this.accountId}/live/`);
            const result = await response.json();
            
            if (result.status === 'success') {
                // Store open position IDs for comparison
                this.openPositionIds = new Set(result.data.open_positions.map(p => p.id));
                
                // Update full UI
                this.updateBalance(result.data.account.balance);
                this.updateBotStatus(result.data.account);
                this.updateStats(result.data.stats);
                this.rebuildOpenPositions(result.data.open_positions);
                this.rebuildTradeHistory(result.data.closed_positions);
            }
        } catch (error) {
            console.error('Failed to load full data:', error);
        }
    }

    startAutoUpdate() {
        if (this.intervalId) return; // Already running
        
        this.intervalId = setInterval(() => {
            this.fetchAndUpdateOptimized();
        }, this.updateInterval);
    }

    stopAutoUpdate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async fetchAndUpdateOptimized() {
        try {
            // Use optimized endpoint (only open positions)
            const response = await fetch(`/api/bot/account/${this.accountId}/open-only/`);
            const result = await response.json();
            
            if (result.status === 'success') {
                const data = result.data;
                
                // Get current position IDs from API
                const currentIds = new Set(data.open_positions.map(p => p.id));
                
                // Check for closed positions (in cache but not in current)
                const closedIds = [...this.openPositionIds].filter(id => !currentIds.has(id));
                
                // Check for new positions (in current but not in cache)
                const newIds = [...currentIds].filter(id => !this.openPositionIds.has(id));
                
                if (closedIds.length > 0 || newIds.length > 0) {
                    // Position(s) closed or new position(s) opened! Reload full data
                    if (closedIds.length > 0) {
                        console.log(`${closedIds.length} position(s) closed, reloading...`);
                    }
                    if (newIds.length > 0) {
                        console.log(`${newIds.length} new position(s) opened, reloading...`);
                    }
                    await this.loadFullData();
                } else {
                    // Just update P&L values (fast)
                    this.updateBalance(data.balance);
                    this.updateTotalPnL(data.total_pnl);
                    this.updateOpenPositionsPnL(data.open_positions);
                    this.openPositionIds = currentIds;
                }
            }
        } catch (error) {
            console.error('Failed to fetch live data:', error);
        }
    }

    updateBalance(balance) {
        const elem = document.querySelector('.account-balance');
        if (elem) {
            elem.textContent = `฿${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
    }

    updateBotStatus(account) {
        // Update all status badges on the page
        const statusBadges = document.querySelectorAll('.badge-glass[class*="badge-active"], .badge-glass[class*="badge-paused"], .badge-glass[class*="badge-down"], .badge-glass[class*="badge-danger"]');
        
        statusBadges.forEach(badge => {
            if (account.dd_blocked) {
                // Show DD Block status
                badge.className = 'badge-glass badge-danger';
                badge.style.fontSize = badge.style.fontSize || '0.75rem';
                badge.innerHTML = `🛑 DD Block: ${account.dd_block_reason_display}`;
            } else {
                // Show normal bot status
                let badgeClass = 'badge-glass ';
                if (account.bot_status === 'ACTIVE') {
                    badgeClass += 'badge-active';
                } else if (account.bot_status === 'PAUSED') {
                    badgeClass += 'badge-paused';
                } else {
                    badgeClass += 'badge-down';
                }
                badge.className = badgeClass;
                badge.textContent = account.bot_status_display;
            }
        });
    }

    updateTotalPnL(totalPnl) {
        const elem = document.getElementById('total-pnl');
        if (elem) {
            const formatted = `${totalPnl >= 0 ? '+' : ''}฿${Math.abs(totalPnl).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            elem.textContent = formatted;
            elem.className = `dashboard-stat-value ${totalPnl >= 0 ? 'text-profit' : 'text-loss'}`;
        }
    }

    updateStats(stats) {
        // Update Total P&L
        const totalPnlElem = document.getElementById('total-pnl');
        if (totalPnlElem) {
            const formatted = `${stats.total_pnl >= 0 ? '+' : ''}฿${Math.abs(stats.total_pnl).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            totalPnlElem.textContent = formatted;
            totalPnlElem.className = `dashboard-stat-value ${stats.total_pnl >= 0 ? 'text-profit' : 'text-loss'}`;
        }

        // Update Total Trades
        const totalTradesElem = document.getElementById('total-trades');
        if (totalTradesElem) {
            totalTradesElem.textContent = stats.total_trades;
        }

        // Update Win Rate
        const winRateElem = document.getElementById('win-rate');
        if (winRateElem) {
            winRateElem.textContent = `${stats.win_rate.toFixed(1)}%`;
        }
    }

    updateOpenPnL(currentOpenPnl) {
        // Calculate Total P&L dynamically
        // We need to keep track of closed P&L somehow
        // For now, just update if we have a Total P&L element that shows open P&L separately
        const totalPnlElem = document.getElementById('total-pnl');
        if (totalPnlElem) {
            // This will be updated properly when full data is loaded
            // For optimization, we skip this in fast updates
        }
    }

    updateOpenPositionsPnL(positions) {
        positions.forEach(pos => {
            const row = document.querySelector(`.position-row[data-position-id="${pos.id}"] .position-pnl-value`);
            if (row) {
                const formatted = `${pos.profit_loss >= 0 ? '+' : ''}฿${Math.abs(pos.profit_loss).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                row.textContent = formatted;
                row.className = `position-pnl-value ${pos.profit_loss >= 0 ? 'text-profit' : 'text-loss'}`;
            }
        });

        // Update section header count
        const header = document.querySelector('.section-header h3');
        if (header && header.textContent.includes('Open Positions')) {
            header.textContent = `Open Positions (${positions.length})`;
        }
    }

    rebuildOpenPositions(positions) {
        const container = document.getElementById('open-positions-container');
        if (!container) return;
        
        if (positions.length === 0) {
            container.innerHTML = `
                <div class="empty-state glass-card-static">
                    <i class="bi bi-bar-chart"></i>
                    <div class="empty-state-title">ไม่มี Position เปิดอยู่</div>
                    <div class="empty-state-text">ไม่มี Position ที่เปิดอยู่ในขณะนี้</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = positions.map(pos => `
            <div class="position-row glass-card fade-in" style="padding: 12px 16px; margin-bottom: 8px;" data-position-id="${pos.id}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 16px; font-weight: 600; color: #ffffff;">${pos.symbol}</span>
                        <span class="position-type ${pos.position_type.toLowerCase()}" style="font-size: 12px; padding: 2px 8px;">
                            ${pos.position_type_display}
                        </span>
                    </div>
                    <div style="text-align: right;">
                        <div class="position-pnl-value ${pos.profit_loss >= 0 ? 'text-profit' : 'text-loss'}" style="font-size: 18px; font-weight: 600;">
                            ${pos.profit_loss >= 0 ? '+' : ''}฿${Math.abs(pos.profit_loss).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; color: rgba(255, 255, 255, 0.6);">
                    <div>
                        <span style="opacity: 0.6;">${pos.position_type_display} ${pos.lot_size} lot at ${pos.entry_price}</span>
                    </div>
                    <div style="text-align: right;">
                        <span>${pos.opened_at}</span>
                    </div>
                </div>
            </div>
        `).join('');

        // Update section header
        const header = document.querySelector('.section-header h3');
        if (header && header.textContent.includes('Open Positions')) {
            header.textContent = `Open Positions (${positions.length})`;
        }
    }

    rebuildTradeHistory(positions) {
        const container = document.getElementById('trade-history-container');
        if (!container) return;
        
        if (positions.length === 0) {
            container.innerHTML = `
                <div class="empty-state glass-card-static">
                    <i class="bi bi-clock-history"></i>
                    <div class="empty-state-title">ยังไม่มีประวัติ</div>
                    <div class="empty-state-text">ยังไม่มีการเทรดที่ปิดไปแล้ว</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = positions.map(pos => `
            <div class="position-row glass-card fade-in" style="padding: 12px 16px; margin-bottom: 8px;" data-position-id="${pos.id}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 16px; font-weight: 600; color: #ffffff;">${pos.symbol}</span>
                        <span class="position-type ${pos.position_type.toLowerCase()}" style="font-size: 12px; padding: 2px 8px;">
                            ${pos.position_type_display}
                        </span>
                        ${pos.close_reason ? `
                        <span class="${pos.close_reason === 'TP' ? 'text-profit' : pos.close_reason === 'SL' ? 'text-loss' : 'text-secondary'}" style="font-size: 12px; padding: 2px 8px; border: 1px solid currentColor; border-radius: 4px;">
                            ${pos.close_reason_display}
                        </span>
                        ` : ''}
                    </div>
                    <div style="text-align: right;">
                        <div class="${pos.profit_loss >= 0 ? 'text-profit' : 'text-loss'}" style="font-size: 18px; font-weight: 600;">
                            ${pos.profit_loss >= 0 ? '+' : ''}฿${Math.abs(pos.profit_loss).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; color: rgba(255, 255, 255, 0.6);">
                    <div>
                        <span style="opacity: 0.6;">${pos.position_type_display} ${pos.lot_size} lot at ${pos.entry_price}</span>
                    </div>
                    <div style="text-align: right;">
                        <span>${pos.closed_at || ''}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

// Export for use in template
window.AccountLiveUpdate = AccountLiveUpdate;
