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