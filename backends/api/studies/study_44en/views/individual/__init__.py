# backends/api/studies/study_44en/views/individual/__init__.py

"""
Individual Views for Study 44EN
"""

from .individual_case.views_individual_case import *
from .views_individual_exposure import *
from .views_individual_followup import *
from .views_individual_sample import *

__all__ = [
    'individual_detail',
    'individual_create',
    'individual_edit',
    'individual_exposure',
    'individual_followup',
    'individual_sample',
]
