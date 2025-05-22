// arreglo de prueba
const propiedades = [
  {
    nombre: "Monoambiente en La Plata",
    precio: 60000,
    ubicacion: "Av. Rivadavia 5000",
    imagen: "img/logo-alquiler-express.png"
  },
  {
    nombre: "Cochera cubierta",
    precio: 15000,
    ubicacion: "Recoleta, CABA",
    imagen: "https://via.placeholder.com/400x200"
  },
  {
    nombre: "Dpto 2 amb. en Belgrano",
    precio: 90000,
    ubicacion: "Juramento 2000",
    imagen: "https://via.placeholder.com/400x200"
  }
];

// busca el div de propiedades y crea el HTML de forma dinámica
const contenedor = document.getElementById("lista-propiedades");
propiedades.forEach(prop => {
  const col = document.createElement("div");
  col.className = "col-12 col-md-6 col-lg-3 mb-4";
  col.innerHTML = `
    <div class="card h-100 property-card">
      <img src="${prop.imagen}" class="propiedad__image card-img-top" alt="${prop.nombre}">
      <div class="propiedad__body card-body d-flex flex-column justify-content-between">
        <h5 class="propiedad__nombre card-title">${prop.nombre}</h5>
        <p class="propiedad__precio card-text"><i class="bi bi-currency-dollar"></i> ${prop.precio.toLocaleString("es-AR")}/mes</p>
        <p class="propiedad__ubicacion card-text"><i class="bi bi-geo-alt-fill"></i> ${prop.ubicacion}</p>
      </div>
    </div>
  `;
  contenedor.appendChild(col);
});

// para el json
// fetch("propiedades.json")
//   .then(response => response.json())
//   .then(data => {
//     // igual que arriba, usando `data.forEach(...)`
//   });
