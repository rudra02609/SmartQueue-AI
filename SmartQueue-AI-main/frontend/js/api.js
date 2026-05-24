// API Client for SmartQueue Backend
class SmartQueueAPI {
    constructor() {
        this.baseURL = API_CONFIG.BASE_URL;
        this.wsURL = API_CONFIG.WS_URL;
        this.token = localStorage.getItem('authToken');
        this.ws = null;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, { ...options, headers });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    // ── Auth ──────────────────────────────────────
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await this.request(API_CONFIG.ENDPOINTS.LOGIN, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        this.token = response.access_token;
        localStorage.setItem('authToken', this.token);
        return response;
    }

    async register(userData) {
        return await this.request(API_CONFIG.ENDPOINTS.REGISTER, {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    // ── Healthcare ────────────────────────────────
    async createHealthcareToken(tokenData) {
        return await this.request(API_CONFIG.ENDPOINTS.HEALTHCARE_TOKEN, {
            method: 'POST',
            body: JSON.stringify({
                patient_name: tokenData.name,
                phone: tokenData.phone,
                department: tokenData.department,
                doctor_id: tokenData.doctor,
                priority: tokenData.priority,
                age: tokenData.age,
                gender: tokenData.gender,
                reason: tokenData.reason
            })
        });
    }

    async getHealthcareQueue(department = null) {
        const params = department ? `?department=${department}` : '';
        return await this.request(`${API_CONFIG.ENDPOINTS.HEALTHCARE_QUEUE}${params}`);
    }

    // ── Banking ───────────────────────────────────
    async createBankingToken(tokenData) {
        return await this.request(API_CONFIG.ENDPOINTS.BANKING_TOKEN, {
            method: 'POST',
            body: JSON.stringify({
                customer_name: tokenData.name,
                phone: tokenData.phone,
                service_type: tokenData.service,
                account_type: tokenData.accountType,
                is_premium: tokenData.isPremium || false
            })
        });
    }

    async getBankingQueue(serviceType = null) {
        const params = serviceType ? `?service_type=${serviceType}` : '';
        return await this.request(`${API_CONFIG.ENDPOINTS.BANKING_QUEUE}${params}`);
    }

    // ── Token Management ──────────────────────────
    async getToken(tokenId) {
        return await this.request(`${API_CONFIG.ENDPOINTS.GET_TOKEN}/${tokenId}`);
    }

    // FIX 1: Was building /api/tokens/{id} — now correctly builds /api/tokens/{id}/position
    async getTokenPosition(tokenId) {
        return await this.request(`${API_CONFIG.ENDPOINTS.QUEUE_POSITION}/${tokenId}/position`);
    }

    // FIX 2: Was PUT /api/tokens/{id} — backend expects PATCH /api/tokens/{id}/status
    async updateTokenStatus(tokenId, status) {
        return await this.request(`${API_CONFIG.ENDPOINTS.UPDATE_TOKEN}/${tokenId}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status })
        });
    }

    async getQueueStatus(queueType, queueId) {
        return await this.request(`${API_CONFIG.ENDPOINTS.QUEUE_STATUS}/${queueType}/${queueId}`);
    }

    // ── Analytics ─────────────────────────────────
    async getAnalytics(timeRange = '24h') {
        return await this.request(`${API_CONFIG.ENDPOINTS.ANALYTICS}?range=${timeRange}`);
    }

    // ── Admin ─────────────────────────────────────
    async getAdminDashboard() {
        return await this.request(API_CONFIG.ENDPOINTS.ADMIN_DASHBOARD);
    }

    async getAdminQueues() {
        return await this.request(API_CONFIG.ENDPOINTS.ADMIN_QUEUES);
    }

    // FIX 3: Was /api/admin/queues/{id}/next — backend endpoint is /call-next
    async callNextToken(queueId) {
        return await this.request(`${API_CONFIG.ENDPOINTS.ADMIN_QUEUES}/${queueId}/call-next`, {
            method: 'POST'
        });
    }

    // ── Admin token actions (new) ─────────────────────
    // Call a specific token to counter — triggers buffer-aware recalculation
    async adminCallToken(tokenId) {
        return await this.request(`/api/admin/tokens/${tokenId}/call`, { method: 'PATCH' });
    }

    // Skip token — moves to end, adds SKIP_GRACE_BUFFER for next person
    async adminSkipToken(tokenId) {
        return await this.request(`/api/admin/tokens/${tokenId}/skip`, { method: 'PATCH' });
    }

    // Complete service for a token — marks done, recalculates queue
    async adminCompleteToken(tokenId) {
        return await this.request(`/api/admin/tokens/${tokenId}/complete`, { method: 'PATCH' });
    }

    // Emergency fraud: reject claim, penalty-move to back of normal queue
    async rejectEmergencyClaim(tokenId) {
        return await this.request(`/api/admin/tokens/${tokenId}/reject-emergency`, { method: 'PATCH' });
    }

    // Buffer-aware cancel — protects users with low ETA from losing their slot
    async cancelToken(tokenId) {
        return await this.request(`/api/tokens/${tokenId}`, { method: 'DELETE' });
    }

    // ── WebSocket ─────────────────────────────────
    connectWebSocket(clientId, onMessage) {
        if (this.ws) {
            this.ws.close();
        }

        this.ws = new WebSocket(`${this.wsURL}/ws/${clientId}`);

        this.ws.onopen = () => console.log('WebSocket connected');

        this.ws.onmessage = (event) => {
            if (onMessage) {
                try {
                    onMessage(JSON.parse(event.data));
                } catch {
                    onMessage({ type: 'raw', data: event.data });
                }
            }
        };

        this.ws.onerror = (error) => console.error('WebSocket error:', error);

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            // Auto-reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(clientId, onMessage), 3000);
        };

        return this.ws;
    }

    disconnectWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Global instance
const api = new SmartQueueAPI();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SmartQueueAPI;
}