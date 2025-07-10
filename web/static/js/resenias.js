// Ejemplo para un botón de eliminar con AJAX
document.querySelectorAll('.btn-eliminar-resenia').forEach(btn => {
  btn.addEventListener('click', async function(e) {
    e.preventDefault();
    const form = this.closest('form');
    const result = await Swal.fire({
      title: '¿Eliminar reseña?',
      text: "¿Está seguro que desea eliminar esta reseña?",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Confirmar',
      cancelButtonText: 'Cancelar'
    });
    if (result.isConfirmed) {
      fetch(form.action, {
        method: 'POST',
        headers: {'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value}
      }).then(resp => {
        if (resp.ok) {
          // Eliminá el elemento del DOM si querés
          form.closest('.card').remove();
          Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: 'Reseña eliminada correctamente',
            showConfirmButton: false,
            timer: 2000,
            timerProgressBar: true
          });
        }
      });
    }
  });
});

// Configurar botones de eliminar reseñas
function configurarBotonesEliminarResenias() {
  document.querySelectorAll('.btn-eliminar-resenia').forEach(boton => {
    boton.addEventListener('click', async function(evento) {
      evento.preventDefault();
      const confirmado = await mostrarConfirmacion(
        'Eliminar reseña',
        '¿Estás seguro de que deseas eliminar esta reseña?'
      );
      
      if (confirmado) {
        this.closest('form').submit();
      }
    });
  });
}

// Función de confirmación reusable
async function mostrarConfirmacion(titulo, texto) {
  const resultado = await Swal.fire({
    title: titulo,
    text: texto,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Confirmar',
    cancelButtonText: 'Cancelar'
  });
  
  return resultado.isConfirmed;
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
  configurarBotonesEliminarResenias();
});