# apps/studies/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def custom_study_view(request, study_code):
    if request.study.code != study_code:
        return redirect('select_study')
    context = {'study_folder': study_code}
    return render(request, f'studies/{study_code}/content.html', context)