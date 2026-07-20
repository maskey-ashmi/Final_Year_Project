function renderHistory(entries) {
  const container = document.getElementById('history-content');
  if (!Array.isArray(entries) || entries.length === 0) {
    container.innerHTML = `
      <div class="empty-state editorial-soft">
        <i class="bi bi-images"></i>
        <p>No scan history yet. Start with your first analysis and your images will live here.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <button class="btn btn-outline-editorial mb-3" type="button" data-bs-toggle="collapse" data-bs-target="#historyPanel" aria-expanded="true" aria-controls="historyPanel">
      Show History
    </button>
    <div id="historyPanel" class="collapse show">
      <form id="bulkDeleteForm" method="POST" action="/predictions/bulk-delete"></form>
      <div class="history-toolbar mb-3">
        <label for="historySelectAll" class="history-select-all">
          <input id="historySelectAll" type="checkbox" />
          <span>Select all photos</span>
        </label>
        <button id="bulkDeleteButton" type="submit" form="bulkDeleteForm" class="btn btn-outline-editorial danger-tone" disabled>
          Delete Selected
        </button>
      </div>
      <div class="history-grid">
        ${entries
          .map(({ day_label: dayLabel, prediction }) => {
            const imagePath = `/${window.escapeHtml(prediction.image_path)}`;
            return `
              <article class="history-card">
                <div class="history-image-wrap">
                  <img src="${imagePath}" alt="${window.escapeHtml(dayLabel)} scan image" class="history-image" />
                </div>
                <div class="history-copy">
                  <label class="history-select-row mb-3">
                    <input class="history-select-checkbox" type="checkbox" name="prediction_ids" value="${prediction.id}" form="bulkDeleteForm" />
                    <span>Select this photo</span>
                  </label>
                  <div class="history-topline">
                    <span class="history-day">${window.escapeHtml(dayLabel)}</span>
                    <span class="status-badge">${window.escapeHtml(prediction.acne_type)}</span>
                  </div>
                  <p class="history-meta mb-2">Confidence ${(Number(prediction.confidence || 0) * 100).toFixed(1)}%</p>
                  <small class="text-muted">${window.escapeHtml(prediction.created_at_display || '')}</small>
                  <div class="d-flex flex-wrap gap-2 mt-3">
                    <a href="${imagePath}" target="_blank" class="btn btn-outline-editorial btn-sm">View Photo</a>
                    <form method="POST" action="/predictions/${prediction.id}/delete">
                      <button type="submit" class="btn btn-outline-editorial danger-tone btn-sm">Delete Photo</button>
                    </form>
                  </div>
                </div>
              </article>
            `;
          })
          .join('')}
      </div>
    </div>
  `;

  const selectAll = document.getElementById('historySelectAll');
  const checkboxes = Array.from(document.querySelectorAll('.history-select-checkbox'));
  const bulkDeleteButton = document.getElementById('bulkDeleteButton');

  const syncState = () => {
    const checkedCount = checkboxes.filter((checkbox) => checkbox.checked).length;
    bulkDeleteButton.disabled = checkedCount === 0;
    selectAll.checked = checkedCount === checkboxes.length;
    selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
  };

  selectAll.addEventListener('change', () => {
    checkboxes.forEach((checkbox) => {
      checkbox.checked = selectAll.checked;
    });
    syncState();
  });
  checkboxes.forEach((checkbox) => checkbox.addEventListener('change', syncState));
  syncState();
}

function renderAppointments(appointments, doctors) {
  const container = document.getElementById('appointments-content');
  if (!Array.isArray(appointments) || appointments.length === 0) {
    container.innerHTML = `
      <div class="empty-state editorial-soft">
        <i class="bi bi-calendar2-heart"></i>
        <p>No doctor appointments yet. Use the booking card to add one.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="appointment-list">
      ${appointments
        .map((appointment) => {
          const editBtn = appointment.can_edit
            ? `<button class="btn btn-outline-editorial btn-sm"
                onclick="openEditAppointment(${appointment.id}, ${appointment.doctor.id}, '${appointment.appointment_time}')">
                <i class="bi bi-pencil me-1"></i>Edit
               </button>`
            : `<button class="btn btn-outline-editorial btn-sm" disabled title="Cannot edit within 24 hours of appointment">
                <i class="bi bi-pencil me-1"></i>Edit
               </button>`;

          const deleteBtn = appointment.can_delete
            ? `<button class="btn btn-outline-editorial danger-tone btn-sm"
                onclick="deleteAppointment(${appointment.id})">
                <i class="bi bi-trash me-1"></i>Cancel
               </button>`
            : '';

          return `
            <div class="appointment-card" id="appointment-card-${appointment.id}">
              <div class="flex-grow-1">
                <h3>${window.escapeHtml(appointment.doctor.name)}</h3>
                <p class="mb-1">${window.escapeHtml(appointment.doctor.specialization)}</p>
                <small>${window.escapeHtml(appointment.appointment_time_display)}</small>
              </div>
              <div class="d-flex flex-column align-items-end gap-2">
                <span class="status-badge success">${window.escapeHtml(appointment.status)}</span>
                <div class="d-flex gap-2">
                  ${editBtn}
                  ${deleteBtn}
                </div>
              </div>
            </div>
          `;
        })
        .join('')}
    </div>
  `;
}

// ── Edit appointment ──────────────────────────────────────────────────────────
window.openEditAppointment = function(id, currentDoctorId, isoTime) {
  document.getElementById('edit-appointment-id').value = id;
  document.getElementById('edit-appointment-error').classList.add('d-none');

  const dt = new Date(isoTime);
  const dateStr = dt.toISOString().slice(0, 10);
  const hh = String(dt.getUTCHours()).padStart(2, '0');
  const mm = String(dt.getUTCMinutes()).padStart(2, '0');
  document.getElementById('edit-appointment-date').value = dateStr;
  document.getElementById('edit-appointment-time').value = `${hh}:${mm}`;
  document.getElementById('edit-doctor-id').value = currentDoctorId;

  bootstrap.Modal.getOrCreateInstance(document.getElementById('editAppointmentModal')).show();
};

// ── Delete appointment ────────────────────────────────────────────────────────
window.deleteAppointment = async function(id) {
  if (!confirm('Are you sure you want to cancel this appointment?')) return;
  try {
    const res  = await fetch(`/appointments/${id}/delete`, { method: 'POST', credentials: 'same-origin' });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to cancel appointment.');
      return;
    }
    // Remove the card from DOM immediately
    const card = document.getElementById(`appointment-card-${id}`);
    if (card) card.remove();
    // Show empty state if no cards remain
    const list = document.querySelector('.appointment-list');
    if (list && list.querySelectorAll('.appointment-card').length === 0) {
      document.getElementById('appointments-content').innerHTML = `
        <div class="empty-state editorial-soft">
          <i class="bi bi-calendar2-heart"></i>
          <p>No doctor appointments yet. Use the booking card to add one.</p>
        </div>
      `;
    }
  } catch (e) {
    alert('Something went wrong. Please try again.');
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  // ── Save-edit button handler ─────────────────────────────────────────────
  const saveBtn = document.getElementById('save-appointment-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const id       = document.getElementById('edit-appointment-id').value;
      const doctorId = document.getElementById('edit-doctor-id').value;
      const date     = document.getElementById('edit-appointment-date').value;
      const time     = document.getElementById('edit-appointment-time').value;
      const errorEl  = document.getElementById('edit-appointment-error');
      errorEl.classList.add('d-none');

      const form = new FormData();
      form.append('doctor_id', doctorId);
      form.append('appointment_date', date);
      form.append('appointment_time', time);

      try {
        const res  = await fetch(`/appointments/${id}/edit`, { method: 'POST', body: form, credentials: 'same-origin' });
        const data = await res.json();
        if (!res.ok) {
          errorEl.textContent = data.error || 'Failed to update appointment.';
          errorEl.classList.remove('d-none');
          return;
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('editAppointmentModal')).hide();
        window.location.reload();
      } catch (e) {
        errorEl.textContent = 'Something went wrong. Please try again.';
        errorEl.classList.remove('d-none');
      }
    });
  }

  // ── Load dashboard data ───────────────────────────────────────────────────
  try {
    const response = await fetch('/api/dashboard', {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      if (response.redirected) {
        window.location.href = response.url;
      }
      throw new Error('Unable to load dashboard.');
    }

    const payload = await response.json();
    const latest = payload.latest_prediction;
    const nextAppointment = payload.next_appointment;

    document.getElementById('latest-condition').textContent = latest?.acne_type || 'No scan yet';

    if (nextAppointment) {
      document.getElementById('upcoming-appointment-title').textContent = nextAppointment.doctor.name;
      document.getElementById('upcoming-appointment-meta').textContent = nextAppointment.appointment_time_display;
      const status = document.getElementById('upcoming-appointment-status');
      status.textContent = nextAppointment.status;
      status.classList.remove('d-none');
    }

    const doctors = payload.doctors || [];

    // Populate booking form doctor dropdown
    const doctorSelect = document.getElementById('doctor_id');
    doctors.forEach((doctor) => {
      const option = document.createElement('option');
      option.value = doctor.id;
      option.textContent = `${doctor.name} - ${doctor.specialization}`;
      doctorSelect.appendChild(option);
    });

    // Populate edit modal doctor dropdown
    const editDoctorSelect = document.getElementById('edit-doctor-id');
    if (editDoctorSelect) {
      doctors.forEach((doctor) => {
        const option = document.createElement('option');
        option.value = doctor.id;
        option.textContent = `${doctor.name} - ${doctor.specialization}`;
        editDoctorSelect.appendChild(option);
      });
    }

    renderHistory(payload.history_entries || []);
    renderAppointments(payload.appointments || [], doctors);
  } catch (error) {
    console.error(error);
  }
});
