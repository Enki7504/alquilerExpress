// static/js/search_logic.js

document.addEventListener('DOMContentLoaded', function() {
    // Script para la lógica del buscador en la navbar
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const query = this.q.value.trim();
            const currentPath = window.location.pathname;
            let url;

            if (currentPath.includes('/buscar-cocheras/')) {
                url = "/buscar-cocheras/"; // Usar URL directamente, Django tags no funcionan en JS estático
            } else {
                url = "/buscar-inmuebles/"; // Usar URL directamente
            }
            
            window.location.href = query ? `${url}?q=${encodeURIComponent(query)}` : url;
        });
    }

    // Script para la carga de ciudades dinámicamente (común a ambas búsquedas)
    const provinciaSelects = document.querySelectorAll('#provincia-select');
    provinciaSelects.forEach(provincia => {
        if (provincia) {
            const ciudadSelect = document.getElementById(provincia.id.replace('provincia', 'ciudad')); // Asume id="provincia-select" y id="ciudad-select"
            
            provincia.addEventListener('change', function() {
                const provinciaId = this.value;
                ciudadSelect.innerHTML = '<option value="">Todas</option>';
                ciudadSelect.disabled = true;
                if (!provinciaId) return;

                // Determinar el tipo de búsqueda para la URL de AJAX
                const currentPath = window.location.pathname;
                let tipo = '';
                if (currentPath.includes('/buscar-cocheras/')) {
                    tipo = '&tipo=cochera';
                } else if (currentPath.includes('/buscar-inmuebles/')) {
                    tipo = '&tipo=inmueble'; // O un valor por defecto si no es cochera
                }

                fetch(`/ajax/cargar-ciudades-filtro/?provincia=${provinciaId}${tipo}`)
                    .then(response => response.json())
                    .then(data => {
                        data.ciudades.forEach(function(ciudadObj) {
                            const option = document.createElement('option');
                            option.value = ciudadObj.id;
                            option.textContent = ciudadObj.nombre;
                            ciudadSelect.appendChild(option);
                        });
                        ciudadSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error al cargar ciudades:', error);
                        // Opcional: mostrar un SweetAlert si la carga de ciudades falla
                    });
            });
        }
    });
});
