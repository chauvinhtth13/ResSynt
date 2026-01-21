# backends/studies/study_43en/models/contact/Screening.py
import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class SCR_CONTACT(AuditFieldsMixin):
    """
    Contact screening information
    
    Inherits from AuditFieldsMixin:
    - version: Optimistic locking version control
    - last_modified_by_id: User ID who last modified
    - last_modified_by_username: Username backup for audit
    - last_modified_at: Timestamp of last modification
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY IDENTIFIERS
    # ==========================================
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
        verbose_name=_('Unique Subject ID')
    )
    
    # ==========================================
    # STUDY INFORMATION
    # ==========================================
    STUDYID = models.CharField(
        max_length=50,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=20,
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
        verbose_name=_('Initial')
    )
    
    # ==========================================
    # RELATED PATIENT
    # ==========================================
    SUBJIDENROLLSTUDY = models.ForeignKey(
        'SCR_CASE',
        on_delete=models.CASCADE,
        related_name='contacts',
        db_column='SUBJIDENROLLSTUDY',
        to_field='USUBJID',
        verbose_name=_('Related Patient')
    )
    
    # ==========================================
    # ELIGIBILITY CRITERIA (Contact-specific - 3 criteria)
    # ==========================================
    LIVEIN5DAYS3MTHS = models.BooleanField(
        default=False,
        verbose_name=_('Lived together ≥5 days in last 3 months')
    )
    
    MEALCAREONCEDAY = models.BooleanField(
        default=False,
        verbose_name=_('Shared meals/care ≥1 time per day')
    )
    
    CONSENTTOSTUDY = models.BooleanField(
        default=False,
        verbose_name=_('Consent to participate')
    )
    
    # ==========================================
    # DATES
    # ==========================================
    SCREENINGFORMDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Screening Form Date')
    )
    
    # ==========================================
    # STATUS
    # ==========================================
    is_confirmed = models.BooleanField(
        default=False,
        verbose_name=_('Is Confirmed')
    )
    
    UNRECRUITED_REASON = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Reason Not Recruited')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'SCR_CONTACT'
        verbose_name = _('Contact Screening')
        verbose_name_plural = _('Contact Screenings')
        ordering = ['-SCREENINGFORMDATE', 'SITEID', 'SUBJID']
        indexes = [
            models.Index(fields=['SITEID', '-SCREENINGFORMDATE'], name='idx_csc_site_date'),
            models.Index(fields=['is_confirmed', 'SITEID'], name='idx_csc_confirmed'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_csc_modified'),
        ]
    
    def __str__(self):
        return self.USUBJID if self.USUBJID else f"CS{self.SCRID}"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate SCRID với format CS0001 (đếm riêng theo từng site), SUBJID, and USUBJID based on eligibility
        
        Version increment is handled by AuditFieldsMixin.save()
        
        Returns:
            bool: True if USUBJID was created
        """
        create_usubjid = False
        
        # 1. Generate SCRID if not exists - NEW FORMAT: CS0001 (per site)
        if not self.SCRID:
            if not self.SITEID:
                raise ValueError("SITEID is required to generate SCRID")
            
            # Get all existing SCRIDs for this site only
            # Filter by contacts that belong to this site
            site_contacts = SCR_CONTACT.objects.filter(
                SITEID=self.SITEID
            ).values_list('SCRID', flat=True)
            
            max_num = 0
            for sid in site_contacts:
                # Extract number from CS0001 format
                m = re.match(r'CS(\d+)', str(sid))
                if m:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
            
            # Generate new SCRID with format CS0001 (unique per site)
            self.SCRID = f"CS{max_num + 1:04d}"
        
        # 2. Check eligibility (3 criteria for contacts)
        is_eligible = (
            self.LIVEIN5DAYS3MTHS and 
            self.MEALCAREONCEDAY and
            self.CONSENTTOSTUDY
        )
        
        # 3. Generate SUBJID and USUBJID if eligible
        if is_eligible:
            if not self.SUBJID:
                # Get related patient's SUBJID (e.g., A-001)
                related_usubjid = self.SUBJIDENROLLSTUDY.USUBJID
                parts = related_usubjid.split('-')  # ['003', 'A', '001']
                patient_number = parts[2]  # '001'
                
                # Count existing contacts for this patient
                last_contact = (
                    SCR_CONTACT.objects
                    .filter(SITEID=self.SITEID)
                    .exclude(SUBJID__isnull=True)
                    .exclude(SUBJID__exact='')
                    .filter(SUBJID__startswith=f'B-{patient_number}-')
                    .order_by('-SUBJID')
                    .first()
                )
                
                if last_contact and last_contact.SUBJID:
                    try:
                        # B-001-2 → get 2
                        last_index = int(last_contact.SUBJID.split('-')[-1])
                        next_index = last_index + 1
                    except (ValueError, IndexError):
                        next_index = 1
                else:
                    next_index = 1
                
                self.SUBJID = f"B-{patient_number}-{next_index}"
            
            if not self.USUBJID:
                create_usubjid = True
                if not self.SITEID or not self.SUBJID:
                    raise ValueError("SITEID and SUBJID required to create USUBJID")
                
                self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
                
                # Ensure uniqueness
                while SCR_CONTACT.objects.filter(USUBJID=self.USUBJID).exclude(pk=self.pk).exists():
                    try:
                        subjid_parts = self.SUBJID.split('-')
                        subjid_index = int(subjid_parts[-1])
                    except (ValueError, IndexError):
                        subjid_index = 1
                    
                    subjid_index += 1
                    self.SUBJID = f"B-{subjid_parts[1]}-{subjid_index}"
                    self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
            
            self.is_confirmed = True
        else:
            self.SUBJID = None
            self.USUBJID = None
            self.is_confirmed = False
        
        super().save(*args, **kwargs)
        
        return create_usubjid