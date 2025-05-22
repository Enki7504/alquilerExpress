document.querySelectorAll(".nav-link").forEach(link => {

  link.addEventListener("click", async function (e) {
    e.preventDefault();
    const section = this.getAttribute("data-section");
    const content = await fetch(`admin-${section}.html`).then(r => r.text());
    document.getElementById("contenido-principal").innerHTML = content;
  });

});


