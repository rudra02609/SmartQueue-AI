/* ============================================
   SmartQueue AI - Queue Logic & Simulation
   ============================================ */

window.QueueManager = {
    queues: {
        healthcare: { opd: [], emergency: [], lab: [], pharmacy: [], radiology: [], cardiology: [] },
        banking: { cash: [], accounts: [], loans: [], lockers: [], general: [], forex: [] }
    },

    generateToken(type, department, priority = 'normal') {
        const prefix = type === 'healthcare' ? 'H' : 'B';
        const deptCode = department.substring(0, 3).toUpperCase();
        const num = String(Math.floor(Math.random() * 900) + 100);
        return `${prefix}-${deptCode}-${num}`;
    },

    addToQueue(type, department, tokenData) {
        const queue = this.queues[type][department];
        if (!queue) return null;

        const position = this.calculatePosition(queue, tokenData.priority);
        tokenData.position = position;
        tokenData.queuedAt = Date.now();
        queue.splice(position - 1, 0, tokenData);
        this.saveQueues();
        return tokenData;
    },

    calculatePosition(queue, priority) {
        if (priority === 'emergency') return 1;
        if (priority === 'senior' || priority === 'premium') {
            const normalStart = queue.findIndex(t => t.priority === 'normal' || t.priority === 'regular');
            return normalStart === -1 ? queue.length + 1 : normalStart + 1;
        }
        return queue.length + 1;
    },

    estimateWaitTime(position, type, department) {
        const avgServiceTime = {
            healthcare: { opd: 8, emergency: 5, lab: 4, pharmacy: 3, radiology: 10, cardiology: 12 },
            banking: { cash: 4, accounts: 10, loans: 15, lockers: 5, general: 3, forex: 8 }
        };
        const base = avgServiceTime[type]?.[department] || 5;
        return Math.max(1, Math.round((position - 1) * base + base * 0.5));
    },

    updatePosition(tokenId) {
        let found = null;
        for (const type in this.queues) {
            for (const dept in this.queues[type]) {
                const queue = this.queues[type][dept];
                const idx = queue.findIndex(t => t.id === tokenId);
                if (idx !== -1) {
                    found = { ...queue[idx], position: idx + 1 };
                    break;
                }
            }
            if (found) break;
        }
        return found;
    },

    simulateProgress() {
        for (const type in this.queues) {
            for (const dept in this.queues[type]) {
                if (this.queues[type][dept].length > 0 && Math.random() > 0.7) {
                    this.queues[type][dept].shift();
                }
            }
        }
        this.saveQueues();
    },

    saveQueues() {
        try { localStorage.setItem('smartqueue_queues', JSON.stringify(this.queues)); } catch (e) { }
    },

    loadQueues() {
        try {
            const saved = localStorage.getItem('smartqueue_queues');
            if (saved) this.queues = JSON.parse(saved);
        } catch (e) { }
    },

    init() {
        this.loadQueues();
        setInterval(() => this.simulateProgress(), 30000);
    }
};

document.addEventListener('DOMContentLoaded', () => QueueManager.init());
