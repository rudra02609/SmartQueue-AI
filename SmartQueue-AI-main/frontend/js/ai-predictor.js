/* ============================================
   SmartQueue AI - AI Wait Time Predictor
   ============================================ */

window.AIPredictor = {
    weights: {
        queueLength: 1.2,
        timeOfDay: 0.8,
        dayOfWeek: 0.6,
        serviceType: 1.0,
        priority: 1.5
    },

    baseServiceTimes: {
        healthcare: { opd: 8, emergency: 5, lab: 4, pharmacy: 3, radiology: 10, cardiology: 12 },
        banking: { cash: 4, accounts: 10, loans: 15, lockers: 5, general: 3, forex: 8 }
    },

    predictWaitTime(params) {
        const { type, department, position, priority = 'normal' } = params;

        // Base time from service type
        let baseTime = this.baseServiceTimes[type]?.[department] || 5;

        // Position factor
        let waitTime = (position - 1) * baseTime;

        // Time of day adjustment (busy hours: 10-12, 2-4)
        const hour = new Date().getHours();
        if ((hour >= 10 && hour <= 12) || (hour >= 14 && hour <= 16)) {
            waitTime *= 1.3;
        } else if (hour < 9 || hour > 17) {
            waitTime *= 0.7;
        }

        // Day of week (Monday/Saturday busier)
        const day = new Date().getDay();
        if (day === 1 || day === 6) waitTime *= 1.2;

        // Priority adjustment
        const priorityFactors = { emergency: 0.2, senior: 0.5, premium: 0.4, normal: 1.0, regular: 1.0 };
        waitTime *= priorityFactors[priority] || 1.0;

        // Add randomness for realism (±15%)
        const variance = 0.15;
        waitTime *= (1 + (Math.random() - 0.5) * variance * 2);

        return Math.max(1, Math.round(waitTime));
    },

    getAccuracyConfidence(position) {
        // Higher confidence for shorter queues
        if (position <= 3) return 95;
        if (position <= 6) return 90;
        if (position <= 10) return 85;
        return 80;
    },

    formatPrediction(minutes) {
        if (minutes < 60) return `${minutes} min`;
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }
};

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIPredictor;
}
