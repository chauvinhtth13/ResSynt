import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ScreeningCase(models.Model):
    """
    Patient screening information
    Initial assessment for study eligibility
    """
    
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
    
    # Dates
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
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Reason Not Recruited')
    )
    
    # Location
    WARD = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Department')
    )
    
    # Metadata
    ENTRY = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Entry Number')
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True,
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
        ]
    
    def __str__(self):
        return self.USUBJID if self.USUBJID else f"PS{self.SCRID}"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate SCRID, SUBJID, and USUBJID based on eligibility
        USUBJID format: {SITEID}-{SUBJID} (e.g., 003-A-001)
        """
        # Generate SCRID if not exists
        if not self.SCRID:
            all_ids = ScreeningCase.objects.values_list('SCRID', flat=True)
            max_num = 0
            for sid in all_ids:
                m = re.match(r'PS(\d+)', str(sid))
                if m:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
            self.SCRID = f"PS{max_num + 1:04d}"
        
        # Initial save to get primary key
        super().save(*args, **kwargs)
        
        create_usubjid = False
        
        # Check eligibility and consent
        if (self.UPPER16AGE and 
            self.INFPRIOR2OR48HRSADMIT and
            self.ISOLATEDKPNFROMINFECTIONORBLOOD and 
            not self.KPNISOUNTREATEDSTABLE and
            self.CONSENTTOSTUDY):
            
            # Generate SUBJID if not exists
            if not self.SUBJID:
                last_case = (
                    ScreeningCase.objects
                    .filter(SITEID=self.SITEID)
                    .exclude(SUBJID__isnull=True)
                    .exclude(SUBJID__exact='')
                    .filter(SUBJID__startswith='A-')
                    .order_by('-SUBJID')
                    .first()
                )
                
                if last_case and last_case.SUBJID and last_case.SUBJID.startswith('A-'):
                    try:
                        last_number = int(last_case.SUBJID.split('-')[-1])
                        next_number = last_number + 1
                    except (ValueError, IndexError):
                        next_number = 1
                else:
                    next_number = 1
                
                self.SUBJID = f"A-{next_number:03d}"
            
            # Generate USUBJID if not exists
            if not self.USUBJID:
                create_usubjid = True
                if not self.SITEID or not self.SUBJID:
                    raise ValueError("SITEID and SUBJID required to create USUBJID")
                
                self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
                
                # Ensure unique USUBJID
                while ScreeningCase.objects.filter(USUBJID=self.USUBJID).exclude(pk=self.pk).exists():
                    try:
                        subjid_number = int(self.SUBJID.split('-')[-1])
                    except (ValueError, IndexError):
                        subjid_number = 1
                    
                    subjid_number += 1
                    self.SUBJID = f"A-{subjid_number:03d}"
                    self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
            
            self.is_confirmed = True
        else:
            # Not eligible - clear identifiers
            self.SUBJID = None
            self.USUBJID = None
            self.is_confirmed = False
        
        # Save again with updated fields
        super().save(*args, **kwargs)
        return create_usubjid