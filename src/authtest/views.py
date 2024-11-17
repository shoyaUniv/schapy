from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
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

@login_required  # ログインしていないユーザーはログインページにリダイレクト
@user_passes_test(admin_page)  # 特定のユーザーだけにアクセスを制限
def restricted_page(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')  # ユーザー登録後のリダイレクト先
    else:
        form = CustomUserCreationForm()

    return render(request, 'authtest/restricted_page.html', {'form': form})