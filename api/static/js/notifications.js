// Initialize Bootstrap toasts for any flash messages rendered in base.html

document.addEventListener('DOMContentLoaded', () => {
  const toastElList = [].slice.call(document.querySelectorAll('.toast'));
  toastElList.forEach((toastEl) => {
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
  });
});

