// Token Display with Real-time Updates
document.addEventListener('DOMContentLoaded', async () => {
    const tokenData = JSON.parse(localStorage.getItem('currentToken'));

    if (!tokenData) {
        window.location.href = 'index.html';
        return;
    }

    const isHealthcare = tokenData.type === 'healthcare';
    const card = document.getElementById('token-card');
    const badge = document.getElementById('token-badge');

    // Set theme
    card.classList.add(tokenData.type);
    badge.classList.add(tokenData.type);

    // Display token info
    document.getElementById('token-icon').textContent = isHealthcare ? '🏥' : '🏦';
    document.getElementById('token-type-text').textContent = isHealthcare ? 'Healthcare' : 'Banking';
    document.getElementById('token-number').textContent = tokenData.id;
    document.getElementById('token-position').textContent = `#${tokenData.position} in queue`;
    document.getElementById('token-service').textContent = isHealthcare ?
        (tokenData.department || '-').toUpperCase() :
        (tokenData.service || '-').replace(/([A-Z])/g, ' $1').trim();
    document.getElementById('token-name').textContent = tokenData.name || '-';
    document.getElementById('token-time').textContent = new Date(tokenData.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit'
    });
    document.getElementById('token-wait').textContent = `~${tokenData.estimatedWait}`;

    // Connect to WebSocket for real-time updates
    try {
        api.connectWebSocket(tokenData.id, (message) => {
            console.log('WebSocket message:', message);
            
            if (message.type === 'position_update') {
                document.getElementById('token-position').textContent = `#${message.position} in queue`;
                document.getElementById('token-wait').textContent = `~${message.estimated_wait}`;
            }
            
            if (message.type === 'your_turn') {
                showToast('Your Turn!', 'Please proceed to the counter', 'success', '✓');
            }

            // Handle token rejection notification
            if (message.type === 'token_rejected') {
                showRejectionToast(message);
            }
        });
    } catch (error) {
        console.log('WebSocket not available, using polling');
        startPolling();
    }

    // Fallback: Poll for updates every 30 seconds
    function startPolling() {
        setInterval(async () => {
            try {
                const update = await api.getTokenPosition(tokenData.id);
                document.getElementById('token-position').textContent = `#${update.position} in queue`;
                document.getElementById('token-wait').textContent = `~${update.estimated_wait}`;
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 30000);
    }

    // Download token
    document.getElementById('download-token-btn').addEventListener('click', () => {
        downloadTokenAsImage(tokenData);
    });

    // Toast notification functions
    function showToast(title, message, type = 'info', icon = 'ℹ️', duration = 5000, action = null) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const progressBar = document.createElement('div');
        progressBar.className = 'toast-progress';
        
        const content = document.createElement('div');
        content.className = 'toast-content';
        
        const titleEl = document.createElement('div');
        titleEl.className = 'toast-title';
        titleEl.textContent = title;
        
        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.textContent = message;
        
        content.appendChild(titleEl);
        content.appendChild(messageEl);
        
        // Add action button if provided
        if (action) {
            const actionEl = document.createElement('div');
            actionEl.className = 'toast-action';
            const link = document.createElement('span');
            link.className = 'toast-link';
            link.textContent = action.label;
            link.addEventListener('click', action.callback);
            actionEl.appendChild(link);
            content.appendChild(actionEl);
        }
        
        const iconEl = document.createElement('div');
        iconEl.className = 'toast-icon';
        iconEl.textContent = icon;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '✕';
        closeBtn.addEventListener('click', () => {
            toast.remove();
        });
        
        toast.appendChild(iconEl);
        toast.appendChild(content);
        toast.appendChild(closeBtn);
        toast.appendChild(progressBar);
        
        container.appendChild(toast);
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, duration);
        }
    }

    // Rejection toast notification with action
    function showRejectionToast(message) {
        // Store rejection data for grievance form
        sessionStorage.setItem('rejectionData', JSON.stringify({
            token_id: message.token_id || tokenData.id,
            reason: message.reason || 'Rejected by staff',
            phone: tokenData.phone || '',
            rejection_time: new Date().toISOString()
        }));

        const reason = message.reason || 'Rejected by staff';
        const toastMessage = `Reason: ${reason}\nToken: ${message.token_id || tokenData.id}`;
        
        showToast(
            'Token Rejected ⚠️',
            toastMessage,
            'rejection',
            '⚠️',
            0, // Don't auto-dismiss
            {
                label: 'File Appeal →',
                callback: () => {
                    // Pass token data to grievance form
                    const rejectionData = JSON.parse(sessionStorage.getItem('rejectionData') || '{}');
                    sessionStorage.setItem('grievanceData', JSON.stringify({
                        token_number: rejectionData.token_id,
                        phone: rejectionData.phone,
                        reason_code: 'emergency_rejected',
                        pre_filled: true
                    }));
                    window.location.href = 'grievance.html';
                }
            }
        );
    }
});

function downloadTokenAsImage(tokenData) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 600;
    canvas.height = 800;

    // Background
    const gradient = ctx.createLinearGradient(0, 0, 600, 800);
    gradient.addColorStop(0, '#0a0a1a');
    gradient.addColorStop(1, '#1a1a2e');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 600, 800);

    // Card
    ctx.fillStyle = 'rgba(30, 30, 50, 0.9)';
    ctx.beginPath();
    ctx.roundRect(40, 40, 520, 720, 20);
    ctx.fill();

    // Border
    const isHealthcare = tokenData.type === 'healthcare';
    ctx.strokeStyle = isHealthcare ? '#06d6a0' : '#ffd60a';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(40, 40, 520, 720, 20);
    ctx.stroke();

    // Header
    ctx.fillStyle = isHealthcare ? 'rgba(6, 214, 160, 0.2)' : 'rgba(255, 214, 10, 0.2)';
    ctx.beginPath();
    ctx.roundRect(200, 60, 200, 40, 20);
    ctx.fill();

    ctx.fillStyle = isHealthcare ? '#06d6a0' : '#ffd60a';
    ctx.font = 'bold 18px Arial';
    ctx.textAlign = 'center';
    ctx.fillText((isHealthcare ? '🏥 Healthcare' : '🏦 Banking'), 300, 88);

    // Token number
    ctx.font = 'bold 72px Arial';
    const tokenGradient = ctx.createLinearGradient(150, 150, 450, 200);
    tokenGradient.addColorStop(0, '#a855f7');
    tokenGradient.addColorStop(1, '#06d6a0');
    ctx.fillStyle = tokenGradient;
    ctx.fillText(tokenData.id, 300, 200);

    ctx.fillStyle = '#888';
    ctx.font = '16px Arial';
    ctx.fillText('Your Queue Number', 300, 240);

    // Details
    const details = [
        { label: 'Position', value: `#${tokenData.position} in queue` },
        { label: 'Service', value: isHealthcare ? (tokenData.department || '-').toUpperCase() : (tokenData.service || '-') },
        { label: 'Name', value: tokenData.name || '-' },
        { label: 'Time', value: new Date(tokenData.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }
    ];

    let yPos = 300;
    details.forEach(detail => {
        ctx.fillStyle = 'rgba(10, 10, 20, 0.5)';
        ctx.beginPath();
        ctx.roundRect(60, yPos, 480, 60, 10);
        ctx.fill();

        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(detail.label.toUpperCase(), 75, yPos + 25);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 16px Arial';
        ctx.fillText(detail.value, 75, yPos + 48);

        yPos += 75;
    });

    // Wait time
    ctx.fillStyle = 'rgba(168, 85, 247, 0.1)';
    ctx.beginPath();
    ctx.roundRect(60, 600, 480, 100, 15);
    ctx.fill();

    ctx.fillStyle = '#a855f7';
    ctx.font = 'bold 48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`~${tokenData.estimatedWait}`, 300, 660);

    ctx.fillStyle = '#888';
    ctx.font = '14px Arial';
    ctx.fillText('Est. Wait (min) • 🤖 AI Predicted', 300, 690);

    // Footer
    ctx.fillStyle = '#666';
    ctx.font = '14px Arial';
    ctx.fillText('SmartQueue AI', 300, 730);

    // Download
    const link = document.createElement('a');
    link.download = `Token-${tokenData.id}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}
