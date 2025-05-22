from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.forms import UserCreationForm

# Create your views here.

def index(request):
    return render(request, 'index.html')



def logout_view(request):
    """Sólo procesa POST para cerrar sesión y redirige a login"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, "Has cerrado sesión correctamente.")
        return redirect('login')
    # si alguien entra por GET, lo mandamos al index
    return redirect('index')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})