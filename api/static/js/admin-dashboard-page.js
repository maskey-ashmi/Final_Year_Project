document.addEventListener('DOMContentLoaded', async () => {
  try {
    const response = await fetch('/api/admin/dashboard', {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      if (response.redirected) {
        window.location.href = response.url;
      }
      throw new Error('Unable to load admin dashboard.');
    }

    const payload = await response.json();
    const unauthorized = document.getElementById('admin-unauthorized');
    const content = document.getElementById('admin-content');

    if (payload.unauthorized) {
      unauthorized.classList.remove('d-none');
      content.classList.add('d-none');
      return;
    }

    unauthorized.classList.add('d-none');
    content.classList.remove('d-none');
    document.getElementById('admin-users-count').textContent = payload.users_count ?? 0;
    document.getElementById('admin-scans-count').textContent = payload.scans_count ?? 0;
    document.getElementById('admin-doctors-count').textContent = Array.isArray(payload.doctors) ? payload.doctors.length : 0;
    document.getElementById('admin-most-common-condition').textContent = payload.most_common_condition ?? 'N/A';

    document.getElementById('admin-users-list').innerHTML = (payload.users || [])
      .map(
        (user) => `
          <div class="appointment-card">
            <div>
              <h3>${window.escapeHtml(user.name)}</h3>
              <p class="mb-1">${window.escapeHtml(user.email)}</p>
              <small>${window.escapeHtml(user.role)} • ${window.escapeHtml(user.skin_type || 'Not set')}</small>
            </div>
            <span class="status-badge${user.role === 'admin' ? ' success' : ''}">${window.escapeHtml(user.role)}</span>
          </div>
        `
      )
      .join('');

    const appointments = payload.appointments || [];
    document.getElementById('admin-appointments-list').innerHTML = appointments.length
      ? appointments
          .map(
            (appointment) => `
              <div class="appointment-card">
                <div>
                  <h3>${window.escapeHtml(appointment.doctor.name)}</h3>
                  <p class="mb-1">User #${appointment.user_id}</p>
                  <small>${window.escapeHtml(appointment.appointment_time_display)}</small>
                </div>
                <span class="status-badge success">${window.escapeHtml(appointment.status)}</span>
              </div>
            `
          )
          .join('')
      : `
          <div class="empty-state editorial-soft">
            <i class="bi bi-calendar2-heart"></i>
            <p>No appointments yet.</p>
          </div>
        `;

    const doctors = payload.doctors || [];
    document.getElementById('admin-doctors-list-full').innerHTML = doctors.length
      ? doctors
          .map(
            (doc) => `
              <div class="col-md-6 col-lg-4">
                <div class="appointment-card h-100 d-flex flex-column justify-content-between">
                  <div>
                    <h3>${window.escapeHtml(doc.name)}</h3>
                    <p class="mb-1 text-muted">${window.escapeHtml(doc.specialization)}</p>
                    <small class="d-block"><i class="bi bi-geo-alt"></i> ${window.escapeHtml(doc.location || 'N/A')}</small>
                    <small class="d-block"><i class="bi bi-briefcase"></i> ${window.escapeHtml(doc.experience_years || 0)} years • <i class="bi bi-star-fill text-warning"></i> ${window.escapeHtml(doc.rating || 'N/A')}</small>
                  </div>
                  <div class="mt-3 text-end">
                    <button class="btn btn-sm btn-outline-editorial" onclick="openEditDoctorModal(${doc.id}, '${window.escapeHtml(doc.name).replace(/'/g, "\\'")}', '${window.escapeHtml(doc.specialization).replace(/'/g, "\\'")}', '${window.escapeHtml(doc.location || '').replace(/'/g, "\\'")}', ${doc.experience_years || 0}, ${doc.rating || 0})">Edit Doctor</button>
                  </div>
                </div>
              </div>
            `
          )
          .join('')
      : `
          <div class="empty-state editorial-soft col-12">
            <i class="bi bi-person-badge"></i>
            <p>No doctors added yet.</p>
          </div>
        `;

    // Make the function global so it can be called from onclick
    window.openEditDoctorModal = function(id, name, specialization, location, experience_years, rating) {
      document.getElementById('editDoctorForm').action = '/admin/doctors/' + id + '/edit';
      document.getElementById('editDoctorName').value = name;
      document.getElementById('editDoctorSpec').value = specialization;
      document.getElementById('editDoctorLocation').value = location;
      document.getElementById('editDoctorExp').value = experience_years;
      document.getElementById('editDoctorRating').value = rating;
      
      const editModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('editDoctorModal'));
      editModal.show();
    };

    const predictions = payload.predictions || [];
    document.getElementById('admin-predictions-list').innerHTML = predictions.length
      ? predictions
          .map(
            (prediction) => `
              <article class="history-card">
                <div class="history-image-wrap">
                  <img src="/${window.escapeHtml(prediction.image_path)}" alt="Uploaded scan" class="history-image" />
                </div>
                <div class="history-copy">
                  <div class="history-topline">
                    <span class="history-day">User #${prediction.user_id}</span>
                    <span class="status-badge">${window.escapeHtml(prediction.acne_type)}</span>
                  </div>
                  <p class="history-meta mb-2">Confidence ${(Number(prediction.confidence || 0) * 100).toFixed(1)}%</p>
                  <small class="text-muted">${window.escapeHtml(prediction.created_at_display || '')}</small>
                  <div class="d-flex flex-wrap gap-2 mt-3">
                    <a href="/${window.escapeHtml(prediction.image_path)}" target="_blank" class="btn btn-outline-editorial btn-sm">View Photo</a>
                    <form method="POST" action="/predictions/${prediction.id}/delete">
                      <button type="submit" class="btn btn-outline-editorial danger-tone btn-sm">Delete Photo</button>
                    </form>
                  </div>
                </div>
              </article>
            `
          )
          .join('')
      : `
          <div class="empty-state editorial-soft">
            <i class="bi bi-images"></i>
            <p>No uploaded photos yet.</p>
          </div>
        `;
  } catch (error) {
    console.error(error);
  }
});
