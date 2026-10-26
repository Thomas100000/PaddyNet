from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.forms import LoginForm, FarmerRegistrationForm, MillOwnerRegistrationForm

def redirect_by_role(user):
    """Utility helper to redirect a logged-in user to their respective dashboard."""
    if user.is_superuser or user.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif user.role == 'MILLOWNER':
        return redirect('millowner_dashboard')
    else:
        return redirect('farmer_dashboard')

def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.role == 'FARMER':
                    profile = getattr(user, 'farmer_profile', None)
                    if profile and not profile.is_verified:
                        messages.error(request, "Your account is pending verification by the admin. Please wait for verification before logging in.")
                        return render(request, 'login.html', {'form': form})
                if user.role == 'MILLOWNER':
                    profile = getattr(user, 'millowner_profile', None)
                    if profile and not profile.is_verified:
                        messages.error(request, "Your mill account is pending verification by the admin. Please wait for verification before logging in.")
                        return render(request, 'login.html', {'form': form})
                login(request, user)
                display_name = user.first_name if user.first_name else user.username
                messages.success(request, f"Welcome back, {display_name}!")
                return redirect_by_role(user)
            else:
                messages.error(request, "Invalid email/mobile number or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully signed out.")
    return redirect('login')


def register_select_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    return render(request, 'register.html')


def register_farmer_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        form = FarmerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                "Farmer account registered successfully! Your account is pending Admin verification. You can sign in once an Admin approves your account."
            )
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FarmerRegistrationForm()

    return render(request, 'register_farmer.html', {'form': form})



def register_millowner_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        form = MillOwnerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Mill Owner account registered successfully! Your account is pending Admin verification. You can sign in once an Admin approves your account."
            )
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MillOwnerRegistrationForm()

    return render(request, 'register_millowner.html', {'form': form})
