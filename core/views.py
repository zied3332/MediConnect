"""Public directory backed by approved practitioners."""
from django.db.models import Q
from django.shortcuts import render
from appointments.services import approved_doctors
from specialty.models import Specialty


def home(request):
    query = request.GET.get('q', '').strip()[:150]
    selected = request.GET.get('specialty', '')
    doctors = approved_doctors().select_related('main_specialty', 'doctor_profile').order_by('first_name', 'last_name', 'pk')
    total = doctors.count()
    featured = doctors.first()
    for word in query.split()[:12]:
        doctors = doctors.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word) | Q(main_specialty__name__icontains=word))
    if selected:
        doctors = doctors.filter(main_specialty_id=int(selected)) if selected.isdecimal() and len(selected) < 12 else doctors.none()
    specialties = Specialty.objects.order_by('name')
    return render(request, 'core/home.html', {
        'popular_specialties': specialties, 'doctors': doctors[:6], 'result_count': doctors.count(),
        'doctor_total': total, 'specialty_total': specialties.count(), 'featured_doctor': featured,
        'query': query, 'selected_specialty': selected, 'is_search': bool(query or selected),
    })
