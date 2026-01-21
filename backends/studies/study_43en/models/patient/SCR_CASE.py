# backends/studies/study_43en/models/patient/Screening.py
import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from django.conf import settings


class SCR_CASE(AuditFieldsMixin):
    """
    Patient screening information
    
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
    # ELIGIBILITY CRITERIA
    # ==========================================
    UPPER16AGE = models.BooleanField(
        default=False,
        verbose_name=_('Age ≥16 years')
    )
    
    INFPRIOR2OR48HRSADMIT = models.BooleanField(
        default=False,
        verbose_name=_('Infection prior to or within 48h of admission')
    )
    
    ISOLATEDKPNFROMINFECTIONORBLOOD = models.BooleanField(
        default=False,
        verbose_name=_('KPN isolated from infection site or blood')
    )
    
    KPNISOUNTREATEDSTABLE = models.BooleanField(
        default=False,
        verbose_name=_('KPN untreated and stable')
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
    CONFIRMED = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_('Confirmed')
    )
    
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
    # LOCATION
    # ==========================================
    WARD = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Department')
    )
    
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'SCR_CASE'
        verbose_name = _('Patient Screening')
        verbose_name_plural = _('Patient Screenings')
        ordering = ['-SCREENINGFORMDATE', 'SITEID', 'SUBJID']
        indexes = [
            models.Index(fields=['SITEID', '-SCREENINGFORMDATE'], name='idx_scr_site_date'),
            models.Index(fields=['is_confirmed', 'SITEID'], name='idx_scr_confirmed'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_scr_modified'),
        ]
    
    def __str__(self):
        return self.USUBJID if self.USUBJID else f"PS{self.SCRID}"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate SCRID với format PS-SITEID-0001, SUBJID, và USUBJID based on eligibility
        
        Version increment is handled by AuditFieldsMixin.save()
        
        Returns:
            bool: True if USUBJID was created
        """
        create_usubjid = False
        
        # 1. Generate SCRID if not exists - FORMAT: PS0001 (per site)
        # Each site counts independently: Site 003 -> PS0001, PS0002...
        #                                  Site 020 -> PS0001, PS0002...
        if not self.SCRID:
            if not self.SITEID:
                raise ValueError("SITEID is required to generate SCRID")
            
            # 🚀 OPTIMIZED: Use database aggregation instead of fetching all records
            # Extract numeric part from SCRID (PS0001 -> 0001) and find max
            from django.db.models import Max, F, Value, IntegerField
            from django.db.models.functions import Substr, Cast, Length
            
            # Get max SCRID number for THIS SITE ONLY using database aggregation
            # This is MUCH faster than fetching all records and iterating
            max_scrid = SCR_CASE.objects.filter(
                SITEID=self.SITEID,
                SCRID__startswith='PS',
                SCRID__isnull=False
            ).exclude(
                SCRID__exact=''
            ).annotate(
                # Extract numeric part: SUBSTRING(SCRID FROM 3) -> '0001' from 'PS0001'
                scrid_num=Cast(
                    Substr('SCRID', 3),  # Skip 'PS' prefix
                    IntegerField()
                )
            ).aggregate(
                max_num=Max('scrid_num')
            )
            
            max_num = max_scrid['max_num'] or 0
            
            # Generate new SCRID: PS0001, PS0002, etc. (per site)
            self.SCRID = f"PS{max_num + 1:04d}"
        
        # 2. Check eligibility
        is_eligible = (
            self.UPPER16AGE and 
            self.INFPRIOR2OR48HRSADMIT and
            self.ISOLATEDKPNFROMINFECTIONORBLOOD and 
            not self.KPNISOUNTREATEDSTABLE and
            self.CONSENTTOSTUDY
        )
        
        # 3. Generate SUBJID and USUBJID if eligible
        if is_eligible:
            if not self.SUBJID:
                # 🚀 OPTIMIZED: Use database aggregation for SUBJID too
                from django.db.models import Max
                from django.db.models.functions import Substr, Cast
                from django.db.models import IntegerField
                
                max_subjid = SCR_CASE.objects.filter(
                    SITEID=self.SITEID,
                    SUBJID__startswith='A-',
                    SUBJID__isnull=False
                ).exclude(
                    SUBJID__exact=''
                ).annotate(
                    # Extract numeric part: SUBSTRING(SUBJID FROM 3) -> '001' from 'A-001'
                    subjid_num=Cast(
                        Substr('SUBJID', 3),  # Skip 'A-' prefix
                        IntegerField()
                    )
                ).aggregate(
                    max_num=Max('subjid_num')
                )
                
                next_number = (max_subjid['max_num'] or 0) + 1
                self.SUBJID = f"A-{next_number:03d}"
            
            if not self.USUBJID:
                create_usubjid = True
                if not self.SITEID or not self.SUBJID:
                    raise ValueError("SITEID and SUBJID required to create USUBJID")
                
                self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
                
                while SCR_CASE.objects.filter(USUBJID=self.USUBJID).exclude(pk=self.pk).exists():
                    try:
                        subjid_number = int(self.SUBJID.split('-')[-1])
                    except (ValueError, IndexError):
                        subjid_number = 1
                    
                    subjid_number += 1
                    self.SUBJID = f"A-{subjid_number:03d}"
                    self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
            
            self.is_confirmed = True
        else:
            self.SUBJID = None
            self.USUBJID = None
            self.is_confirmed = False
        
        super().save(*args, **kwargs)
        
        return create_usubjid