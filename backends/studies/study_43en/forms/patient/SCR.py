# backends/studies/study_43en/forms/patient/SCR.py

from django import forms
from django.utils.translation import gettext_lazy as _

# Import models from refactored structure
from backends.studies.study_43en.models.patient import SCR_CASE

# ==========================================
# COMMON CHOICES
# ==========================================

SITEID_CHOICES = [
    ('003', 'HTD/003 - Bệnh viện Bệnh Nhiệt Đới TPHCM'),
    ('020', 'NHTD/020 - Bệnh viện Bệnh Nhiệt Đới Trung Ương'),
    ('011', 'CRH/011 - Bệnh viện Chợ Rẫy'),
]


# ==========================================
# SCREENING FORMS
# ==========================================

class ScreeningCaseForm(forms.ModelForm):
    """
    Screening Case Form with labels synced to model verbose_name
    
     UPDATED: Support selected_site_id for site filtering
    
    Features:
    - Auto-generated SCRID (not editable)
    - Auto-generated SUBJID and USUBJID for eligible patients
    - Optimistic locking with version control
    - Radio buttons for eligibility criteria
    - Site-based SITEID filtering
    """
    
    #  UPDATED: SITEID will be configured in __init__ based on user's site
    SITEID = forms.ChoiceField(
        choices=SITEID_CHOICES,
        label=_('Site ID')
    )
    
    # Radio buttons for boolean fields
    UPPER16AGE = forms.ChoiceField(
        choices=[('0', _('No')), ('1', _('Yes'))],
        widget=forms.RadioSelect,
        required=True,
        label=_('Age ≥16 years')
    )
    
    INFPRIOR2OR48HRSADMIT = forms.ChoiceField(
        choices=[('0', _('No')), ('1', _('Yes'))],
        widget=forms.RadioSelect,
        required=True,
        label=_('Infection prior to or within 48h of admission')
    )
    
    ISOLATEDKPNFROMINFECTIONORBLOOD = forms.ChoiceField(
        choices=[('0', _('No')), ('1', _('Yes'))],
        widget=forms.RadioSelect,
        required=True,
        label=_('KPN isolated from infection site or blood')
    )

    KPNISOUNTREATEDSTABLE = forms.ChoiceField(
        choices=[('0', _('No')), ('1', _('Yes'))],
        widget=forms.RadioSelect,
        required=True,
        label=_('KPN untreated and stable')
    )

    CONSENTTOSTUDY = forms.ChoiceField(
        choices=[('0', _('No')), ('1', _('Yes'))],
        widget=forms.RadioSelect,
        required=True,
        label=_('Consent to participate')
    )
    
    SCREENINGFORMDATE = forms.DateField(
        required=False,
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        widget=forms.DateInput(format='%d/%m/%Y', attrs={'type': 'text', 'class': 'form-control datepicker', 'placeholder': 'DD/MM/YYYY'}),
        label=_('Screening Form Date')
    )
    
    # Optimistic locking
    version = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        initial=0
    )
    
    class Meta:
        model = SCR_CASE
        fields = [
            'STUDYID', 'SITEID', 'INITIAL',
            'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT', 'ISOLATEDKPNFROMINFECTIONORBLOOD',
            'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY', 'SCREENINGFORMDATE',
            'UNRECRUITED_REASON', 'WARD'
        ]
        
        labels = {
            'STUDYID': _('Study ID'),
            'SITEID': _('Site ID'),
            'INITIAL': _('Initial'),
            'UPPER16AGE': _('Age ≥16 years'),
            'INFPRIOR2OR48HRSADMIT': _('Infection prior to or within 48h of admission'),
            'ISOLATEDKPNFROMINFECTIONORBLOOD': _('KPN isolated from infection site or blood'),
            'KPNISOUNTREATEDSTABLE': _('KPN untreated and stable'),
            'CONSENTTOSTUDY': _('Consent to participate'),
            'SCREENINGFORMDATE': _('Screening Form Date'),
            'UNRECRUITED_REASON': _('Reason Not Recruited'),
            'WARD': _('Ward/Department'),
        }
        
        widgets = {
            'STUDYID': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
            'INITIAL': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'UNRECRUITED_REASON': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'WARD': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 255}),
        }
        
        help_texts = {
            'STUDYID': _('Unique identifier for the study'),
            'SITEID': _('Study site identification code'),
            'INITIAL': _('Patient initials'),
            'UPPER16AGE': _('Patient must be 16 years or older'),
            'INFPRIOR2OR48HRSADMIT': _('Infection occurred before admission or within 48 hours'),
            'ISOLATEDKPNFROMINFECTIONORBLOOD': _('K. pneumoniae isolated from infection site or blood culture'),
            'KPNISOUNTREATEDSTABLE': _('Untreated KPN infection that resolved spontaneously'),
            'CONSENTTOSTUDY': _('Patient or legal representative consent to participate'),
            'SCREENINGFORMDATE': _('Date when screening form was completed'),
            'UNRECRUITED_REASON': _('Reason why patient was not enrolled in the study'),
            # 'WARD': _('Hospital ward or department where patient is located'),
        }
    
    def __init__(self, *args, **kwargs):
        """
         UPDATED: Extract and handle selected_site_id
        
        Args:
            selected_site_id (str): Site ID from session
                - 'all': Admin - can select any site
                - '003'/'011'/'020': Site user - locked to their site
        """
        #  CRITICAL FIX: Pop selected_site_id BEFORE calling super()
        selected_site_id = kwargs.pop('selected_site_id', None)
        
        super().__init__(*args, **kwargs)
        
        # ⚠️ FIX: STUDYID is readonly but must be included in POST
        # Remove disabled=True, use readonly only
        self.fields['STUDYID'].widget.attrs['readonly'] = 'readonly'
        self.fields['STUDYID'].widget.attrs['style'] = 'background-color: #e9ecef;'
        self.fields['STUDYID'].required = True
        
        #  THÊM: Configure SITEID field based on user's site
        self._configure_siteid_field(selected_site_id)
        
        # Set version for optimistic locking
        if self.instance and self.instance.pk:
            self.fields['version'].initial = self.instance.version
        
        #  Show readonly SCRID (for both CREATE and UPDATE)
        if self.instance.SCRID:  # Changed from self.instance.pk
            self.fields['SCRID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Screening ID"),
                initial=self.instance.SCRID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef; font-weight: bold;'
                })
            )
        
        #  Show readonly SUBJID if exists
        if self.instance.pk and self.instance.SUBJID:
            self.fields['SUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Subject ID"),
                initial=self.instance.SUBJID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef;'
                })
            )
        
        #  Show readonly USUBJID if exists
        if self.instance.pk and self.instance.USUBJID:
            self.fields['USUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Unique Subject ID"),
                initial=self.instance.USUBJID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef;'
                })
            )
        
        # Apply form-control class to all fields
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'input_type') or field.widget.input_type != 'radio':
                existing_class = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_class:
                    field.widget.attrs['class'] = f"{existing_class} form-control".strip()
        
        # Set default values for new forms
        if not self.instance.pk:
            boolean_fields = [
                'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT',
                'ISOLATEDKPNFROMINFECTIONORBLOOD', 'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY'
            ]
            for field_name in boolean_fields:
                self.fields[field_name].initial = '0'
        else:
            # Convert boolean to string for existing records
            self.fields['UPPER16AGE'].initial = '1' if self.instance.UPPER16AGE else '0'
            self.fields['INFPRIOR2OR48HRSADMIT'].initial = '1' if self.instance.INFPRIOR2OR48HRSADMIT else '0'
            self.fields['ISOLATEDKPNFROMINFECTIONORBLOOD'].initial = '1' if self.instance.ISOLATEDKPNFROMINFECTIONORBLOOD else '0'
            self.fields['KPNISOUNTREATEDSTABLE'].initial = '1' if self.instance.KPNISOUNTREATEDSTABLE else '0'
            self.fields['CONSENTTOSTUDY'].initial = '1' if self.instance.CONSENTTOSTUDY else '0'
    
    def _configure_siteid_field(self, selected_site_id):
        """
         NEW METHOD: Configure SITEID field choices based on user's site
        
        Args:
            selected_site_id (str): 'all', '003', '011', or '020'
        """
        if selected_site_id and selected_site_id != 'all':
            #  SITE USER: Lock to their site only
            site_choice = next(
                (choice for choice in SITEID_CHOICES if choice[0] == selected_site_id),
                None
            )
            
            if site_choice:
                # Lock field to user's site
                self.fields['SITEID'].choices = [site_choice]
                self.fields['SITEID'].initial = selected_site_id
                self.fields['SITEID'].disabled = True  # Cannot change
                self.fields['SITEID'].help_text = _('Your site (cannot be changed)')
                
                #  THÊM: Update widget attrs for styling
                self.fields['SITEID'].widget.attrs.update({
                    'class': 'form-control',
                    'style': 'background-color: #e9ecef;'
                })
            else:
                # Fallback: If site not found, show all but mark as required
                self.fields['SITEID'].choices = SITEID_CHOICES
                self.fields['SITEID'].help_text = _('Please select your site')
        else:
            #  ADMIN: Can select any site
            self.fields['SITEID'].choices = SITEID_CHOICES
            self.fields['SITEID'].help_text = _('Select study site')
    
    def clean_SITEID(self):
        """
         NEW METHOD: Security validation for SITEID
        """
        siteid = self.cleaned_data.get('SITEID')
        
        # If this is an update (instance exists)
        if self.instance and self.instance.pk:
            # SITEID cannot be changed after creation
            if siteid != self.instance.SITEID:
                raise forms.ValidationError(
                    _('Site ID cannot be changed after creation.')
                )
        
        return siteid
    
    def clean_SCREENINGFORMDATE(self):
        """Validate screening date"""
        from django.utils import timezone
        
        date_value = self.cleaned_data.get('SCREENINGFORMDATE')
        
        if date_value:
            # Cannot be in the future
            if date_value > timezone.now().date():
                raise forms.ValidationError(
                    _("Screening date cannot be in the future")
                )
            
            # Cannot be too old (e.g., more than 2 years ago)
            two_years_ago = timezone.now().date().replace(year=timezone.now().year - 2)
            if date_value < two_years_ago:
                raise forms.ValidationError(
                    _("Screening date is too old (>2 years)")
                )
        
        return date_value
    
    def clean_INITIAL(self):
        """Validate initials"""
        value = self.cleaned_data.get('INITIAL')
        
        if value:
            # Remove whitespace and convert to uppercase
            value = value.strip().upper()
            
            # Must be 2-10 characters
            if len(value) < 2:
                raise forms.ValidationError(
                    _("Initial must be at least 2 characters")
                )
            
            if len(value) > 10:
                raise forms.ValidationError(
                    _("Initial cannot exceed 10 characters")
                )
            
            # Only allow letters
            if not value.isalpha():
                raise forms.ValidationError(
                    _("Initial must contain only letters")
                )
        
        return value
    
    def clean(self):
        """Full validation with optimistic locking"""
        cleaned_data = super().clean()
        
        # ==========================================
        # 1. OPTIMISTIC LOCKING CHECK
        # ==========================================
        if self.instance.pk:
            submitted_version = cleaned_data.get('version')
            
            try:
                current_record = SCR_CASE.objects.get(pk=self.instance.pk)
                
                if submitted_version != current_record.version:
                    raise forms.ValidationError(
                        _(" Record has been modified by another user. "
                          "Please refresh the page and try again.")
                    )
            except SCR_CASE.DoesNotExist:
                raise forms.ValidationError(_("Record does not exist"))
        
        # ==========================================
        # 2. CONVERT BOOLEAN FIELDS
        # ==========================================
        boolean_fields = [
            'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT',
            'ISOLATEDKPNFROMINFECTIONORBLOOD', 'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY'
        ]
        for field_name in boolean_fields:
            value = cleaned_data.get(field_name)
            cleaned_data[field_name] = (value == '1')
        
        # ==========================================
        # 3. ELIGIBILITY VALIDATION
        # ==========================================
        is_eligible = (
            cleaned_data.get('UPPER16AGE') and
            cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
            cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
            not cleaned_data.get('KPNISOUNTREATEDSTABLE')
        )
        
        # Cannot consent if not eligible
        if not is_eligible and cleaned_data.get('CONSENTTOSTUDY'):
            self.add_error(
                'CONSENTTOSTUDY',
                _("Cannot consent when eligibility criteria are not met "
                  "(all 4 criteria above must be correct)")
            )
            cleaned_data['CONSENTTOSTUDY'] = False
        
        # ==========================================
        # 4. UNRECRUITED_REASON VALIDATION
        # ==========================================
        if not is_eligible or not cleaned_data.get('CONSENTTOSTUDY'):
            # Not recruited - reason is required
            if not cleaned_data.get('UNRECRUITED_REASON'):
                self.add_error(
                    'UNRECRUITED_REASON',
                    _("Reason is required when patient is not recruited")
                )
        
        # ==========================================
        # 5. WARD VALIDATION (Optional)
        # ==========================================
        ward = cleaned_data.get('WARD')
        if ward:
            # Trim whitespace
            cleaned_data['WARD'] = ward.strip()
        
        return cleaned_data