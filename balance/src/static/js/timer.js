// Balance Timer - Server-Driven Timer with Visibility Sync
// Key patterns:
// 1. Server is source of truth (end_timestamp, not countdown)
// 2. Calculate remaining = endTimestamp - adjustedNow
// 3. Page Visibility API resyncs when tab becomes visible
// 4. No local state survives reload - always fetch from server

const Balance = {
  // Server sync state
  serverTimeDiff: 0,  // Offset between server and client clocks
  endTimestamp: null, // Unix timestamp when timer ends
  totalDuration: 0,   // Total duration for progress calculation

  // UI state
  currentPage: 'home',
  sessionType: 'expected',
  intention: '',
  tickInterval: null,

  // Priority state
  priorities: [],
  selectedPriorityId: null,

  // Session data from server
  currentSession: null,

  // Session end state
  selectedDistractions: null,
  selectedDidThing: null,

  // Rabbit hole state
  showRabbitHolePrompt: false,
  consecutivePersonalCount: 0,
  selectedRabbitHole: null,

  // Today's stats
  todaySessions: { expected: 0, personal: 0 },
  dailyCap: 10,

  // DOM elements
  el: {},

  async init() {
    // Only initialize if timer page elements exist
    if (!document.getElementById('page-home')) return;

    this.cacheElements();
    this.bindEvents();
    this.setupVisibilityHandler();

    // Immediately fetch server state (no flash of wrong time)
    await this.syncWithServer();
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
    this.el.typeBtns = document.querySelectorAll('.type-selection .btn--option');
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
    this.el.rabbitHoleGroup = document.getElementById('rabbit-hole-group');
    this.el.rabbitHoleOptions = document.getElementById('rabbit-hole-options');
    this.el.continueBtn = document.getElementById('continue-btn');
    this.el.endExpected = document.getElementById('end-expected');
    this.el.endPersonal = document.getElementById('end-personal');
    this.el.endBreakTime = document.getElementById('end-break-time');

    // Break page
    this.el.breakTime = document.getElementById('break-time');
    this.el.breakProgress = document.getElementById('break-progress');

    // Priority dropdown
    this.el.prioritySection = document.getElementById('priority-section');
    this.el.priorityTrigger = document.getElementById('priority-trigger');
    this.el.priorityLabel = document.getElementById('priority-label');
    this.el.priorityDropdown = document.getElementById('dropdown-priority');
  },

  bindEvents() {
    // Type selection
    this.el.typeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.typeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.sessionType = btn.dataset.type;

        // Show/hide priority section
        if (this.sessionType === 'expected' && this.priorities.length > 0) {
          this.el.prioritySection.style.display = 'block';
          // Reset priority selection
          this.selectedPriorityId = null;
          this.el.priorityLabel.textContent = 'Select...';
          this.el.priorityTrigger.classList.remove('selected');
        } else {
          this.el.prioritySection.style.display = 'none';
          this.selectedPriorityId = null;
        }
        this.updateStartButton();
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
    this.el.distractionOptions.querySelectorAll('.btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.distractionOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.selectedDistractions = btn.dataset.value;
        this.checkEndComplete();
      });
    });

    // Did the thing options
    this.el.didThingOptions.querySelectorAll('.btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.didThingOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.selectedDidThing = btn.dataset.value === 'yes';
        this.checkEndComplete();
      });
    });

    // Rabbit hole options
    this.el.rabbitHoleOptions?.querySelectorAll('.btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        this.el.rabbitHoleOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.selectedRabbitHole = btn.dataset.value === 'yes';
        this.checkEndComplete();
      });
    });

    // Continue to break
    this.el.continueBtn.addEventListener('click', () => this.endSession());

    // Quick actions
    document.getElementById('quick-meditation')?.addEventListener('click', () => this.quickLog('meditation'));
    document.getElementById('quick-exercise')?.addEventListener('click', () => this.quickLog('exercise'));
  },

  setupVisibilityHandler() {
    // Resync with server when tab becomes visible
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        console.log('Tab visible - resyncing with server');
        this.syncWithServer();
      }
    });
  },

  async syncWithServer() {
    try {
      const response = await fetch('/api/status');
      const status = await response.json();

      // Calculate server-client time difference
      const clientNow = Date.now() / 1000;
      this.serverTimeDiff = status.server_timestamp - clientNow;

      // Store timing data
      this.endTimestamp = status.end_timestamp;
      this.totalDuration = status.total_duration;

      // Handle different modes
      switch (status.mode) {
        case 'idle':
          this.stopTick();
          await this.loadTodaySessions();
          this.updateProgressDots();
          this.el.homeTime.textContent = this.formatTime(status.remaining_seconds);
          this.showPage('home');
          break;

        case 'session':
          this.currentSession = status.session;
          this.sessionType = status.session.type;
          this.intention = status.session.intention || '';
          this.showPage('active');
          this.updateActiveUI();
          this.startTick();
          break;

        case 'session_ended':
          // Break is running, questionnaire pending
          this.currentSession = status.session;
          this.sessionType = status.session.type;
          this.intention = status.session.intention || '';

          // Check rabbit hole for personal sessions
          if (this.sessionType === 'personal') {
            await this.checkRabbitHole();
          }

          this.showPage('end');
          this.updateEndUI();
          this.startTick(); // Continue ticking for break countdown
          break;

        case 'break':
          this.showPage('break');
          this.startTick();
          break;
      }

      // Load settings for dailyCap
      await this.loadSettings();

      // Load priorities
      await this.loadPriorities();

    } catch (err) {
      console.error('Failed to sync with server:', err);
    }
  },

  async loadSettings() {
    try {
      const settings = await fetch('/api/settings').then(r => r.json());
      this.dailyCap = settings.daily_cap;
      if (this.el.sessionCap) {
        this.el.sessionCap.textContent = this.dailyCap;
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  },

  async loadPriorities() {
    try {
      const response = await fetch('/api/priorities');
      this.priorities = await response.json();
      this.renderPriorityDropdown();

      // Show priority section if Expected is already selected
      if (this.sessionType === 'expected' && this.priorities.length > 0 && this.el.prioritySection) {
        this.el.prioritySection.style.display = 'block';
        this.updateStartButton();
      }
    } catch (err) {
      console.error('Failed to load priorities:', err);
    }
  },

  renderPriorityDropdown() {
    if (!this.el.priorityDropdown) return;
    this.el.priorityDropdown.innerHTML = this.priorities.map(p => `
      <button type="button" class="dropdown__item dropdown__item--with-meta" onclick="Balance.selectPriority(${p.id}, '${p.name.replace(/'/g, "\\'")}')">
        <span>${p.name}</span>
        <span class="dropdown__item-meta">#${p.rank}</span>
      </button>
    `).join('');
  },

  togglePriorityDropdown() {
    const dropdown = this.el.priorityDropdown;
    const backdrop = document.getElementById('backdrop-priority');
    if (dropdown.classList.contains('dropdown__menu--open')) {
      dropdown.classList.remove('dropdown__menu--open');
      backdrop.classList.remove('active');
    } else {
      dropdown.classList.add('dropdown__menu--open');
      backdrop.classList.add('active');
    }
  },

  closePriorityDropdown() {
    this.el.priorityDropdown?.classList.remove('dropdown__menu--open');
    document.getElementById('backdrop-priority')?.classList.remove('active');
  },

  selectPriority(id, name) {
    this.selectedPriorityId = id;
    this.el.priorityLabel.textContent = name;
    this.el.priorityTrigger.classList.add('selected');
    this.closePriorityDropdown();
    this.updateStartButton();
  },

  updateStartButton() {
    if (this.sessionType === 'expected' && this.priorities.length > 0) {
      this.el.startBtn.disabled = !this.selectedPriorityId;
    } else {
      this.el.startBtn.disabled = false;
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
        this.el.headerNav?.classList.remove('hidden');
        this.el.bottomNav?.classList.remove('hidden');
        break;
      case 'active':
        this.el.pageActive.classList.add('active');
        this.el.headerNav?.classList.add('hidden');
        this.el.bottomNav?.classList.add('hidden');
        document.body.classList.add('dark-mode');
        break;
      case 'end':
        this.el.pageEnd.classList.add('active');
        this.el.headerNav?.classList.add('hidden');
        this.el.bottomNav?.classList.add('hidden');
        break;
      case 'break':
        this.el.pageBreak.classList.add('active');
        this.el.headerNav?.classList.add('hidden');
        this.el.bottomNav?.classList.add('hidden');
        document.body.classList.add('break-mode');
        break;
    }
  },

  updateActiveUI() {
    this.el.activeType.textContent = this.sessionType.charAt(0).toUpperCase() + this.sessionType.slice(1);
    this.el.activeIntention.textContent = this.intention || '-';

    // Calculate remaining time from server timestamp
    const remaining = this.calculateRemainingSeconds();
    this.el.activeTime.textContent = this.formatTime(remaining);

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
    this.el.distractionOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
    this.el.didThingOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));

    // Show rabbit hole prompt if needed
    if (this.showRabbitHolePrompt && this.el.rabbitHoleGroup) {
      this.el.rabbitHoleGroup.style.display = 'block';
      this.selectedRabbitHole = null;
      this.el.rabbitHoleOptions?.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
    } else if (this.el.rabbitHoleGroup) {
      this.el.rabbitHoleGroup.style.display = 'none';
      this.selectedRabbitHole = false; // Not needed, auto-pass
    }
  },

  checkEndComplete() {
    const baseComplete = this.selectedDistractions && this.selectedDidThing !== null;
    const rabbitHoleComplete = !this.showRabbitHolePrompt || this.selectedRabbitHole !== null;
    this.el.continueBtn.disabled = !(baseComplete && rabbitHoleComplete);
  },

  // Calculate remaining seconds using server-adjusted time
  calculateRemainingSeconds() {
    if (!this.endTimestamp) return 0;
    const adjustedNow = (Date.now() / 1000) + this.serverTimeDiff;
    return Math.max(0, Math.ceil(this.endTimestamp - adjustedNow));
  },

  // Start the display tick - updates every 100ms for smooth countdown
  startTick() {
    this.stopTick();

    const circumference = 2 * Math.PI * 90;

    this.tickInterval = setInterval(() => {
      const remaining = this.calculateRemainingSeconds();

      if (this.currentPage === 'active') {
        // Update session timer
        this.el.activeTime.textContent = this.formatTime(remaining);

        // Update progress ring
        const elapsed = this.totalDuration - remaining;
        const progress = elapsed / this.totalDuration;
        const offset = circumference * (1 - progress);
        this.el.progressCircle.style.strokeDashoffset = offset;

        // Timer complete - call timer-complete endpoint
        if (remaining <= 0) {
          this.stopTick();
          this.timerComplete();
        }
      } else if (this.currentPage === 'end') {
        // Update break countdown on end screen
        if (this.el.endBreakTime) {
          this.el.endBreakTime.textContent = this.formatTime(remaining);
        }

        // When break ends on end screen, show "Break complete"
        if (remaining <= 0) {
          if (this.el.endBreakTime) {
            this.el.endBreakTime.textContent = 'Break complete';
          }
        }
      } else if (this.currentPage === 'break') {
        // Update break timer
        this.el.breakTime.textContent = this.formatTime(remaining);

        // Update progress bar
        const elapsed = this.totalDuration - remaining;
        const progress = (elapsed / this.totalDuration) * 100;
        this.el.breakProgress.style.width = `${progress}%`;

        // Break complete - return to home
        if (remaining <= 0) {
          this.stopTick();
          this.syncWithServer(); // Refresh full state
        }
      }
    }, 100); // Update frequently for smooth display
  },

  stopTick() {
    if (this.tickInterval) {
      clearInterval(this.tickInterval);
      this.tickInterval = null;
    }
  },

  async startSession() {
    try {
      const response = await fetch('/api/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: this.sessionType,
          intention: this.intention || null,
          priority_id: this.sessionType === 'expected' ? this.selectedPriorityId : null
        })
      });

      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || 'Cannot start session');
        return;
      }

      // Sync with server to get correct end_timestamp
      await this.syncWithServer();

    } catch (err) {
      console.error('Failed to start session:', err);
      alert('Failed to start session');
    }
  },

  async abandonSession() {
    if (!confirm('Abandon this session?')) return;

    try {
      this.stopTick();
      await fetch('/api/sessions/abandon', { method: 'POST' });

      // Reset form
      this.intention = '';
      this.el.intentionInput.value = '';
      this.el.charCount.textContent = '0';

      // Sync with server
      await this.syncWithServer();

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
          did_the_thing: this.selectedDidThing,
          rabbit_hole: this.selectedRabbitHole || false
        })
      });

      if (!response.ok) {
        alert('Failed to end session');
        return;
      }

      // Update session counts
      this.todaySessions[this.sessionType]++;

      // Reset form for next session
      this.intention = '';
      this.el.intentionInput.value = '';
      this.el.charCount.textContent = '0';

      // Sync with server to get break timing
      await this.syncWithServer();

    } catch (err) {
      console.error('Failed to end session:', err);
    }
  },

  async timerComplete() {
    try {
      const response = await fetch('/api/sessions/timer-complete', {
        method: 'POST'
      });

      if (!response.ok) {
        console.error('Failed to complete timer');
        return;
      }

      const data = await response.json();

      // Update break timing
      this.endTimestamp = new Date(data.break_until).getTime() / 1000;
      this.totalDuration = data.break_duration * 60;

      // Check for rabbit hole if personal session
      if (this.sessionType === 'personal') {
        await this.checkRabbitHole();
      }

      // Show end page (questionnaire) with break running
      this.showPage('end');
      this.updateEndUI();
      this.startTick(); // Continue ticking for break countdown

    } catch (err) {
      console.error('Timer complete error:', err);
    }
  },

  async checkRabbitHole() {
    try {
      const response = await fetch('/api/sessions/rabbit-hole-check');
      const data = await response.json();

      this.showRabbitHolePrompt = data.should_alert;
      this.consecutivePersonalCount = data.consecutive_count;
    } catch (err) {
      console.error('Rabbit hole check error:', err);
      this.showRabbitHolePrompt = false;
    }
  },

  formatTime(seconds) {
    if (seconds < 0) seconds = 0;
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
