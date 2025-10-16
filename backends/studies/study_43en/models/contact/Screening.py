from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ScreeningContact(models.Model):
    """
    Contact screening information
    Tracks contacts of enrolled patients for screening eligibility
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary identifier
    SCRID = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name=_('Screening ID')
    )
    
    # Subject identifiers
    USUBJID = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Unique Subject ID')
    )
    
    SUBJID = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Subject ID')
    )
    
    INITIAL = models.CharField(
        max_length=10,
        verbose_name=_('Initials')
    )
    
    # Study information
    EVENT = models.CharField(
        max_length=50,
        default='CONTACT',
        verbose_name=_('Event')
    )
    
    STUDYID = models.CharField(
        max_length=10,
        default='43EN',
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=5,
        db_index=True,
        verbose_name=_('Site ID')
    )
    
    # Related enrolled patient
    SUBJIDENROLLSTUDY = models.ForeignKey('ScreeningCase',
        on_delete=models.CASCADE,
        related_name='contacts',
        to_field='USUBJID',
        verbose_name=_('Related Patient')
    )
    
    # Eligibility criteria
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
    
    # Dates
    SCREENINGFORMDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Screening Date')
    )
    
    COMPLETEDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    # Metadata
    ENTRY = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Entry Number')
    )
    
    ENTEREDTIME = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Entry Time')
    )
    
    is_confirmed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Confirmed')
    )
    
    class Meta:
        db_table = 'Contact_SCR_Case'
        verbose_name = _('Contact Screening')
        verbose_name_plural = _('Contact Screenings')
        ordering = ['-SCREENINGFORMDATE', 'SITEID', 'SUBJID']
        indexes = [
            models.Index(fields=['SITEID', '-SCREENINGFORMDATE'], name='idx_sc_site_date'),
            models.Index(fields=['is_confirmed', 'SITEID'], name='idx_sc_confirmed_site'),
        ]
    
    def __str__(self):
        return self.USUBJID if self.USUBJID else f"CS-{self.SCRID}"
    
    def save(self, *args, **kwargs):
        """Auto-generate SCRID and USUBJID if eligible"""
        # Generate SCRID if not exists
        if not self.SCRID:
            last_screening = ScreeningContact.objects.order_by('-SCRID').first()
            if last_screening and last_screening.SCRID and last_screening.SCRID.startswith('CS-'):
                try:
                    last_num = int(last_screening.SCRID[3:])
                    self.SCRID = f"CS-{last_num + 1:03d}"
                except ValueError:
                    self.SCRID = "CS-001"
            else:
                self.SCRID = "CS-001"
        
        # Generate USUBJID if meets eligibility criteria
        create_usubjid = False
        if (self.LIVEIN5DAYS3MTHS and self.MEALCAREONCEDAY and 
            self.CONSENTTOSTUDY and self.SUBJIDENROLLSTUDY):
            
            if not self.USUBJID:
                create_usubjid = True
                
                # Ensure SITEID exists
                if not hasattr(self, 'SITEID') or not self.SITEID:
                    self.SITEID = self.SUBJIDENROLLSTUDY.SITEID
                
                # Get related patient USUBJID (e.g., 003-A-003)
                related_usubjid = self.SUBJIDENROLLSTUDY.USUBJID
                
                # Parse and transform: A -> B
                parts = related_usubjid.split('-')
                if len(parts) == 3 and parts[1] == 'A':
                    contact_usubjid_base = f"{parts[0]}-B-{parts[2]}"
                else:
                    contact_usubjid_base = related_usubjid.replace('-A-', '-B-', 1)
                
                # Get next index
                existing_contacts = ScreeningContact.objects.filter(
                    USUBJID__startswith=contact_usubjid_base + '-'
                ).count()
                next_index = existing_contacts + 1
                
                # Generate unique USUBJID
                self.USUBJID = f"{contact_usubjid_base}-{next_index}"
                while ScreeningContact.objects.filter(USUBJID=self.USUBJID).exists():
                    next_index += 1
                    self.USUBJID = f"{contact_usubjid_base}-{next_index}"
                
                # Generate SUBJID
                if not self.SUBJID:
                    self.SUBJID = f"B-{parts[2]}-{next_index}"
                
                self.is_confirmed = True
        
        super().save(*args, **kwargs)
        return create_usubjid