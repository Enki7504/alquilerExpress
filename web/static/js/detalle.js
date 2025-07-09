// Variables globales
let fechaFinMantenimiento = null;

// Obtener datos iniciales del DOM
function obtenerDatosIniciales() {
  try {
    const fechaFin = document.getElementById('fechaFinMantenimientoJSON');
    if (fechaFin && fechaFin.textContent) {
      fechaFinMantenimiento = JSON.parse(fechaFin.textContent);
    }
  } catch (e) {
    console.error("Error al parsear datos iniciales:", e);
  }
}

// Mostrar notificación tipo toast
function mostrarNotificacion(mensaje, tipo = 'info') {
  Swal.fire({
    position: 'top-end',
    icon: tipo,
    title: mensaje,
    showConfirmButton: false,
    timer: 3000,
    toast: true,
    timerProgressBar: true
  });
}

// Obtener fecha mínima para reserva
function obtenerFechaMinima() {
  if (fechaFinMantenimiento) {
    const fecha = new Date(fechaFinMantenimiento);
    fecha.setDate(fecha.getDate() + 1);
    return fecha.toISOString().slice(0, 10);
  }
  return "today";
}

// Configurar datepickers
function configurarDatePickers(fechasOcupadas, fechasOcupadasPropias) {
  const opcionesDatepicker = {
    disable: fechasOcupadas,
    dateFormat: "Y-m-d",
    minDate: obtenerFechaMinima(),
    onDayCreate: function(dObj, dStr, fp, diaElem) {
      marcarFechasPropias(diaElem, fechasOcupadasPropias);
    }
  };
  
  flatpickr("#fecha_inicio", opcionesDatepicker);
  flatpickr("#fecha_fin", opcionesDatepicker);
}

// Marcar fechas propias en el calendario
function marcarFechasPropias(diaElem, fechasOcupadasPropias) {
  const fechaStr = diaElem.dateObj.toISOString().slice(0, 10);
  if (fechasOcupadasPropias.includes(fechaStr)) {
    diaElem.classList.add('flatpickr-day-propia');
  }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
  // Obtener datos iniciales
  obtenerDatosIniciales();
  
  // Mostrar mensajes de Django
  document.querySelectorAll('.django-message').forEach(elemento => {
    const etiquetas = elemento.getAttribute('data-tags');
    const mensaje = elemento.getAttribute('data-message');
    
    let tipo = 'info';
    if (etiquetas.includes('success')) tipo = 'success';
    if (etiquetas.includes('error') || etiquetas.includes('danger')) tipo = 'error';
    if (etiquetas.includes('warning')) tipo = 'warning';
    
    mostrarNotificacion(mensaje, tipo);
  });
  
  // Configurar datepickers
  const fechasOcupadas = JSON.parse(document.getElementById('fechasOcupadasJSON').textContent);
  const fechasOcupadasPropias = JSON.parse(document.getElementById('fechasOcupadasPropiasJSON').textContent);
  configurarDatePickers(fechasOcupadas, fechasOcupadasPropias);
});