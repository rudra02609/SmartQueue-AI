/* ============================================
   SmartQueue AI - Particle System
   Animated background particles
   ============================================ */

class ParticleSystem {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouseX = 0;
        this.mouseY = 0;
        this.isRunning = true;

        // Configuration
        this.config = {
            particleCount: 80,
            particleSize: { min: 1, max: 3 },
            particleSpeed: { min: 0.2, max: 0.8 },
            connectionDistance: 150,
            mouseInfluence: 100,
            colors: [
                'rgba(0, 212, 170, 0.6)',   // Primary teal
                'rgba(255, 107, 53, 0.4)',   // Secondary coral
                'rgba(0, 180, 216, 0.5)',    // Healthcare cyan
                'rgba(247, 37, 133, 0.3)',   // Banking magenta
            ]
        };

        this.init();
    }

    init() {
        this.resize();
        this.createParticles();
        this.bindEvents();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    createParticles() {
        this.particles = [];

        for (let i = 0; i < this.config.particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: this.random(this.config.particleSize.min, this.config.particleSize.max),
                speedX: this.random(-this.config.particleSpeed.max, this.config.particleSpeed.max),
                speedY: this.random(-this.config.particleSpeed.max, this.config.particleSpeed.max),
                color: this.config.colors[Math.floor(Math.random() * this.config.colors.length)],
                opacity: Math.random() * 0.5 + 0.3,
                pulse: Math.random() * Math.PI * 2 // For pulsing effect
            });
        }
    }

    random(min, max) {
        return Math.random() * (max - min) + min;
    }

    bindEvents() {
        window.addEventListener('resize', () => {
            this.resize();
            this.createParticles();
        });

        document.addEventListener('mousemove', (e) => {
            this.mouseX = e.clientX;
            this.mouseY = e.clientY;
        });

        // Pause when tab is hidden
        document.addEventListener('visibilitychange', () => {
            this.isRunning = !document.hidden;
            if (this.isRunning) this.animate();
        });
    }

    animate() {
        if (!this.isRunning) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        this.particles.forEach((particle, index) => {
            // Update position
            particle.x += particle.speedX;
            particle.y += particle.speedY;

            // Update pulse
            particle.pulse += 0.02;

            // Mouse interaction
            const dx = this.mouseX - particle.x;
            const dy = this.mouseY - particle.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < this.config.mouseInfluence) {
                const force = (this.config.mouseInfluence - distance) / this.config.mouseInfluence;
                particle.x -= dx * force * 0.02;
                particle.y -= dy * force * 0.02;
            }

            // Wrap around edges
            if (particle.x < 0) particle.x = this.canvas.width;
            if (particle.x > this.canvas.width) particle.x = 0;
            if (particle.y < 0) particle.y = this.canvas.height;
            if (particle.y > this.canvas.height) particle.y = 0;

            // Draw particle with pulsing effect
            const pulseSize = particle.size + Math.sin(particle.pulse) * 0.5;

            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, pulseSize, 0, Math.PI * 2);
            this.ctx.fillStyle = particle.color;
            this.ctx.fill();

            // Draw glow
            const gradient = this.ctx.createRadialGradient(
                particle.x, particle.y, 0,
                particle.x, particle.y, pulseSize * 4
            );
            gradient.addColorStop(0, particle.color);
            gradient.addColorStop(1, 'transparent');

            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, pulseSize * 4, 0, Math.PI * 2);
            this.ctx.fillStyle = gradient;
            this.ctx.fill();

            // Draw connections
            for (let j = index + 1; j < this.particles.length; j++) {
                const other = this.particles[j];
                const dx = particle.x - other.x;
                const dy = particle.y - other.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < this.config.connectionDistance) {
                    const opacity = (1 - dist / this.config.connectionDistance) * 0.2;
                    this.ctx.beginPath();
                    this.ctx.moveTo(particle.x, particle.y);
                    this.ctx.lineTo(other.x, other.y);
                    this.ctx.strokeStyle = `rgba(0, 212, 170, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        });

        requestAnimationFrame(() => this.animate());
    }
}

// Initialize particle system when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('particles-canvas')) {
        window.particleSystem = new ParticleSystem('particles-canvas');
    }
});
