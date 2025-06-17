// Script para manejar el dropdown de notificaciones
document.addEventListener('DOMContentLoaded', function() {
  const dropdown = document.getElementById('notificacionesDropdown');
  if (dropdown) {
    dropdown.addEventListener('shown.bs.dropdown', function() {
        // Actualizar el contador via AJAX
        fetch('{% url "marcar_todas_leidas" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
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
            }
        });
    });
  }
});

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