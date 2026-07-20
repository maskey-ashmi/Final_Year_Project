window.escapeHtml = function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
};

window.loadAppSession = async function loadAppSession() {
  if (!window.__appSessionPromise) {
    window.__appSessionPromise = fetch('/api/session', {
      headers: { Accept: 'application/json' },
    }).then(async (response) => {
      if (!response.ok) {
        throw new Error('Unable to load session state.');
      }

      const payload = await response.json();
      window.appSession = payload;
      return payload;
    });
  }

  return window.__appSessionPromise;
};

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const session = await window.loadAppSession();
    const navLinks = document.getElementById('navbarMainLinks');
    if (navLinks) {
      let links = [];
      if (session.authenticated) {
        if (session.user?.role === 'admin') {
          links.push('<li class="nav-item"><a class="nav-link" href="/admin">Clinical Insights</a></li>');
        } else {
          links.push('<li class="nav-item"><a class="nav-link" href="/">HOME</a></li>');
          links.push('<li class="nav-item"><a class="nav-link" href="/dashboard">Sanctuary</a></li>');
          links.push('<li class="nav-item"><a class="nav-link" href="/scan">Scan Studio</a></li>');
        }
        links.push('<li class="nav-item"><a class="nav-link nav-link-cta" href="/logout">Logout</a></li>');
      } else {
        links.push('<li class="nav-item"><a class="nav-link" href="/">HOME</a></li>');
        links.push('<li class="nav-item"><a class="nav-link" href="/login">LOGIN</a></li>');
        links.push('<li class="nav-item"><a class="nav-link nav-link-cta" href="/signup">CREATE ACCOUNT</a></li>');
      }
      navLinks.innerHTML = links.join('');
    }

    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer && Array.isArray(session.flash_messages) && session.flash_messages.length > 0) {
      toastContainer.innerHTML = session.flash_messages
        .map(
          ({ category, message }) => `
            <div class="toast editorial-toast align-items-center show mb-2" role="alert" aria-live="assertive" aria-atomic="true">
              <div class="d-flex">
                <div class="toast-body">
                  <span class="toast-tag">${window.escapeHtml(category).replace(/^\w/, (match) => match.toUpperCase())}</span>
                  <span>${window.escapeHtml(message)}</span>
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
            </div>
          `
        )
        .join('');

      if (window.bootstrap?.Toast) {
        Array.from(toastContainer.querySelectorAll('.toast')).forEach((toastEl) => {
          const toast = new window.bootstrap.Toast(toastEl, { delay: 4000 });
          toast.show();
        });
      }
    }

    const analysisLink = document.getElementById('home-analysis-link');
    if (analysisLink) {
      analysisLink.href = session.authenticated ? '/scan' : '/login?next=%2Fscan';
    }
  } catch (error) {
    console.error(error);
  }
});
