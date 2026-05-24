/* ============================================
   SmartQueue AI - Main JavaScript
   Shared utilities and functions
   ============================================ */

// Global namespace
window.SmartQueue = window.SmartQueue || {};

// ============================================
// DOM Ready Handler
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  SmartQueue.init();
});

// ============================================
// Initialization
// ============================================
SmartQueue.init = function () {
  this.initNavbar();
  this.initScrollReveal();
  this.initAnimatedCounters();
  this.initMobileMenu();
  this.initSmoothScroll();
};

// ============================================
// Navbar Functionality
// ============================================
SmartQueue.initNavbar = function () {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    // Add/remove scrolled class
    if (currentScroll > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }

    // Hide/show on scroll direction
    if (currentScroll > lastScroll && currentScroll > 200) {
      navbar.style.transform = 'translateY(-100%)';
    } else {
      navbar.style.transform = 'translateY(0)';
    }

    lastScroll = currentScroll;
  });
};

// ============================================
// Mobile Menu
// ============================================
SmartQueue.initMobileMenu = function () {
  const toggle = document.querySelector('.navbar-toggle');
  const nav = document.querySelector('.navbar-nav');

  if (!toggle || !nav) return;

  toggle.addEventListener('click', () => {
    nav.classList.toggle('active');
    toggle.classList.toggle('active');
  });

  // Close menu when clicking a link
  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      nav.classList.remove('active');
      toggle.classList.remove('active');
    });
  });
};

// ============================================
// Scroll Reveal Animation
// ============================================
SmartQueue.initScrollReveal = function () {
  const reveals = document.querySelectorAll('.reveal, .reveal-stagger');

  if (reveals.length === 0) return;

  const revealOnScroll = () => {
    reveals.forEach(element => {
      const windowHeight = window.innerHeight;
      const elementTop = element.getBoundingClientRect().top;
      const revealPoint = 150;

      if (elementTop < windowHeight - revealPoint) {
        element.classList.add('revealed');
      }
    });
  };

  window.addEventListener('scroll', revealOnScroll);
  revealOnScroll(); // Check on load
};

// ============================================
// Animated Counter
// ============================================
SmartQueue.initAnimatedCounters = function () {
  const counters = document.querySelectorAll('[data-count]');

  if (counters.length === 0) return;

  const animateCounter = (element) => {
    const target = parseInt(element.dataset.count);
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;

    const updateCounter = () => {
      current += step;
      if (current < target) {
        element.textContent = Math.floor(current) + (element.dataset.suffix || '');
        requestAnimationFrame(updateCounter);
      } else {
        element.textContent = target + (element.dataset.suffix || '');
      }
    };

    updateCounter();
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(counter => observer.observe(counter));
};

// ============================================
// Smooth Scroll
// ============================================
SmartQueue.initSmoothScroll = function () {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
};

// ============================================
// Notification System
// ============================================
SmartQueue.showNotification = function (title, message, type = 'success') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <div class="notification-title">${title}</div>
    <p class="notification-message">${message}</p>
  `;

  document.body.appendChild(notification);

  // Trigger animation
  setTimeout(() => notification.classList.add('show'), 100);

  // Auto remove
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 500);
  }, 4000);
};

// ============================================
// Local Storage Helpers
// ============================================
SmartQueue.storage = {
  set: function (key, value) {
    localStorage.setItem(`smartqueue_${key}`, JSON.stringify(value));
  },

  get: function (key) {
    const item = localStorage.getItem(`smartqueue_${key}`);
    return item ? JSON.parse(item) : null;
  },

  remove: function (key) {
    localStorage.removeItem(`smartqueue_${key}`);
  },

  clear: function () {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('smartqueue_')) {
        localStorage.removeItem(key);
      }
    });
  }
};

// ============================================
// Utility Functions
// ============================================
SmartQueue.utils = {
  // Format time in minutes to readable string
  formatTime: function (minutes) {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  },

  // Generate clean queue number
  generateTokenId: function (prefix = 'T') {
    // Get today's date as a seed for sequential numbering
    const today = new Date().toDateString();
    const storageKey = `queue_counter_${prefix}_${today}`;

    // Get current counter from sessionStorage (resets per session/day)
    let counter = parseInt(sessionStorage.getItem(storageKey) || '0') + 1;
    sessionStorage.setItem(storageKey, counter.toString());

    // Format as 3-digit number with leading zeros
    const num = counter.toString().padStart(3, '0');
    return `${prefix}-${num}`;
  },

  // Get current time formatted
  getCurrentTime: function () {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  // Debounce function
  debounce: function (func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Throttle function
  throttle: function (func, limit) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};

// ============================================
// Form Validation
// ============================================
SmartQueue.validateForm = function (formElement) {
  const inputs = formElement.querySelectorAll('[required]');
  let isValid = true;

  inputs.forEach(input => {
    const value = input.value.trim();
    const errorElement = input.parentElement.querySelector('.form-error');

    if (!value) {
      isValid = false;
      input.classList.add('error');
      if (errorElement) errorElement.style.display = 'block';
    } else {
      input.classList.remove('error');
      if (errorElement) errorElement.style.display = 'none';
    }

    // Phone validation
    if (input.type === 'tel' && value) {
      const phoneRegex = /^[0-9]{10}$/;
      if (!phoneRegex.test(value.replace(/\D/g, ''))) {
        isValid = false;
        input.classList.add('error');
      }
    }
  });

  return isValid;
};

// ============================================
// Page Navigation with Transition
// ============================================
SmartQueue.navigateTo = function (url) {
  document.body.classList.add('page-exit');
  setTimeout(() => {
    window.location.href = url;
  }, 300);
};

console.log('🚀 SmartQueue AI initialized');
// ============================================
// 🔥 TOKEN GENERATION + BACKEND CONNECTION
// ============================================

SmartQueue.generateToken = async function (formData) {
  try {
    const response = await fetch("http://127.0.0.1:8000/generate-token/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(formData)
    });

    if (!response.ok) {
      throw new Error("Server error while generating token");
    }

    const data = await response.json();

    console.log("✅ Backend Response:", data);

    SmartQueue.showNotification(
      "Token Generated",
      "Your token has been successfully created!",
      "success"
    );

  } catch (error) {
    console.error("❌ Error:", error);

    SmartQueue.showNotification(
      "Connection Failed",
      "Unable to connect to backend server.",
      "error"
    );
  }
};


// ============================================
// 📝 FORM SUBMIT HANDLER
// ============================================

document.addEventListener("DOMContentLoaded", function () {

  const form = document.getElementById("tokenForm");

  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    if (!SmartQueue.validateForm(form)) {
      SmartQueue.showNotification(
        "Validation Error",
        "Please fill all required fields correctly.",
        "error"
      );
      return;
    }

    const formData = {
      queue_id: 1,
      domain: "healthcare",
      symptoms: form.querySelector('[name="symptoms"]').value,
      consultation_type: form.querySelector('[name="consultation_type"]').value,
      service_required: form.querySelector('[name="service_required"]').value
    };

    console.log("📤 Sending Data:", formData);

    SmartQueue.generateToken(formData);
  });

});