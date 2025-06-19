document.addEventListener('DOMContentLoaded', function() {
  const provinciaSelect = document.getElementById('provincia-select');
  const ciudadSelect = document.getElementById('ciudad-select');

  // Detectar tipo de búsqueda según el formulario
  // Por ejemplo, podés poner un data-attribute en el formulario: <form data-tipo="inmueble">
  let tipo = 'inmueble';
  const form = provinciaSelect?.closest('form');
  if (form && form.dataset.tipo) {
    tipo = form.dataset.tipo;
  }

  if (provinciaSelect && ciudadSelect) {
    provinciaSelect.addEventListener('change', function() {
      const provinciaId = this.value;
      ciudadSelect.disabled = true;
      ciudadSelect.innerHTML = '<option value="">Cargando...</option>';
      if (provinciaId) {
        fetch(`/ajax/cargar-ciudades-filtro/?provincia=${provinciaId}&tipo=${tipo}`)
          .then(response => response.json())
          .then(data => {
            ciudadSelect.innerHTML = '<option value="">Todas</option>';
            data.ciudades.forEach(function(ciudad) {
              const option = document.createElement('option');
              option.value = ciudad.id;
              option.textContent = ciudad.nombre;
              ciudadSelect.appendChild(option);
            });
            ciudadSelect.disabled = false;
          });
      } else {
        ciudadSelect.innerHTML = '<option value="">Todas</option>';
        ciudadSelect.disabled = true;
      }
    });
  }
});