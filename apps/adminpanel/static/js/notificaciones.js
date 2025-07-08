// Función global para marcar notificaciones al presionar boton de notificaciones (usada en el HTML)
function marcarTodasLeidas(url, csrfToken) {
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            const badge = document.querySelector('.badge.bg-danger');
            if(badge) {
                badge.textContent = '0';
                badge.style.display = 'none';
            }
            document.querySelectorAll('.notification-item.unread').forEach(function(item) {
                item.classList.remove('unread');
            });
        }
    });
}

// Función global para eliminar notificaciones (usada en el HTML)
function eliminarNotificacion(btn, url, csrfToken) {
  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken
    }
  })
  .then(response => {
    if (response.ok) {
      // Eliminar visualmente la notificación
      const li = btn.closest('li.notification-item');
      if (li) li.remove();
      // Mostrar el toast
      Swal.fire({
        position: 'top-end',
        icon: 'success',
        title: 'Notificación eliminada',
        showConfirmButton: false,
        timer: 1500,
        toast: true,
        timerProgressBar: true
      });
    } else {
      Swal.fire({
        position: 'top-end',
        icon: 'error',
        title: 'Error al eliminar',
        showConfirmButton: false,
        timer: 2000,
        toast: true,
        timerProgressBar: true
      });
    }
  });
}