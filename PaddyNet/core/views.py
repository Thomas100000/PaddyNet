from django.shortcuts import render


def home(request):
    return render(request, 'index.html')


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler403(request, exception=None):
    return render(request, '403.html', status=403)
