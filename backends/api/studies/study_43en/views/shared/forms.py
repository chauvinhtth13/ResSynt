# backends/api/studies/study_43en/views/shared/forms.py
"""
Form utilities shared across all views.
"""
import logging

logger = logging.getLogger(__name__)


def make_form_readonly(form):
    """
    Make all form fields readonly/disabled.
    
    Args:
        form: Django Form instance
    """
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True,
            'class': field.widget.attrs.get('class', '') + ' readonly-field'
        })


def make_formset_readonly(formset):
    """
    Make all formset fields readonly/disabled.
    
    Args:
        formset: Django FormSet instance
    """
    for form in formset:
        make_form_readonly(form)
    
    # Disable management form actions
    if hasattr(formset, 'management_form'):
        formset.management_form.fields['DELETE'] = None


def set_field_readonly(form, field_names):
    """
    Make specific fields readonly.
    
    Args:
        form: Django Form instance
        field_names: List of field names to make readonly
    """
    for name in field_names:
        if name in form.fields:
            form.fields[name].disabled = True
            form.fields[name].widget.attrs.update({
                'readonly': True,
                'style': 'background-color: #e9ecef;'
            })


def lock_identity_fields(form, fields=None):
    """
    Lock identity fields (SCRID, SITEID, STUDYID).
    
    Args:
        form: Django Form instance
        fields: List of field names (default: ['SCRID', 'SITEID', 'STUDYID'])
    """
    if fields is None:
        fields = ['SCRID', 'SITEID', 'STUDYID']
    
    for name in fields:
        if name in form.fields:
            form.fields[name].disabled = True
            form.fields[name].widget.attrs.update({
                'readonly': True,
                'style': 'background-color: #e9ecef; font-weight: bold;'
            })
