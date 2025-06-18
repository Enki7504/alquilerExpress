document.addEventListener('DOMContentLoaded', function() {
  const provinciaSelect = document.getElementById('provincia-select');
  const ciudadSelect = document.getElementById('ciudad-select');

  if (provinciaSelect && ciudadSelect) {
    provinciaSelect.addEventListener('change', function() {
      const provinciaId = this.value;
      ciudadSelect.disabled = true;
      ciudadSelect.innerHTML = '<option value="">Cargando...</option>';
      if (provinciaId) {
        fetch(`/ajax/cargar-ciudades/?provincia=${provinciaId}`)
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