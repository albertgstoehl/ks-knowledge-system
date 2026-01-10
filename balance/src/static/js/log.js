// Balance Log Page
const LogPage = {
  meditationTimeOfDay: null,
  exerciseType: 'cardio',
  exerciseIntensity: 'medium',

  init() {
    // Only initialize if log page elements exist
    if (!document.getElementById('meditation-form')) return;
    this.bindEvents();
    this.loadWeekSummary();
  },

  bindEvents() {
    // Tab switching
    document.querySelectorAll('.log-tabs .btn--option').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.log-tabs .btn--option').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.log-form').forEach(f => f.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab + '-form').classList.add('active');
      });
    });

    // Quick duration buttons
    document.querySelectorAll('.quick-durations').forEach(group => {
      group.querySelectorAll('.btn--option').forEach(btn => {
        btn.addEventListener('click', () => {
          group.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          group.closest('.form-group').querySelector('input').value = btn.dataset.value;
        });
      });
    });

    // Exercise type selection
    document.querySelectorAll('.type-options .btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.type-options .btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.exerciseType = btn.dataset.value;
      });
    });

    // Intensity selection
    document.querySelectorAll('.intensity-options .btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.intensity-options .btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.exerciseIntensity = btn.dataset.value;
      });
    });

    // Time override toggle
    document.querySelectorAll('.time-override-toggle').forEach(toggle => {
      toggle.addEventListener('click', () => {
        const options = toggle.nextElementSibling;
        options.classList.toggle('visible');
      });
    });

    // Time of day selection (meditation)
    document.querySelectorAll('#meditation-time-options .btn--option').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#meditation-time-options .btn--option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.meditationTimeOfDay = btn.dataset.value;
      });
    });

    // Form submissions
    document.getElementById('meditation-form').addEventListener('submit', (e) => this.submitMeditation(e));
    document.getElementById('exercise-form').addEventListener('submit', (e) => this.submitExercise(e));
  },

  async submitMeditation(e) {
    e.preventDefault();
    const duration = parseInt(document.getElementById('meditation-duration').value);

    try {
      const body = {
        duration_minutes: duration
      };
      if (this.meditationTimeOfDay) {
        body.time_of_day = this.meditationTimeOfDay;
      }

      const response = await fetch('/api/meditation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        this.showSuccess('Meditation logged');
        this.loadWeekSummary();
        this.resetMeditationForm();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to log meditation');
      }
    } catch (err) {
      console.error('Failed to log meditation:', err);
      alert('Failed to log meditation');
    }
  },

  async submitExercise(e) {
    e.preventDefault();
    const duration = parseInt(document.getElementById('exercise-duration').value);

    try {
      const response = await fetch('/api/exercise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: this.exerciseType,
          duration_minutes: duration,
          intensity: this.exerciseIntensity
        })
      });

      if (response.ok) {
        this.showSuccess('Exercise logged');
        this.loadWeekSummary();
        this.resetExerciseForm();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to log exercise');
      }
    } catch (err) {
      console.error('Failed to log exercise:', err);
      alert('Failed to log exercise');
    }
  },

  resetMeditationForm() {
    document.getElementById('meditation-duration').value = '10';
    document.querySelectorAll('#meditation-form .quick-durations .btn--option').forEach(b => b.classList.remove('selected'));
    document.querySelector('#meditation-form .quick-durations .btn--option[data-value="10"]').classList.add('selected');
    document.querySelectorAll('#meditation-time-options .btn--option').forEach(b => b.classList.remove('selected'));
    document.getElementById('meditation-time-options').classList.remove('visible');
    this.meditationTimeOfDay = null;
  },

  resetExerciseForm() {
    document.getElementById('exercise-duration').value = '30';
    document.querySelectorAll('#exercise-form .quick-durations .btn--option').forEach(b => b.classList.remove('selected'));
    document.querySelector('#exercise-form .quick-durations .btn--option[data-value="30"]').classList.add('selected');
    document.querySelectorAll('.type-options .btn--option').forEach(b => b.classList.remove('selected'));
    document.querySelector('.type-options .btn--option[data-value="cardio"]').classList.add('selected');
    document.querySelectorAll('.intensity-options .btn--option').forEach(b => b.classList.remove('selected'));
    document.querySelector('.intensity-options .btn--option[data-value="medium"]').classList.add('selected');
    this.exerciseType = 'cardio';
    this.exerciseIntensity = 'medium';
  },

  async loadWeekSummary() {
    try {
      const response = await fetch('/api/stats/week');
      if (response.ok) {
        const stats = await response.json();
        document.getElementById('meditation-summary').textContent =
          `${stats.meditation_count || 0} sessions · ${stats.meditation_minutes || 0} min`;
        document.getElementById('exercise-summary').textContent =
          `${stats.exercise_count || 0} sessions · ${stats.exercise_minutes || 0} min`;
      }
    } catch (err) {
      console.error('Failed to load week summary:', err);
    }
  },

  showSuccess(message) {
    // Simple success feedback - could be enhanced with a toast
    const btn = document.querySelector('.log-form.active .btn--primary');
    const originalText = btn.textContent;
    btn.textContent = message;
    btn.style.background = '#090';
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.background = '';
    }, 1500);
  }
};

document.addEventListener('DOMContentLoaded', () => LogPage.init());
