// ============================= BOTONES ============================= //

function configurarBotonesResponder() {
  document.querySelectorAll('.btn-responder-comentario').forEach(boton => {
    boton.addEventListener('click', function() {
      const id = this.getAttribute('data-comentario');
      const formularioRespuesta = document.getElementById('form-respuesta-' + id);
      const botonResponder = document.getElementById('btn-responder-' + id);
      
      alternarFormularioRespuesta(id, formularioRespuesta, botonResponder);
    });
  });
}

function configurarBotonesConfirmarRespuesta() {
  document.querySelectorAll('.form-respuesta-comentario').forEach(formulario => {
    formulario.addEventListener('submit', async function(evento) {
      evento.preventDefault();
      
      const { isConfirmed } = await Swal.fire({
        title: 'Publicar respuesta',
        text: '¿Estás seguro de que deseas publicar esta respuesta?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Confirmar',
        cancelButtonText: 'Cancelar'
      });
      
      if (isConfirmed) {
        this.submit(); // Envío tradicional para que Django maneje los mensajes
      }
    });
  });
}

function configurarBotonesEliminar() {
  document.querySelectorAll('.btn-eliminar-comentario').forEach(boton => {
    boton.addEventListener('click', async function(evento) {
      evento.preventDefault();
      
      const { isConfirmed } = await Swal.fire({
        title: 'Eliminar comentario',
        text: '¿Estás seguro de que deseas eliminar este comentario?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Eliminar',
        cancelButtonText: 'Cancelar'
      });
      
      if (isConfirmed) {
        this.closest('form').submit(); // Envío tradicional
      }
    });
  });
}

function configurarBotonesCancelar() {
  document.querySelectorAll('.btn-cancelar-respuesta').forEach(boton => {
    boton.addEventListener('click', function() {
      const id = this.getAttribute('data-comentario');
      cancelarRespuesta(id);
    });
  });
}

// ============================= UTILIDADES ============================= //

function alternarFormularioRespuesta(id, formularioRespuesta, botonResponder) {
  // Ocultar todos los formularios y restaurar botones
  document.querySelectorAll('.form-respuesta-comentario').forEach(form => {
    form.style.display = 'none';
  });
  document.querySelectorAll('.btn-responder-comentario').forEach(boton => {
    boton.classList.remove('btn-primary');
    boton.classList.add('btn-outline-primary');
  });
  
  // Alternar el formulario actual
  if (formularioRespuesta.style.display === 'none' || formularioRespuesta.style.display === '') {
    formularioRespuesta.style.display = 'block';
    botonResponder.classList.remove('btn-outline-primary');
    botonResponder.classList.add('btn-primary');
  }
}

function cancelarRespuesta(id) {
  // Ocultar formulario
  const formularioRespuesta = document.getElementById('form-respuesta-' + id);
  if (formularioRespuesta) {
    formularioRespuesta.style.display = 'none';
    formularioRespuesta.querySelector('textarea').value = '';
  }
  
  // Restaurar botón Responder
  const botonResponder = document.getElementById('btn-responder-' + id);
  if (botonResponder) {
    botonResponder.classList.remove('btn-primary');
    botonResponder.classList.add('btn-outline-primary');
  }
}

// ============================= INICIALIZACIÓN ============================= //

document.addEventListener('DOMContentLoaded', function() {
  configurarBotonesResponder();
  configurarBotonesConfirmarRespuesta();
  configurarBotonesEliminar();
  configurarBotonesCancelar();
});