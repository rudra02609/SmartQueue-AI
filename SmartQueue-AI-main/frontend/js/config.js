// API Configuration
// Automatically uses deployed backend on production, localhost in development
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

const BACKEND_URL = IS_LOCAL ? 'http://localhost:8000' : 'https://smartqueue-ai-5wf2.onrender.com';

const API_CONFIG = {
    BASE_URL: BACKEND_URL,
    WS_URL:   BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://'),
    ENDPOINTS: {
        // Auth
        LOGIN:    '/api/auth/login',
        REGISTER: '/api/auth/register',

        // Tokens
        CREATE_TOKEN: '/api/tokens',
        GET_TOKEN:    '/api/tokens',
        UPDATE_TOKEN: '/api/tokens',
        QUEUE_POSITION: '/api/tokens',

        // Healthcare
        HEALTHCARE_TOKEN: '/api/healthcare/token',
        HEALTHCARE_QUEUE: '/api/healthcare/queue',

        // Banking
        BANKING_TOKEN: '/api/banking/token',
        BANKING_QUEUE: '/api/banking/queue',

        // Queues
        QUEUE_STATUS: '/api/queues/status',

        // Analytics
        ANALYTICS: '/api/analytics',

        // Admin
        ADMIN_DASHBOARD: '/api/admin/dashboard',
        ADMIN_QUEUES:    '/api/admin/queues'
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}