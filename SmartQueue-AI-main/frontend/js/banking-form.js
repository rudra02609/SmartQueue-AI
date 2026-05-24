// Banking Form Logic with API Integration
document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('banking-form');
    let currentStep = 1;
    let formData = {
        service: null,
        accountType: null,
        isPremium: false
    };

    // Load services
    async function loadServices() {
        const services = [
            { id: 'deposit', name: 'Cash Deposit', icon: '💵', queue: 0 },
            { id: 'withdrawal', name: 'Cash Withdrawal', icon: '💸', queue: 0 },
            { id: 'account', name: 'Account Opening', icon: '📝', queue: 0 },
            { id: 'loan', name: 'Loan Services', icon: '🏠', queue: 0 },
            { id: 'cards', name: 'Cards & Cheques', icon: '💳', queue: 0 },
            { id: 'investment', name: 'Investment', icon: '📈', queue: 0 }
        ];

        try {
            const queueData = await api.getBankingQueue();
            services.forEach(svc => {
                const queueInfo = queueData.find(q => q.service_type === svc.id);
                if (queueInfo) svc.queue = queueInfo.count || 0;
            });
        } catch (error) {
            console.log('Using default service data');
        }

        const grid = document.getElementById('service-grid');
        grid.innerHTML = services.map(svc => `
            <div class="service-card" data-service="${svc.id}">
                <div class="service-icon">${svc.icon}</div>
                <div class="service-name">${svc.name}</div>
                <div class="service-queue">Current Queue: <strong>${svc.queue}</strong></div>
            </div>
        `).join('');

        attachServiceListeners();
    }

    // Step navigation
    function updateStep(step) {
        currentStep = step;
        document.querySelectorAll('.form-section').forEach((section, idx) => {
            section.classList.toggle('active', idx + 1 === step);
        });
        document.querySelectorAll('.step-dot').forEach((dot, idx) => {
            dot.classList.remove('active', 'completed');
            if (idx + 1 < step) dot.classList.add('completed');
            if (idx + 1 === step) dot.classList.add('active');
        });
        document.querySelectorAll('.step-line').forEach((line, idx) => {
            line.classList.toggle('completed', idx + 1 < step);
        });
        document.querySelector('.queue-form-container').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Service selection
    function attachServiceListeners() {
        document.querySelectorAll('.service-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                formData.service = card.dataset.service;
                document.querySelector('[data-step="1"] .next-step').disabled = false;
                document.getElementById('summary-service').textContent = card.querySelector('.service-name').textContent;
            });
        });
    }

    // Account type selection
    document.querySelectorAll('.account-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.account-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            formData.accountType = card.dataset.account;
            formData.isPremium = card.dataset.account === 'premium';
            document.querySelector('[data-step="2"] .next-step').disabled = false;
            document.getElementById('summary-account').textContent = card.querySelector('.account-name').textContent;
            
            const times = { premium: '~3', savings: '~8', current: '~10' };
            document.getElementById('estimated-time').textContent = times[formData.accountType];
        });
    });

    // Navigation buttons
    document.querySelectorAll('.next-step').forEach(btn => {
        btn.addEventListener('click', () => updateStep(currentStep + 1));
    });
    document.querySelectorAll('.prev-step').forEach(btn => {
        btn.addEventListener('click', () => updateStep(currentStep - 1));
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('customer-name').value.trim();
        const phone = document.getElementById('customer-phone').value.trim();
        const accountNumber = document.getElementById('account-number').value.trim();

        if (!name || !phone) {
            alert('Please fill in your name and phone number.');
            return;
        }

        const submitBtn = document.getElementById('submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Creating Token...';

        try {
            const tokenData = {
                name,
                phone,
                service: formData.service,
                accountType: formData.accountType,
                isPremium: formData.isPremium,
                accountNumber: accountNumber || null
            };

            const response = await api.createBankingToken(tokenData);

            localStorage.setItem('currentToken', JSON.stringify({
                id: response.token_id,
                type: 'banking',
                ...tokenData,
                position: response.position,
                estimatedWait: response.estimated_wait_time,
                timestamp: Date.now()
            }));

            window.location.href = 'token.html';
        } catch (error) {
            console.error('Error creating token:', error);
            alert('Failed to create token. Please try again.');
            submitBtn.disabled = false;
            submitBtn.textContent = '🎫 Get My Token';
        }
    });

    // Initialize
    await loadServices();
});
