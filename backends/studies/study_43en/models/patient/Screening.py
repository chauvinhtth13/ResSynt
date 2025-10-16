import re
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ScreeningCase(models.Model):
    """
    Patient screening information
    Initial assessment for study eligibility
    """
    
    # Compiled regex for better performance
    SCRID_PATTERN = re.compile(r'PS-(\d+)-(\d+)')
    
    # Unrecruited Reason Choices
    UNRECRUITED_CHOICES = [
        ('1', '1. The patient with a positive for K. pneumoniae culture recovered without treatment'),
        ('2', '2. Infection onset after 48 hours of hospitalization'),
        ('3', '3. Age <16 years'),
        ('A', 'A. Patient/Carer does not want to participate in research'),
        ('B', 'B. Patient/Carer scared of procedures'),
        ('C', 'C. Not enough time/ too busy to commit'),
        ('D', 'D. Not able to get informed consent'),
        ('E', 'E. Dr/study team does not include Patient in study'),
        ('F', 'F. Dr/RN too busy to screen Patient properly'),
        ('OTHER', 'Other (specify)'),
    ]
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary identifiers
    SCRID = models.CharField(
        max_length=50,
        primary_key=True,
        verbose_name=_('Screening ID')
    )
    
    USUBJID = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Unique Subject ID')
    )
    
    # Study information
    STUDYID = models.CharField(
        max_length=50,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name=_('Site ID')
    )
    
    SUBJID = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Subject ID')
    )
    
    INITIAL = models.CharField(
        max_length=10,
        verbose_name=_('Initials')
    )
    
    # Eligibility criteria
    UPPER16AGE = models.BooleanField(
        verbose_name=_('Age ≥16 years')
    )
    
    INFPRIOR2OR48HRSADMIT = models.BooleanField(
        verbose_name=_('Infection prior to or within 48h of admission')
    )
    
    ISOLATEDKPNFROMINFECTIONORBLOOD = models.BooleanField(
        verbose_name=_('KPN isolated from infection site or blood')
    )
    
    KPNISOUNTREATEDSTABLE = models.BooleanField(
        verbose_name=_('KPN untreated and stable')
    )
    
    CONSENTTOSTUDY = models.BooleanField(
        verbose_name=_('Consent to participate')
    )
    
    # Dates (Manual entry by user)
    SCREENINGFORMDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Screening Form Date')
    )
    
    COMPLETEDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    # Status
    CONFIRMED = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_('Confirmed')
    )
    
    is_confirmed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Is Confirmed')
    )
    
    UNRECRUITED_REASON = models.CharField(
        max_length=10,
        choices=UNRECRUITED_CHOICES,
        null=True,
        blank=True,
        verbose_name=_('Reason Not Recruited')
    )
    
    UNRECRUITED_REASON_OTHER = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Reason (specify)')
    )
    
    # Location
    WARD = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Department')
    )
    
    # Entry Metadata (auto-filled)
    USER_ENTRY = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('User Entry')
    )
    
    ENTRY = models.IntegerField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Entry Number')
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Entry Time')
    )
    
    class Meta:
        db_table = 'SCR_Case'
        verbose_name = _('Patient Screening')
        verbose_name_plural = _('Patient Screenings')
        ordering = ['-SCREENINGFORMDATE', 'SITEID', 'SUBJID']
        indexes = [
            models.Index(fields=['SITEID', '-SCREENINGFORMDATE'], name='idx_scr_site_date'),
            models.Index(fields=['is_confirmed', 'SITEID'], name='idx_scr_confirmed'),
            models.Index(fields=['USER_ENTRY', '-ENTEREDTIME'], name='idx_scr_user_entry'),
        ]
    
    def __str__(self):
        return self.USUBJID or self.SCRID or f"Screening-{self.pk}"
    
    def is_eligible(self) -> bool:
        """Check if patient meets all eligibility criteria"""
        return (
            self.UPPER16AGE and 
            self.INFPRIOR2OR48HRSADMIT and
            self.ISOLATEDKPNFROMINFECTIONORBLOOD and 
            not self.KPNISOUNTREATEDSTABLE and
            self.CONSENTTOSTUDY
        )
    
    def clean(self):
        """Validate model data"""
        # If not eligible, UNRECRUITED_REASON should be set
        if not self.is_eligible() and not self.UNRECRUITED_REASON:
            raise ValidationError({
                'UNRECRUITED_REASON': _('Reason not recruited is required when patient is not eligible')
            })
        
        # If UNRECRUITED_REASON is "OTHER", UNRECRUITED_REASON_OTHER must be filled
        if self.UNRECRUITED_REASON == 'OTHER' and not self.UNRECRUITED_REASON_OTHER:
            raise ValidationError({
                'UNRECRUITED_REASON_OTHER': _('Please specify the other reason')
            })
        
        # If UNRECRUITED_REASON is not "OTHER", clear UNRECRUITED_REASON_OTHER
        if self.UNRECRUITED_REASON and self.UNRECRUITED_REASON != 'OTHER':
            self.UNRECRUITED_REASON_OTHER = None
    
    def _generate_scrid(self) -> str:
        """
        Generate next SCRID for the site
        Format: PS-{SITEID}-{Number}
        Example: PS-003-0001, PS-011-0001
        Each site has its own numbering sequence
        """
        if not self.SITEID:
            raise ValueError("SITEID is required to generate SCRID")
        
        # Get max number for this SITEID
        max_scrid = (
            ScreeningCase.objects
            .filter(SCRID__startswith=f'PS-{self.SITEID}-')
            .extra(
                select={'scrid_num': f"CAST(SUBSTRING(SCRID FROM {len(self.SITEID) + 5}) AS INTEGER)"}
            )
            .aggregate(max_num=Max('scrid_num'))
        )
        
        max_num = max_scrid.get('max_num') or 0
        return f"PS-{self.SITEID}-{max_num + 1:04d}"
    
    def _generate_subjid(self) -> str:
        """
        Generate next SUBJID for the site
        Format: A-{Number} (e.g., A-001, A-002, A-003)
        Each site has independent SUBJID numbering
        Only generated when patient is eligible
        """
        if not self.SITEID:
            raise ValueError("SITEID is required to generate SUBJID")
        
        # Get max number for this SITEID (only from eligible cases)
        max_subjid = (
            ScreeningCase.objects
            .filter(
                SITEID=self.SITEID,
                SUBJID__startswith='A-',
                SUBJID__isnull=False,
                is_confirmed=True
            )
            .exclude(SUBJID='')
            .extra(
                select={'subjid_num': "CAST(SUBSTRING(SUBJID FROM 3) AS INTEGER)"}
            )
            .aggregate(max_num=Max('subjid_num'))
        )
        
        max_num = max_subjid.get('max_num') or 0
        return f"A-{max_num + 1:03d}"
    
    def _generate_unique_usubjid(self) -> str:
        """
        Generate unique USUBJID with collision handling
        Format: {SITEID}-A-{Number}
        Example: 003-A-001, 003-A-002, 011-A-001
        
        This combines:
        - SITEID (3 digits)
        - Prefix "A" (for Arm A or eligible patients)
        - Sequential number (3 digits)
        
        Only generated when patient is eligible for the study
        """
        if not self.SITEID or not self.SUBJID:
            raise ValueError("SITEID and SUBJID required to create USUBJID")
        
        # USUBJID = SITEID + "-" + SUBJID
        # Where SUBJID = A-{Number}
        # Result: 003-A-001, 003-A-002, etc.
        usubjid = f"{self.SITEID}-{self.SUBJID}"
        
        # Verify uniqueness (should always be unique if SUBJID is unique per site)
        if ScreeningCase.objects.filter(USUBJID=usubjid).exclude(pk=self.pk).exists():
            raise ValueError(
                f"USUBJID {usubjid} already exists. "
                f"This indicates a race condition or data integrity issue."
            )
        
        return usubjid
    
    def _generate_entry_number(self) -> int:
        """Generate next entry number"""
        max_entry = (
            ScreeningCase.objects
            .aggregate(max_entry=Max('ENTRY'))
        )
        return (max_entry.get('max_entry') or 0) + 1
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Optimized save with auto-fill entry metadata
        SCRID format: PS-{SITEID}-{Number} (e.g., PS-003-0001)
        
        Usage:
            # Method 1: Pass user directly (recommended)
            instance.save(user=request.user)
            
            # Method 2: Use middleware (see middleware.py)
            instance.save()  # Will auto-detect user from thread local
        """
        # Get user from kwargs or thread local
        user = kwargs.pop('user', None)
        
        if user is None:
            # Try to get from thread local (if middleware is set up)
            from threading import local
            _thread_locals = getattr(self.__class__, '_thread_locals', None)
            if _thread_locals and hasattr(_thread_locals, 'user'):
                user = _thread_locals.user
        
        # Validate SITEID is set before generating SCRID
        if not self.SITEID:
            raise ValueError("SITEID must be set before saving")
        
        # Auto-fill entry metadata ONLY on first save
        if not self.pk:  # New record
            if user and user.is_authenticated:
                self.USER_ENTRY = user.username
            
            if self.ENTRY is None:
                self.ENTRY = self._generate_entry_number()
            
            # Only ENTEREDTIME is auto-filled
            if self.ENTEREDTIME is None:
                self.ENTEREDTIME = timezone.now()
        
        # Generate SCRID if not exists (requires SITEID)
        if not self.SCRID:
            self.SCRID = self._generate_scrid()
        
        # Check eligibility and update accordingly
        if self.is_eligible():
            if not self.SUBJID:
                self.SUBJID = self._generate_subjid()
            
            if not self.USUBJID:
                self.USUBJID = self._generate_unique_usubjid()
            
            self.is_confirmed = True
        else:
            self.SUBJID = None
            self.USUBJID = None
            self.is_confirmed = False
        
        # Single save call
        super().save(*args, **kwargs)