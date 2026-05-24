// Healthcare Form — SmartQueue AI
// SAVE AS: js/healthcare-form.js
// Handles: department → doctor → priority + slot selection → OTP → submit

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('healthcare-form');
    let currentStep = 1;
    let formData = {
        department:    null,
        doctor:        null,
        priority:      null,
        selectedSlot:  null,
        slotTime:      null,
        otpVerified:   false,
        phone:         null
    };

    // ── Departments ───────────────────────────────────────────────────────────

    async function loadDepartments() {
        const departments = [
            { id: 'opd',        name: 'OPD',        icon: '🩺', queue: 0 },
            { id: 'emergency',  name: 'Emergency',  icon: '🚨', queue: 0 },
            { id: 'lab',        name: 'Laboratory', icon: '🔬', queue: 0 },
            { id: 'pharmacy',   name: 'Pharmacy',   icon: '💊', queue: 0 },
            { id: 'radiology',  name: 'Radiology',  icon: '📷', queue: 0 },
            { id: 'cardiology', name: 'Cardiology', icon: '❤️', queue: 0 }
        ];

        try {
            const queueData = await api.getHealthcareQueue();
            departments.forEach(dept => {
                const q = queueData.find(q => q.department === dept.id);
                if (q) dept.queue = q.count || 0;
            });
        } catch {}

        const grid = document.getElementById('department-grid');
        grid.innerHTML = departments.map(dept => `
            <div class="department-card" data-department="${dept.id}">
                <div class="department-icon">${dept.icon}</div>
                <div class="department-name">${dept.name}</div>
                <div class="department-queue">Current Queue: <strong>${dept.queue}</strong></div>
            </div>`).join('');

        document.querySelectorAll('.department-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.department-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                formData.department = card.dataset.department;
                document.querySelector('[data-step="1"] .next-step').disabled = false;
                document.getElementById('summary-department').textContent =
                    card.querySelector('.department-name').textContent;
                loadDoctors(formData.department);
            });
        });
    }

    // ── Doctors ───────────────────────────────────────────────────────────────

    async function loadDoctors(department) {
        const doctors = [
            { id: 'any',       name: 'Any Available Doctor', specialty: 'Fastest Queue',    wait: 8,  avatar: '👤' },
            { id: 'dr-sharma', name: 'Dr. Rajesh Sharma',    specialty: 'General Medicine', wait: 15, avatar: '👨‍⚕️' },
            { id: 'dr-patel',  name: 'Dr. Priya Patel',      specialty: 'Internal Medicine',wait: 25, avatar: '👩‍⚕️' },
            { id: 'dr-kumar',  name: 'Dr. Anil Kumar',       specialty: 'Family Medicine',  wait: 12, avatar: '👨‍⚕️' }
        ];

        const grid = document.getElementById('doctor-grid');
        grid.innerHTML = doctors.map(doc => `
            <div class="doctor-card" data-doctor="${doc.id}">
                <div class="doctor-avatar">${doc.avatar}</div>
                <div class="doctor-info">
                    <div class="doctor-name">${doc.name}</div>
                    <div class="doctor-specialty">${doc.specialty}</div>
                    <div class="doctor-status">
                        <span class="status-indicator ${doc.wait > 20 ? 'busy' : ''}"></span>
                        <span>~${doc.wait} min wait</span>
                    </div>
                </div>
            </div>`).join('');

        document.querySelectorAll('.doctor-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.doctor-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                formData.doctor = card.dataset.doctor;
                document.querySelector('[data-step="2"] .next-step').disabled = false;
                document.getElementById('summary-doctor').textContent =
                    card.querySelector('.doctor-name').textContent;
            });
        });
    }

    // ── Priority + slot selection ─────────────────────────────────────────────

    document.querySelectorAll('.priority-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.priority-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            formData.priority = card.dataset.priority;
            document.getElementById('summary-priority').textContent =
                card.querySelector('.priority-name').textContent;

            const times = { emergency: '~2', senior: '~8', normal: '~15' };
            document.getElementById('estimated-time').textContent = times[formData.priority];

            // Remove old emergency warning
            const old = document.getElementById('emergency-fraud-warning');
            if (old) old.remove();

            // Emergency fraud warning
            if (formData.priority === 'emergency') {
                const warning = document.createElement('div');
                warning.id = 'emergency-fraud-warning';
                warning.style.cssText = `
                    background:rgba(239,71,111,0.12);border:1px solid rgba(239,71,111,0.4);
                    border-radius:10px;padding:14px 16px;margin-top:14px;
                    font-size:0.88rem;color:#ef476f;line-height:1.5;`;
                warning.innerHTML = `<strong>⚠️ Emergency Notice</strong><br>
                    Emergency status gives immediate priority but will be <strong>verified by staff on arrival</strong>.
                    If your claim is rejected, your token moves to the back of the normal queue as a penalty.`;
                card.closest('.priority-grid').insertAdjacentElement('afterend', warning);
            }

            // Load slots for tomorrow
            loadAvailableSlots(formData.department);
        });
    });

    // ── Slot availability ─────────────────────────────────────────────────────

    async function loadAvailableSlots(department) {
        const container = document.getElementById('slot-grid');
        if (!container || !department) return;

        // Reset slot selection
        formData.selectedSlot = null;
        formData.slotTime     = null;
        const slotSummary = document.getElementById('summary-slot');
        if (slotSummary) slotSummary.textContent = 'Walk-in (no slot)';

        container.innerHTML = `
            <div style="padding:12px;font-size:0.88rem;color:var(--color-text-secondary);">
                Loading available slots for tomorrow...
            </div>`;

        try {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const dateStr = tomorrow.toISOString().split('T')[0];

            const res = await fetch(
                `${API_CONFIG.BASE_URL}/api/slots/available?date_str=${dateStr}&department=${department}&domain=healthcare`
            );
            const data = await res.json();

            const displayDate = tomorrow.toLocaleDateString('en-IN', {
                weekday: 'long', day: 'numeric', month: 'long'
            });

            if (!data.slots || data.slots.length === 0) {
                container.innerHTML = `
                    <div style="background:rgba(6,214,160,0.07);border:1px solid rgba(6,214,160,0.25);
                        border-radius:10px;padding:14px 16px;font-size:0.88rem;color:var(--color-text-secondary);">
                        No pre-booked slots available for tomorrow.
                        You can still join the walk-in queue on the day.
                    </div>`;
                // Walk-in is fine — don't block next step
                document.querySelector('[data-step="3"] .next-step').disabled = false;
                return;
            }

            container.innerHTML = `
                <p style="font-size:0.82rem;color:var(--color-text-secondary);margin-bottom:10px;">
                    Slots for <strong>${displayDate}</strong> — select one to pre-book,
                    or skip to join walk-in queue on the day.
                </p>
                ${data.slots.map(slot => {
                    const full = slot.is_full;
                    return `
                    <div class="slot-card ${full ? 'slot-full' : ''}"
                         data-slot-id="${slot.id}"
                         data-slot-time="${slot.slot_time}"
                         style="background:var(--color-background-secondary);
                            border:1px solid var(--color-border-tertiary);
                            border-radius:10px;padding:12px 16px;margin-bottom:8px;
                            cursor:${full ? 'not-allowed' : 'pointer'};
                            opacity:${full ? '0.45' : '1'};
                            display:flex;justify-content:space-between;align-items:center;
                            transition:border-color .15s,background .15s;">
                        <div>
                            <div style="font-weight:500;font-size:0.95rem;">
                                ${slot.slot_time} – ${slot.slot_end || ''}
                            </div>
                            <div style="font-size:0.78rem;color:var(--color-text-secondary);margin-top:2px;">
                                ${slot.available} of ${slot.capacity} spots left
                            </div>
                        </div>
                        <div style="font-size:0.78rem;padding:3px 10px;border-radius:20px;
                            background:${full ? 'rgba(239,71,111,0.1)' : 'rgba(6,214,160,0.1)'};
                            color:${full ? '#ef476f' : '#06d6a0'};">
                            ${full ? 'Full' : 'Available'}
                        </div>
                    </div>`;
                }).join('')}
                <div style="font-size:0.8rem;color:var(--color-text-secondary);margin-top:8px;padding:10px 14px;
                    background:var(--color-background-secondary);border-radius:8px;">
                    💡 No slot selected = walk-in queue on the day
                </div>`;

            // Slot click listener
            container.querySelectorAll('.slot-card:not(.slot-full)').forEach(card => {
                card.addEventListener('click', () => {
                    container.querySelectorAll('.slot-card').forEach(c => {
                        c.style.borderColor = 'var(--color-border-tertiary)';
                        c.style.background  = 'var(--color-background-secondary)';
                    });
                    card.style.borderColor = '#06d6a0';
                    card.style.background  = 'rgba(6,214,160,0.08)';
                    formData.selectedSlot = card.dataset.slotId;
                    formData.slotTime     = card.dataset.slotTime;
                    const slotSummary = document.getElementById('summary-slot');
                    if (slotSummary) slotSummary.textContent = card.dataset.slotTime;
                });
            });

            // Always allow next — slot is optional
            document.querySelector('[data-step="3"] .next-step').disabled = false;

        } catch (err) {
            container.innerHTML = `
                <div style="font-size:0.88rem;color:var(--color-text-secondary);padding:10px;">
                    Could not load slots. Walk-in queue available on the day.
                </div>`;
            document.querySelector('[data-step="3"] .next-step').disabled = false;
        }
    }

    // ── OTP section (step 4 — patient details) ────────────────────────────────

    function setupOTPSection() {
        const phoneInput  = document.getElementById('patient-phone');
        const sendOtpBtn  = document.getElementById('send-otp-btn');
        const otpSection  = document.getElementById('otp-section');
        const otpInput    = document.getElementById('otp-input');
        const verifyBtn   = document.getElementById('verify-otp-btn');
        const otpStatus   = document.getElementById('otp-status');

        if (!sendOtpBtn) return;  // OTP elements not on page, skip

        sendOtpBtn.addEventListener('click', async () => {
            const phone = phoneInput.value.trim();
            if (!phone || phone.length < 10) {
                alert('Please enter a valid 10-digit phone number first.');
                return;
            }
            formData.phone = phone;

            sendOtpBtn.disabled    = true;
            sendOtpBtn.textContent = '⏳ Sending...';

            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/api/slots/otp/send`, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({ phone })
                });
                const data = await res.json();

                otpSection.style.display = 'block';
                otpStatus.textContent    = '';
                sendOtpBtn.textContent   = '✓ OTP Sent — Resend';
                sendOtpBtn.disabled      = false;

                // Dev: show OTP in console (remove in production)
                if (data.dev_otp) console.log('[DEV] OTP:', data.dev_otp);

            } catch (err) {
                alert('Failed to send OTP. Please try again.');
                sendOtpBtn.disabled    = false;
                sendOtpBtn.textContent = 'Send OTP';
            }
        });

        verifyBtn.addEventListener('click', async () => {
            const otp = otpInput.value.trim();
            if (!otp || otp.length !== 6) {
                otpStatus.textContent = '⚠️ Enter the 6-digit OTP.';
                otpStatus.style.color = '#ef476f';
                return;
            }

            verifyBtn.disabled    = true;
            verifyBtn.textContent = '⏳ Verifying...';

            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/api/slots/otp/verify`, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({ phone: formData.phone, otp })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail);
                }

                formData.otpVerified = true;
                otpStatus.textContent = '✓ Phone verified!';
                otpStatus.style.color = '#06d6a0';

                // If slot selected: enable submit, else normal submit
                document.getElementById('submit-btn').disabled = false;

                verifyBtn.textContent = '✓ Verified';
                verifyBtn.style.background = 'rgba(6,214,160,0.15)';
                verifyBtn.style.color      = '#06d6a0';

            } catch (err) {
                otpStatus.textContent = '❌ ' + (err.message || 'Incorrect OTP.');
                otpStatus.style.color = '#ef476f';
                verifyBtn.disabled    = false;
                verifyBtn.textContent = 'Verify OTP';
            }
        });
    }

    // ── Step navigation ───────────────────────────────────────────────────────

    function updateStep(step) {
        currentStep = step;
        document.querySelectorAll('.form-section').forEach((s, i) => {
            s.classList.toggle('active', i + 1 === step);
        });
        document.querySelectorAll('.step-dot').forEach((dot, i) => {
            dot.classList.remove('active', 'completed');
            if (i + 1 < step) dot.classList.add('completed');
            if (i + 1 === step) dot.classList.add('active');
        });
        document.querySelectorAll('.step-line').forEach((line, i) => {
            line.classList.toggle('completed', i + 1 < step);
        });
        document.querySelector('.queue-form-container').scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Wire OTP when reaching step 4
        if (step === 4) setupOTPSection();
    }

    document.querySelectorAll('.next-step').forEach(btn =>
        btn.addEventListener('click', () => updateStep(currentStep + 1)));
    document.querySelectorAll('.prev-step').forEach(btn =>
        btn.addEventListener('click', () => updateStep(currentStep - 1)));

    // ── Form submission ───────────────────────────────────────────────────────

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name   = document.getElementById('patient-name').value.trim();
        const phone  = document.getElementById('patient-phone').value.trim();
        const age    = document.getElementById('patient-age').value;
        const gender = document.getElementById('patient-gender').value;
        const reason = document.getElementById('patient-reason').value.trim();

        if (!name || !phone) {
            alert('Please fill in your name and phone number.');
            return;
        }

        // If slot selected, OTP must be verified
        if (formData.selectedSlot && !formData.otpVerified) {
            alert('Please verify your phone number with OTP before booking a slot.');
            return;
        }

        const submitBtn = document.getElementById('submit-btn');
        submitBtn.disabled    = true;
        submitBtn.textContent = '⏳ Creating Token...';

        try {
            let response;

            if (formData.selectedSlot) {
                // ── Advance booking path ──────────────────────────────────
                const res = await fetch(`${API_CONFIG.BASE_URL}/api/slots/book`, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        slot_id:      parseInt(formData.selectedSlot),
                        phone:        phone,
                        patient_name: name,
                        department:   formData.department,
                        domain:       'healthcare',
                        priority:     formData.priority,
                        reason:       reason || null,
                        age:          age ? parseInt(age) : null,
                        gender:       gender || null
                    })
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Booking failed');
                }
                response = await res.json();

                localStorage.setItem('currentToken', JSON.stringify({
                    id:              response.token_id,
                    type:            'healthcare',
                    bookingType:     'advance',
                    name, phone,
                    department:      formData.department,
                    doctor:          formData.doctor,
                    priority:        formData.priority,
                    slotTime:        response.slot_time,
                    slotEnd:         response.slot_end,
                    appointmentDate: response.appointment_date,
                    slotPosition:    response.slot_position,
                    position:        response.estimated_queue_position,
                    estimatedWait:   null,
                    message:         response.message,
                    timestamp:       Date.now()
                }));

            } else {
                // ── Walk-in path ──────────────────────────────────────────
                response = await api.createHealthcareToken({
                    name, phone,
                    department: formData.department,
                    doctor:     formData.doctor,
                    priority:   formData.priority,
                    age:        age ? parseInt(age) : null,
                    gender:     gender || null,
                    reason:     reason || null
                });

                localStorage.setItem('currentToken', JSON.stringify({
                    id:            response.token_id,
                    type:          'healthcare',
                    bookingType:   'walkin',
                    name, phone,
                    department:    formData.department,
                    doctor:        formData.doctor,
                    priority:      formData.priority,
                    position:      response.position,
                    estimatedWait: response.estimated_wait_time,
                    timestamp:     Date.now()
                }));
            }

            window.location.href = 'token.html';

        } catch (error) {
            console.error('Error creating token:', error);
            alert('Failed to create token: ' + error.message);
            submitBtn.disabled    = false;
            submitBtn.textContent = '🎫 Get My Token';
        }
    });

    await loadDepartments();
});