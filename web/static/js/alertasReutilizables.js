// alertasReutilizables.js - Funciones base de SweetAlert2
export async function mostrarConfirmacion(titulo, texto, icono = 'question') {
  return await Swal.fire({
    title: titulo,
    text: texto,
    icon: icono,
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Confirmar',
    cancelButtonText: 'Cancelar',
    allowOutsideClick: false
  });
}

export function mostrarToast(mensaje, tipo = 'info') {
  const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
      toast.addEventListener('mouseenter', Swal.stopTimer);
      toast.addEventListener('mouseleave', Swal.resumeTimer);
    }
  });
  
  Toast.fire({
    icon: tipo,
    title: mensaje
  });
}

export function mostrarError(titulo, mensaje, detalles = null) {
  return Swal.fire({
    title: titulo,
    html: detalles ? `${mensaje}<br><br><details><summary>Detalles</summary>${detalles}</details>` : mensaje,
    icon: 'error',
    confirmButtonText: 'Entendido'
  });
}