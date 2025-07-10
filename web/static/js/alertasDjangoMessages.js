// alertasDjangoMessages.js
import { mostrarToast } from './alertasReutilizables.js';

function convertirTagDjango(tag) {
  const mapping = {
    'success': 'success',
    'error': 'error',
    'danger': 'error',
    'warning': 'warning',
    'info': 'info',
    'debug': 'info'
  };
  return mapping[tag] || 'info';
}

export function procesarMensajesDjango() {
  const mensajes = document.querySelectorAll('#django-messages-container .django-message');
  
  mensajes.forEach(mensaje => {
    const tag = mensaje.getAttribute('data-tag');
    const texto = mensaje.getAttribute('data-message');
    
    if (texto) {
      mostrarToast(texto, convertirTagDjango(tag));
      mensaje.remove();
    }
  });

  if (mensajes.length > 0) {
    const container = document.getElementById('django-messages-container');
    container.innerHTML = '';
  }
}

document.addEventListener('DOMContentLoaded', procesarMensajesDjango);
window.procesarMensajesDjango = procesarMensajesDjango;