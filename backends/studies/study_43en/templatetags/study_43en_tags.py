from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Lấy giá trị từ dictionary theo key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def count_performed(tests):
    """Đếm số lượng xét nghiệm đã thực hiện"""
    return len([t for t in tests if getattr(t, 'PERFORMED', False)])


TEST_UNITS = {
    # 11. Blood Coagulation
    'INR': '',
    'DIC': '(Yes/No)',
    
    # 12. Complete Blood Count
    'WBC': '(k/µl)',
    'NEU': '(%)',
    'LYM': '(%)',
    'EOS': '(%)',
    'RBC': '(M/µl)',
    'HEMOGLOBIN': '(g/dl)',
    'PLATELETS': '(k/µl)',
    
    # 13. Biochemistry & Immunology
    'NATRI': '(mmol/l)',
    'KALI': '(mmol/l)',
    'CLO': '(mmol/l)',
    'MAGNE': '(mmol/l)',
    'URE': '(mmol/l)',
    'CREATININE': '(µmol/l)',
    'AST': '(U/l)',
    'ALT': '(U/l)',
    'GLUCOSEBLOOD': '(mmol/l)',
    'BILIRUBIN_TP': '(µmol/l)',
    'BILIRUBIN_TT': '(µmol/l)',
    'PROTEIN': '(g/l)',
    'ALBUMIN': '(g/l)',
    'CRP_QUALITATIVE': '(Positive/Negative)',
    'CRP_QUANTITATIVE': '(mmol/l)',
    'CRP': '(mg/l)',
    'PROCALCITONIN': '(ng/ml)',
    'HBA1C': '(%)',
    'CORTISOL': '(µg/dl)',
    'HIV': '(Yes/No)',
    'CD4': '(cells/mm³)',
    
    # 14. Arterial Blood Gas
    'PH_BLOOD': '',
    'PCO2': '(mmHg)',
    'PO2': '(mmHg)',
    'HCO3': '(mmol/l)',
    'BE': '(mmol/l)',
    'AADO2': '(mmHg)',
    
    # 15. Arterial Lactate
    'LACTATE_ARTERIAL': '(mmol/l)',
    
    # 16. Urinalysis
    'PH': '',
    'NITRIT': '(Positive/Negative)',
    'URINE_PROTEIN': '(Positive/Negative)',
    'LEU': '(cells)',
    'URINE_RBC': '(cells/mm³)',
    'SEDIMENT': '',
    
    # 17. Peritoneal Fluid
    'PERITONEAL_WBC': '(cells/mm³)',
    'PERITONEAL_NEU': '(%)',
    'PERITONEAL_MONO': '(%)',
    'PERITONEAL_RBC': '(cells/mm³)',
    'PERITONEAL_PROTEIN': '(g/l)',
    'PERITONEAL_PROTEIN_BLOOD': '(g/l)',
    'PERITONEAL_ALBUMIN': '(g/l)',
    'PERITONEAL_ALBUMIN_BLOOD': '(g/l)',
    'PERITONEAL_ADA': '(U/l)',
    'PERITONEAL_CELLBLOCK': '',
    
    # 18. Pleural Fluid
    'PLEURAL_WBC': '(cells/mm³)',
    'PLEURAL_NEU': '(%)',
    'PLEURAL_MONO': '(%)',
    'PLEURAL_EOS': '(%)',  # ← Note: CRF doesn't show unit for Eos
    'PLEURAL_RBC': '(cells/mm³)',
    'PLEURAL_PROTEIN': '(g/l)',
    'PLEURAL_PROTEIN_BLOOD': '(g/l)',
    'PLEURAL_ALBUMIN': '(g/l)',  # ← CRF shows U/l but should be g/l
    'PLEURAL_ALBUMIN_BLOOD': '(g/l)',  # ← CRF shows U/l but should be g/l
    'PLEURAL_LDH': '(U/l)',
    'PLEURAL_LDH_BLOOD': '(U/l)',
    'PLEURAL_ADA': '(U/l)',
    'PLEURAL_CELLBLOCK': '',
    
    # 19. Cerebrospinal Fluid
    'CSF_WBC': '(cells/mm³)',
    'CSF_NEU': '(%)',
    'CSF_MONO': '(%)',
    'CSF_EOS': '(%)',
    'CSF_RBC': '(cells/mm³)',
    'CSF_PROTEIN': '(g/l)',
    'CSF_GLUCOSE': '(g/l)',
    'CSF_LACTATE': '(mmol/l)',
    'CSF_GRAM_STAIN': '',
    
    # 20-25. Imaging Studies
    'CHEST_XRAY': '',
    'ABDOMINAL_ULTRASOUND': '',
    'BRAIN_CT_MRI': '',
    'CHEST_ABDOMEN_CT': '',
    'ECHOCARDIOGRAPHY': '',
    'SOFT_TISSUE_ULTRASOUND': '',
}


@register.filter(name='get_test_unit')
def get_test_unit(test_type):
    """Get unit for a test type"""
    return TEST_UNITS.get(test_type, '')