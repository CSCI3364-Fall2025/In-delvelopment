from django.shortcuts import render, redirect

def home(request):
    return render(request, 'home.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def google_login(request):
    # This is just a placeholder until you implement actual Google login
    return redirect('home')