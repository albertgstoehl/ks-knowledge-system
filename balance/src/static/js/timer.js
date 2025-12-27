// Balance Timer - Single Page Application
const Balance = {
  // State
  currentPage: 'home',
  sessionType: 'expected',
  intention: '',
  sessionDuration: 25 * 60,  // seconds
  shortBreak: 5 * 60,
  longBreak: 15 * 60,
  timeRemaining: 25 * 60,
  breakRemaining: 0,
  timerInterval: null,
  breakInterval: null,
  dailyCap: 10,
  todaySessions: { expected: 0, personal: 0 },

  // Session end state
  selectedDistractions: null,
  selectedDidThing: null,

  // DOM elements
  el: {},

  init() {
    this.cacheElements();
    this.bindEvents();
    this.checkCurrentState();
  },

  cacheElements() {
    // Pages
    this.el.pageHome = document.getElementById('page-home');
    this.el.pageActive = document.getElementById('page-active');
    this.el.pageEnd = document.getElementById('page-end');
    this.el.pageBreak = document.getElementById('page-break');
    this.el.headerNav = document.querySelector('.header-nav');
    this.el.bottomNav = document.querySelector('.bottom-nav');

    // Home page
    this.el.homeStatus = document.getElementById('home-status');
    this.el.homeTime = document.getElementById('home-time');
    this.el.typeBtns = document.querySelectorAll('.type-btn');
    this.el.intentionInput = document.getElementById('intention-input');
    this.el.charCount = document.getElementById('char-count');
    this.el.startBtn = document.getElementById('start-btn');
    this.el.expectedDots = document.getElementById('expected-dots');
    this.el.personalDots = document.getElementById('personal-dots');

    // Active page
    this.el.activeType = document.getElementById('active-type');
    this.el.activeTime = document.getElementById('active-time');
    this.el.activeIntention = document.getElementById('active-intention');
    this.el.progressCircle = document.getElementById('progress-circle');
    this.el.sessionNum = document.getElementById('session-num');
    this.el.sessionCap = document.getElementById('session-cap');
    this.el.abandonBtn = document.getElementById('abandon-btn');

    // End page
    this.el.endIntention = document.getElementById('end-intention');
    this.el.distractionOptions = document.getElementById('distraction-options');
    this.el.didThingOptions = document.getElementById('did-thing-options');
    this.el.continueBtn = document.getElementById('continue-btn');
    this.el.endExpected = document.getElementById('end-expected');
    this.el.endPersonal = document.getElementById('end-personal');

    // Break page
    this.el.breakTime = document.getElementById('break-time');
    this.el.breakProgress = document.getElementById('break-progress');
  },

  bindEvents() {
    // Type selection
    this.el.typeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.typeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.sessionType = btn.dataset.type;
      });
    });

    // Intention input
    this.el.intentionInput.addEventListener('input', (e) => {
      this.intention = e.target.value;
      this.el.charCount.textContent = e.target.value.length;
    });

    // Start session
    this.el.startBtn.addEventListener('click', () => this.startSession());

    // Abandon session
    this.el.abandonBtn.addEventListener('click', () => this.abandonSession());

    // Distraction options
    this.el.distractionOptions.querySelectorAll('.option-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.distractionOptions.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.selectedDistractions = btn.dataset.value;
        this.checkEndComplete();
      });
    });

    // Did the thing options
    this.el.didThingOptions.querySelectorAll('.binary-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.didThingOptions.querySelectorAll('.binary-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.selectedDidThing = btn.dataset.value === 'yes';
        this.checkEndComplete();
      });
    });

    // Continue to break
    this.el.continueBtn.addEventListener('click', () => this.endSession());

    // Quick actions
    document.getElementById('quick-meditation')?.addEventListener('click', () => this.quickLog('meditation'));
    document.getElementById('quick-exercise')?.addEventListener('click', () => this.quickLog('exercise'));
  },

  async checkCurrentState() {
    try {
      // Check if on break
      const breakCheck = await fetch('/api/check').then(r => r.json());
      if (breakCheck.on_break) {
        this.breakRemaining = breakCheck.remaining_seconds;
        this.showPage('break');
        this.startBreakTimer();
        return;
      }

      // Check for active session
      const current = await fetch('/api/sessions/current').then(r => r.json());
      if (current.active) {
        // Resume session
        const session = current.session;
        this.sessionType = session.type;
        this.intention = session.intention || '';

        // Calculate remaining time
        const startedAt = new Date(session.started_at);
        const elapsed = Math.floor((Date.now() - startedAt.getTime()) / 1000);
        this.timeRemaining = Math.max(0, this.sessionDuration - elapsed);

        if (this.timeRemaining > 0) {
          this.showPage('active');
          this.startTimer();
        } else {
          // Timer expired while away
          this.showPage('end');
        }
        return;
      }

      // Load settings and today's sessions
      await this.loadSettings();
      await this.loadTodaySessions();
      this.updateProgressDots();

    } catch (err) {
      console.error('Failed to check state:', err);
    }
  },

  async loadSettings() {
    try {
      const settings = await fetch('/api/settings').then(r => r.json());
      this.sessionDuration = settings.session_duration * 60;
      this.shortBreak = settings.short_break * 60;
      this.longBreak = settings.long_break * 60;
      this.dailyCap = settings.daily_cap;
      this.timeRemaining = this.sessionDuration;
      this.el.homeTime.textContent = this.formatTime(this.sessionDuration);
      this.el.sessionCap.textContent = this.dailyCap;
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  },

  async loadTodaySessions() {
    try {
      const sessions = await fetch('/api/sessions/today').then(r => r.json());
      this.todaySessions = { expected: 0, personal: 0 };
      sessions.forEach(s => {
        if (s.ended_at) {
          this.todaySessions[s.type]++;
        }
      });
    } catch (err) {
      console.error('Failed to load today sessions:', err);
    }
  },

  updateProgressDots() {
    const maxDots = 5;

    // Expected dots
    this.el.expectedDots.innerHTML = '';
    for (let i = 0; i < maxDots; i++) {
      const dot = document.createElement('div');
      dot.className = 'dot' + (i < this.todaySessions.expected ? ' filled' : '');
      this.el.expectedDots.appendChild(dot);
    }

    // Personal dots
    this.el.personalDots.innerHTML = '';
    for (let i = 0; i < maxDots; i++) {
      const dot = document.createElement('div');
      dot.className = 'dot' + (i < this.todaySessions.personal ? ' filled' : '');
      this.el.personalDots.appendChild(dot);
    }
  },

  showPage(page) {
    this.currentPage = page;

    // Hide all pages
    this.el.pageHome.classList.remove('active');
    this.el.pageActive.classList.remove('active');
    this.el.pageEnd.classList.remove('active');
    this.el.pageBreak.classList.remove('active');

    // Reset body classes
    document.body.classList.remove('dark-mode', 'break-mode');

    // Show target page
    switch (page) {
      case 'home':
        this.el.pageHome.classList.add('active');
        this.el.headerNav.classList.remove('hidden');
        this.el.bottomNav.classList.remove('hidden');
        break;
      case 'active':
        this.el.pageActive.classList.add('active');
        this.el.headerNav.classList.add('hidden');
        this.el.bottomNav.classList.add('hidden');
        document.body.classList.add('dark-mode');
        this.updateActiveUI();
        break;
      case 'end':
        this.el.pageEnd.classList.add('active');
        this.el.headerNav.classList.add('hidden');
        this.el.bottomNav.classList.add('hidden');
        this.updateEndUI();
        break;
      case 'break':
        this.el.pageBreak.classList.add('active');
        this.el.headerNav.classList.add('hidden');
        this.el.bottomNav.classList.add('hidden');
        document.body.classList.add('break-mode');
        break;
    }
  },

  updateActiveUI() {
    this.el.activeType.textContent = this.sessionType.charAt(0).toUpperCase() + this.sessionType.slice(1);
    this.el.activeIntention.textContent = this.intention || '-';
    this.el.activeTime.textContent = this.formatTime(this.timeRemaining);

    const totalSessions = this.todaySessions.expected + this.todaySessions.personal + 1;
    this.el.sessionNum.textContent = totalSessions;
  },

  updateEndUI() {
    this.el.endIntention.textContent = `"${this.intention || '-'}"`;
    this.el.endExpected.textContent = `${this.todaySessions.expected} Expected`;
    this.el.endPersonal.textContent = `${this.todaySessions.personal} Personal`;

    // Reset selections
    this.selectedDistractions = null;
    this.selectedDidThing = null;
    this.el.continueBtn.disabled = true;
    this.el.distractionOptions.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
    this.el.didThingOptions.querySelectorAll('.binary-btn').forEach(b => b.classList.remove('active'));
  },

  checkEndComplete() {
    this.el.continueBtn.disabled = !(this.selectedDistractions && this.selectedDidThing !== null);
  },

  async startSession() {
    try {
      const response = await fetch('/api/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: this.sessionType,
          intention: this.intention || null
        })
      });

      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || 'Cannot start session');
        return;
      }

      this.timeRemaining = this.sessionDuration;
      this.showPage('active');
      this.startTimer();

    } catch (err) {
      console.error('Failed to start session:', err);
      alert('Failed to start session');
    }
  },

  startTimer() {
    const circumference = 2 * Math.PI * 90;

    this.timerInterval = setInterval(() => {
      this.timeRemaining--;

      // Update display
      this.el.activeTime.textContent = this.formatTime(this.timeRemaining);

      // Update progress ring
      const progress = 1 - (this.timeRemaining / this.sessionDuration);
      const offset = circumference * (1 - progress);
      this.el.progressCircle.style.strokeDashoffset = offset;

      // Timer complete
      if (this.timeRemaining <= 0) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
        this.showPage('end');
      }
    }, 1000);
  },

  async abandonSession() {
    if (!confirm('Abandon this session?')) return;

    try {
      clearInterval(this.timerInterval);
      this.timerInterval = null;

      await fetch('/api/sessions/abandon', { method: 'POST' });

      await this.loadTodaySessions();
      this.updateProgressDots();
      this.resetForm();
      this.showPage('home');

    } catch (err) {
      console.error('Failed to abandon session:', err);
    }
  },

  async endSession() {
    try {
      const response = await fetch('/api/sessions/end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          distractions: this.selectedDistractions,
          did_the_thing: this.selectedDidThing
        })
      });

      if (!response.ok) {
        alert('Failed to end session');
        return;
      }

      // Get break duration from API
      const breakCheck = await fetch('/api/check').then(r => r.json());
      this.breakRemaining = breakCheck.remaining_seconds;

      // Update session counts
      this.todaySessions[this.sessionType]++;

      this.showPage('break');
      this.startBreakTimer();

    } catch (err) {
      console.error('Failed to end session:', err);
    }
  },

  startBreakTimer() {
    const totalBreak = this.breakRemaining;

    this.breakInterval = setInterval(async () => {
      this.breakRemaining--;

      // Update display
      this.el.breakTime.textContent = this.formatTime(this.breakRemaining);

      // Update progress bar
      const progress = 1 - (this.breakRemaining / totalBreak);
      this.el.breakProgress.style.width = `${progress * 100}%`;

      // Break complete
      if (this.breakRemaining <= 0) {
        clearInterval(this.breakInterval);
        this.breakInterval = null;

        await this.loadTodaySessions();
        this.updateProgressDots();
        this.resetForm();
        this.showPage('home');
      }
    }, 1000);
  },

  resetForm() {
    this.intention = '';
    this.el.intentionInput.value = '';
    this.el.charCount.textContent = '0';
    this.timeRemaining = this.sessionDuration;
    this.el.homeTime.textContent = this.formatTime(this.sessionDuration);
  },

  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  },

  async quickLog(type) {
    const duration = prompt(`${type === 'meditation' ? 'Meditation' : 'Exercise'} duration (minutes):`, '10');
    if (!duration) return;

    try {
      let body;
      let endpoint;

      if (type === 'meditation') {
        endpoint = '/api/meditation';
        body = { duration_minutes: parseInt(duration) };
      } else {
        const exerciseType = confirm('Cardio? (Cancel for Strength)') ? 'cardio' : 'strength';
        endpoint = '/api/exercise';
        body = {
          type: exerciseType,
          duration_minutes: parseInt(duration),
          intensity: 'medium'
        };
      }

      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      alert(`${type.charAt(0).toUpperCase() + type.slice(1)} logged!`);
    } catch (err) {
      console.error('Failed to log:', err);
    }
  }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => Balance.init());
