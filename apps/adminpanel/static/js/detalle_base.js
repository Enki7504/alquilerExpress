// Convertir los mensajes de Django a SweetAlert
const messageElements = document.querySelectorAll('.django-message');

messageElements.forEach(element => {
    const tags = element.getAttribute('data-tags');
    const message = element.getAttribute('data-message');
    
    // Mapear las etiquetas de Django a iconos de SweetAlert
    let icon = 'info';
    if (tags.includes('success')) icon = 'success';
    if (tags.includes('error') || tags.includes('danger')) icon = 'error';
    if (tags.includes('warning')) icon = 'warning';
    
    // Mostrar la notificación tipo toast
    Swal.fire({
        position: 'top-end',
        icon: icon,
        title: message,
        showConfirmButton: false,
        timer: 3000,
        toast: true,
        timerProgressBar: true
    });
});

document.addEventListener('DOMContentLoaded', function() {
  var fechasOcupadas = JSON.parse(document.getElementById('fechasOcupadasJSON').textContent);
  var fechasOcupadasPropias = JSON.parse(document.getElementById('fechasOcupadasPropiasJSON').textContent);

  function marcarPropias(date, domElement) {
    const fechaStr = date.toISOString().slice(0, 10);
    if (fechasOcupadasPropias.includes(fechaStr)) {
      domElement.classList.add('flatpickr-day-propia');
    }
  }

  flatpickr("#fecha_inicio", {
    disable: fechasOcupadas,
    dateFormat: "Y-m-d",
    minDate: "today",
    onDayCreate: function(dObj, dStr, fp, dayElem) {
      marcarPropias(dayElem.dateObj, dayElem);
    }
  });
  flatpickr("#fecha_fin", {
    disable: fechasOcupadas,
    dateFormat: "Y-m-d",
    minDate: "today",
    onDayCreate: function(dObj, dStr, fp, dayElem) {
      marcarPropias(dayElem.dateObj, dayElem);
    }
  });

  // Manejo del botón "Responder"
  document.querySelectorAll('.btn-responder-comentario').forEach(btn => {
    btn.addEventListener('click', function() {
      const id = this.getAttribute('data-comentario');
      const formRespuesta = document.getElementById('form-respuesta-' + id);
      const btnResponder = document.getElementById('btn-responder-' + id);

      // Alternar visibilidad del formulario y el estilo del botón
      if (formRespuesta.style.display === 'none' || formRespuesta.style.display === '') {
        // Oculta todos los formularios de respuesta y restaura sus botones
        document.querySelectorAll('.form-respuesta-comentario').forEach(form => {
          form.style.display = 'none';
        });
        document.querySelectorAll('.btn-responder-comentario').forEach(otherBtn => {
          otherBtn.classList.remove('btn-primary');
          otherBtn.classList.add('btn-outline-primary');
        });

        // Muestra el formulario actual
        formRespuesta.style.display = 'block';
        btnResponder.classList.remove('btn-outline-primary');
        btnResponder.classList.add('btn-primary');
      } else {
        // Oculta el formulario actual
        formRespuesta.style.display = 'none';
        btnResponder.classList.remove('btn-primary');
        btnResponder.classList.add('btn-outline-primary');
      }
    });
  });
  
  // Manejo del botón "Cancelar"
  document.querySelectorAll('.btn-cancelar-respuesta').forEach(btn => {
    btn.addEventListener('click', function() {
      const id = this.getAttribute('data-comentario');
      // Oculta el formulario de respuesta
      const formRespuesta = document.getElementById('form-respuesta-' + id);
      if (formRespuesta) {
        formRespuesta.style.display = 'none';
      }
      // Restaura el botón "Responder" a su estado original
      const btnResponder = document.getElementById('btn-responder-' + id);
      if (btnResponder) {
        btnResponder.classList.remove('btn-primary');
        btnResponder.classList.add('btn-outline-primary');
      }
    });
  });

  // Confirmación para eliminar comentario
  document.querySelectorAll('.btn-eliminar-comentario').forEach(btn => {
    btn.addEventListener('click', async function() {
      const id = this.getAttribute('data-comentario');
      const result = await Swal.fire({
        title: '¿Eliminar comentario?',
        text: "¿Está seguro que desea eliminar este comentario?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Confirmar',
        cancelButtonText: 'Cancelar'
      });
      if (result.isConfirmed) {
        const formEliminar = document.getElementById('form-eliminar-' + id);
        if (formEliminar) {
          formEliminar.submit();
        }
      }
    });
  });
});
