from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from .forms import CustomUserCreationForm

# Create your views here.
def home(request):
    return render(request, 'authtest/home.html', {})

# @login_required
# def private_page(request):
#     return render(request, 'authtest/private.html', {})

@login_required
def chat_page(request):
    return render(request, 'chat/index.html', {})

# def public_page(request):
#     return render(request, 'authtest/public.html', {})

# 特定のユーザーのみ許可
def admin_page(user):
    return '@iniad' in user.username 

def teacher_group(user):
    if user.is_authenticated and user.groups.filter(name="Teacher").exists():
        return True
    raise PermissionDenied

@login_required
@user_passes_test(teacher_group)
def restricted_page(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'authtest/restricted_page.html', {'form': form})

def permi_not(request, exception=None):
    return render(request, 'authtest/403.html', status=403)