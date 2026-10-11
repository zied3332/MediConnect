from django.shortcuts import render


def home(request):
    """Render the public MediConnect homepage."""
    return render(request, "core/home.html")