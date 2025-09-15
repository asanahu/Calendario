/* Shared date-range calendar initializer for add-vacation, add-recurring, and asignar-estados.
 * Behavior:
 * - Two-click range selection across months (click start, navigate, click end).
 * - Persist selection state on month navigation and page interactions.
 * - Background highlight of the selected range.
 * - Disables submit until both dates are selected.
 */

window.initializeDateRangeCalendar = function initDateRangeCalendar(opts) {
  const {
    calendarId = 'dateRangeCalendar',
    startInputId = 'fecha_inicio',
    endInputId = 'fecha_fin',
    infoContainerId = 'dateRangeInfo',
    infoTextId = 'rangeText',
    submitSelector = 'button[type="submit"]',
  } = opts || {};

  let startDate = null; // YYYY-MM-DD
  let endDate = null;   // YYYY-MM-DD

  const calendarEl = document.getElementById(calendarId);
  const rangeInfoEl = document.getElementById(infoContainerId);
  const rangeTextEl = document.getElementById(infoTextId);
  const fechaInicioInput = document.getElementById(startInputId);
  const fechaFinInput = document.getElementById(endInputId);
  const submitBtn = document.querySelector(submitSelector);

  // Utility helpers
  function fmt(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }
  function addDays(dateStr, days) {
    const d = new Date(dateStr + 'T00:00:00');
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
  }
  function updateSubmitState() {
    if (submitBtn) submitBtn.disabled = !(startDate && endDate);
  }
  function updateHiddenInputs() {
    if (fechaInicioInput) fechaInicioInput.value = startDate || '';
    if (fechaFinInput) fechaFinInput.value = endDate || '';
  }
  function setInfo(text) {
    if (rangeTextEl) rangeTextEl.textContent = text || '';
    if (rangeInfoEl) rangeInfoEl.classList.toggle('hidden', !text);
  }

  // Highlight selected range with a background event
  function clearRangeHighlight(cal) {
    cal.getEvents().forEach(ev => {
      if (ev.id === 'selected-range') ev.remove();
    });
  }
  function applyRangeHighlight(cal) {
    clearRangeHighlight(cal);
    if (!startDate) return;
    const endExclusive = endDate ? addDays(endDate, 1) : addDays(startDate, 1);
    cal.addEvent({
      id: 'selected-range',
      start: startDate,
      end: endExclusive,
      display: 'background',
      color: '#cde8ff'
    });
  }

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    firstDay: 1,
    locale: 'es',
    selectable: false, // we drive selection via dateClick to support 2-click across months
    height: 'auto',
    aspectRatio: 1.05,
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
    buttonText: { today: 'Hoy' },
    titleFormat: { year: 'numeric', month: 'short' },
    dayHeaderFormat: { weekday: 'short' },
    dayMaxEvents: false,
    dayCellDidMount: function(arg) {
      // Subtle weekend tint for better visual guidance
      const day = arg.date.getDay(); // 0=Sun,6=Sat
      if (day === 0 || day === 6) {
        arg.el.style.backgroundColor = 'rgba(250, 200, 200, 0.18)';
      }
    },
    datesSet: function() {
      // Re-apply highlight after navigation
      applyRangeHighlight(calendar);
    },
    dateClick: function(info) {
      const clicked = info.dateStr; // YYYY-MM-DD
      if (!startDate || (startDate && endDate)) {
        // Start new selection
        startDate = clicked;
        endDate = null;
        setInfo(`Inicio: ${fmt(startDate)} — selecciona fin`);
        updateHiddenInputs();
        updateSubmitState();
        applyRangeHighlight(calendar);
        return;
      }

      // Complete selection
      endDate = clicked;
      if (new Date(endDate) < new Date(startDate)) {
        const tmp = startDate;
        startDate = endDate;
        endDate = tmp;
      }
      setInfo(`✅ ${fmt(startDate)} → ${fmt(endDate)}`);
      updateHiddenInputs();
      updateSubmitState();
      applyRangeHighlight(calendar);
    }
  });

  // Inject a small clear button below the calendar for convenience
  const clearBtn = document.createElement('button');
  clearBtn.type = 'button';
  clearBtn.textContent = 'Limpiar selección';
  clearBtn.style.marginTop = '8px';
  clearBtn.className = 'btn btn-secondary';
  clearBtn.addEventListener('click', () => {
    startDate = null;
    endDate = null;
    setInfo('');
    updateHiddenInputs();
    updateSubmitState();
    clearRangeHighlight(calendar);
  });
  calendarEl.parentElement && calendarEl.parentElement.appendChild(clearBtn);

  // Initialize default UI state
  setInfo('');
  updateSubmitState();
  calendar.render();

  // Return a tiny API if needed later
  return {
    getStart: () => startDate,
    getEnd: () => endDate,
    setRange: (start, end) => {
      startDate = start;
      endDate = end;
      if (startDate && endDate && new Date(endDate) < new Date(startDate)) {
        const tmp = startDate; startDate = endDate; endDate = tmp;
      }
      setInfo(startDate && endDate ? `✅ ${fmt(startDate)} → ${fmt(endDate)}` : (startDate ? `Inicio: ${fmt(startDate)} — selecciona fin` : ''));
      updateHiddenInputs();
      updateSubmitState();
      applyRangeHighlight(calendar);
    }
  };
};
