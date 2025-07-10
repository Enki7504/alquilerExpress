// Variables globales
let fechaFinMantenimiento = null;
let fechasOcupadas = [];
let fechasOcupadasPropias = [];

// Función para obtener datos JSON embebidos en el DOM
function obtenerJSONDesdeElemento(id) {
  try {
    const elemento = document.getElementById(id);
    if (elemento && elemento.textContent) {
      return JSON.parse(elemento.textContent);
    }
  } catch (error) {
    console.error(`Error al parsear el contenido de ${id}:`, error);
  }
  return null;
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
function configurarDatePickers() {
  const opcionesDatepicker = {
    disable: fechasOcupadas,
    dateFormat: "Y-m-d",
    minDate: obtenerFechaMinima(),
    onDayCreate: function(dObj, dStr, fp, diaElem) {
      marcarFechasPropias(diaElem);
    }
  };

  flatpickr("#fecha_inicio", opcionesDatepicker);
  flatpickr("#fecha_fin", opcionesDatepicker);
}

// Marcar fechas propias en el calendario
function marcarFechasPropias(diaElem) {
  const fechaStr = diaElem.dateObj.toISOString().slice(0, 10);
  if (fechasOcupadasPropias.includes(fechaStr)) {
    diaElem.classList.add('flatpickr-day-propia');
  }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
  fechaFinMantenimiento = obtenerJSONDesdeElemento('fechaFinMantenimientoJSON');
  fechasOcupadas = obtenerJSONDesdeElemento('fechasOcupadasJSON') || [];
  fechasOcupadasPropias = obtenerJSONDesdeElemento('fechasOcupadasPropiasJSON') || [];

  configurarDatePickers();
});
