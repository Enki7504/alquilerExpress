document.addEventListener('DOMContentLoaded', function () {
  const mensajes = JSON.parse(document.getElementById('mensajes-django-json')?.textContent || '[]');

  mensajes.forEach(msg => {
    Swal.fire({
      toast: true,
      position: 'top-end',
      icon: msg.tags.includes('success') ? 'success' :
            msg.tags.includes('error') ? 'error' :
            msg.tags.includes('warning') ? 'warning' : 'info',
      title: msg.message,
      showConfirmButton: false,
      timer: 2500,
    });
  });
});
