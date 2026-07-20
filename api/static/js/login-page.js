function getLoginModeCopy(mode) {
  if (mode === 'admin') {
    return {
      eyebrow: 'Admin Access',
      title: 'Clinical sign in',
      body: 'Use your approved practitioner or admin account to access elevated review tools.',
      button: 'Enter Clinical Insights',
      switchLabel: 'Return to User Login',
      switchHref: '/login',
    };
  }

  return {
    eyebrow: 'Personal Sanctuary',
    title: 'Welcome back',
    body: 'Sign in to review your saved scans, routine guidance, and appointments.',
    button: 'Enter Skin Sanctuary',
    switchLabel: 'Admin Access',
    switchHref: '/login?mode=admin',
  };
}

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') === 'admin' ? 'admin' : 'user';
  const nextPage = params.get('next') || '';
  const copy = getLoginModeCopy(mode);

  document.getElementById('login-mode-label').textContent = copy.eyebrow;
  document.getElementById('login-title').textContent = copy.title;
  document.getElementById('login-copy').textContent = copy.body;
  document.getElementById('login-submit-label').textContent = copy.button;

  const switchLink = document.getElementById('login-mode-switch');
  const switchUrl = new URL(copy.switchHref, window.location.origin);
  if (nextPage) {
    switchUrl.searchParams.set('next', nextPage);
  }
  switchLink.textContent = copy.switchLabel;
  switchLink.href = switchUrl.pathname + switchUrl.search;

  document.getElementById('login-mode-input').value = mode;
  document.getElementById('login-next-input').value = nextPage;
});
