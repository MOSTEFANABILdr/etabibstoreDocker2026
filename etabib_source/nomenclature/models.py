from django.db import models


class Links(models.Model):
    motif = models.ForeignKey('Motif', models.DO_NOTHING, blank=True, null=True)
    snomed_d = models.ForeignKey('SnomedD', models.DO_NOTHING, blank=True, null=True)
    snomed_f = models.ForeignKey('SnomedF', models.DO_NOTHING, blank=True, null=True)
    snomed_p = models.ForeignKey('SnomedP', models.DO_NOTHING, blank=True, null=True)


class Motif(models.Model):
    code_class = models.CharField(max_length=255, blank=True, null=True)
    name_class = models.CharField(max_length=255, blank=True, null=True)
    version_class = models.CharField(max_length=255, blank=True, null=True)
    abrev = models.CharField(max_length=255, blank=True, null=True)
    motif = models.CharField(max_length=1000, blank=True, null=True)
    motif_en = models.CharField(max_length=1000, blank=True, null=True)
    motif_ar = models.CharField(max_length=1000, blank=True, null=True)
    motif_es = models.CharField(max_length=1000, blank=True, null=True)
    definition = models.TextField(blank=True, null=True)
    categorie = models.ForeignKey('MotifCategorie', models.DO_NOTHING)
    code_map = models.CharField(max_length=255, blank=True, null=True)
    map_to = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True, blank=True, null=True)

    def __str__(self):
        return self.motif


class MotifCategorie(models.Model):
    designation = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.designation


class SnomedD(models.Model):
    termcode = models.CharField(db_column='TERMCODE', max_length=255, blank=True, null=True)
    fmod = models.CharField(db_column='FMOD', max_length=255, blank=True, null=True)
    fclass = models.CharField(db_column='FCLASS', max_length=255, blank=True, null=True)
    fnomen = models.CharField(db_column='FNOMEN', max_length=255, blank=True, null=True)
    reference = models.CharField(db_column='REFERENCE', max_length=255, blank=True, null=True)
    icdcode = models.CharField(db_column='ICDCODE', max_length=255, blank=True, null=True)
    icd10 = models.CharField(db_column='ICD10', max_length=255, blank=True, null=True)
    icd10_e = models.CharField(db_column='ICD10_E', max_length=255, blank=True, null=True)
    icdref = models.CharField(db_column='ICDREF', max_length=255, blank=True, null=True)
    sno2 = models.CharField(db_column='SNO2', max_length=255, blank=True, null=True)


class SnomedF(models.Model):
    termcode = models.CharField(db_column='TERMCODE', max_length=255, blank=True, null=True)
    fmod = models.CharField(db_column='FMOD', max_length=255, blank=True, null=True)
    fclass = models.CharField(db_column='FCLASS', max_length=255, blank=True, null=True)
    fnomen = models.CharField(db_column='FNOMEN', max_length=255, blank=True, null=True)
    reference = models.CharField(db_column='REFERENCE', max_length=255, blank=True, null=True)
    icdcode = models.CharField(db_column='ICDCODE', max_length=255, blank=True, null=True)
    icd10 = models.CharField(db_column='ICD10', max_length=255, blank=True, null=True)
    icd10_e = models.CharField(db_column='ICD10_E', max_length=255, blank=True, null=True)
    sno2 = models.CharField(db_column='SNO2', max_length=255, blank=True, null=True)
    iub = models.CharField(db_column='IUB', max_length=255, blank=True, null=True)


class SnomedP(models.Model):
    termcode = models.CharField(db_column='TERMCODE', max_length=255, blank=True, null=True)
    fmod = models.CharField(db_column='FMOD', max_length=255, blank=True, null=True)
    fclass = models.CharField(db_column='FCLASS', max_length=255, blank=True, null=True)
    fnomen = models.CharField(db_column='FNOMEN', max_length=255, blank=True, null=True)
    reference = models.CharField(db_column='REFERENCE', max_length=255, blank=True, null=True)
    icdcode = models.CharField(db_column='ICDCODE', max_length=255, blank=True, null=True)
    sno2 = models.CharField(db_column='SNO2', max_length=255, blank=True, null=True)


class Dictionary(models.Model):
    code_class = models.CharField(max_length=255, blank=True, null=True)
    abrev = models.CharField(max_length=255, blank=True, null=True)
    designation_fr = models.CharField(max_length=255, blank=True, null=True)
    designation_en = models.CharField(max_length=255, blank=True, null=True)
    designation_ar = models.CharField(max_length=255, blank=True, null=True)
    designation_es = models.CharField(max_length=255, blank=True, null=True)
    categorie = models.ForeignKey(MotifCategorie, models.DO_NOTHING, blank=True, null=True)
    resume = models.TextField(blank=True, null=True)
    code_map = models.CharField(max_length=255, blank=True, null=True)
    map_to = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Dictionnaire"
        verbose_name_plural = "Dictionnaire"


class LOINC(models.Model):
    loinc_num = models.CharField(max_length=10, blank=True, primary_key=True)
    component = models.CharField(max_length=255, null=True, blank=True)
    property = models.CharField(max_length=255, null=True, blank=True)
    time_aspct = models.CharField(max_length=255, null=True, blank=True)
    system = models.CharField(max_length=255, null=True, blank=True)
    scale_typ = models.CharField(max_length=255, null=True, blank=True)
    metho_typ = models.CharField(max_length=255, null=True, blank=True)
    # Original name is class not class_name (class is pythonic keyword)
    class_name = models.CharField(max_length=255, null=True, blank=True)
    class_type = models.CharField(max_length=255, null=True, blank=True)
    long_common_name = models.CharField(max_length=255, null=True, blank=True)
    short_name = models.CharField(max_length=255, null=True, blank=True)
    external_copyright_notice = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    version_first_released = models.CharField(max_length=255, null=True, blank=True)
    version_last_changed = models.CharField(max_length=255, null=True, blank=True)



class PanelsAndForms(models.Model):
    parent_id = models.IntegerField(null=True, blank=True)
    parent_loinc = models.ForeignKey(LOINC, null=True, blank=True
                                     , on_delete=models.PROTECT, related_name='child_panels')
    parent_name = models.CharField(max_length=255, null=True, blank=True)
    id_panel = models.IntegerField(null=True, blank=True)
    sequence = models.IntegerField(null=True, blank=True)
    loinc = models.ForeignKey(LOINC, null=True, blank=True
                              , on_delete=models.PROTECT, related_name='panels')
    loinc_name = models.CharField(max_length=255, null=True, blank=True)
    display_name_for_form = models.CharField(max_length=255, null=True, blank=True)
    observation_required_in_panel = models.CharField(max_length=255, null=True, blank=True)
    observation_id_in_form = models.CharField(max_length=255, null=True, blank=True)
    skip_logic_help_text = models.TextField(null=True, blank=True)
    default_value = models.CharField(max_length=100, null=True, blank=True)
    entry_type = models.CharField(max_length=3, null=True, blank=True)
    data_type_in_form = models.CharField(max_length=100, null=True, blank=True)
    data_type_source = models.CharField(max_length=100, null=True, blank=True)
    answer_sequence_override = models.CharField(max_length=10, null=True, blank=True)
    condition_for_inclusion = models.CharField(max_length=255, null=True, blank=True)
    allowable_alternative = models.CharField(max_length=100, null=True, blank=True)
    observation_category = models.CharField(max_length=100, null=True, blank=True)
    context = models.TextField(null=True, blank=True)
    consistency_checks = models.TextField(null=True, blank=True)
    relevance_equation = models.CharField(max_length=255, null=True, blank=True)
    coding_instructions = models.TextField(null=True, blank=True)
    question_cardinality = models.CharField(max_length=100, null=True, blank=True)
    answer_cardinality = models.CharField(max_length=100, null=True, blank=True)
    answer_list_id_override = models.CharField(max_length=14, null=True, blank=True)
    answer_list_type_override = models.CharField(max_length=20, null=True, blank=True)
    external_copyright_notice = models.TextField(null=True, blank=True)


class LoincAnswerListLink(models.Model):
    loinc_number = models.ForeignKey(LOINC, null=True, blank=True
                                     , on_delete=models.PROTECT, related_name='answer_link_list')
    long_common_name = models.CharField(max_length=255, null=True, blank=True)
    answer_list_id = models.CharField(max_length=20, null=True, blank=True)
    answer_list_name = models.CharField(max_length=255, null=True, blank=True)
    answer_list_link_type = models.CharField(max_length=100, null=True, blank=True)
    applicable_context = models.CharField(max_length=10, blank=True, null=True)


class AnswerList(models.Model):
    # answer_list_id a unique identifier for each LOINC answer list that begins with the prefix "LL"
    answer_list = models.CharField(max_length=10, null=True, blank=True)
    # answer_string_id uniquely identifies an answer string and starts with the prefix "LA"
    answer_string_id = models.CharField(max_length=20, null=True, blank=True)
    answer_list_name = models.CharField(max_length=255, null=True, blank=True)
    answer_list_oid = models.CharField(max_length=255, null=True, blank=True)
    ext_defined_yn = models.CharField(max_length=10, null=True, blank=True)
    ext_defined_answer_list_code_system = models.CharField(max_length=255, null=True, blank=True)
    ext_defined_answer_list_link = models.CharField(max_length=255, null=True, blank=True)
    local_answer_code = models.CharField(max_length=255, null=True, blank=True)
    local_answer_code_system = models.CharField(max_length=255, null=True, blank=True)
    sequence_number = models.CharField(max_length=5, null=True, blank=True)
    display_text = models.CharField(max_length=255, null=True, blank=True)
    ext_code_id = models.CharField(max_length=255, null=True, blank=True)
    ext_code_display_name = models.CharField(max_length=255, null=True, blank=True)
    ext_code_system = models.CharField(max_length=255, null=True, blank=True)
    ext_code_system_version = models.CharField(max_length=255, null=True, blank=True)
    ext_code_system_copyright_notice = models.TextField(null=True, blank=True)
    subsequent_text_prompt = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    score = models.CharField(max_length=255, null=True, blank=True)


class FR18LinguisticVariant(models.Model):
    loinc_num = models.ForeignKey(LOINC, null=True, blank=True, on_delete=models.PROTECT)
    component = models.CharField(max_length=255, null=True, blank=True)
    property = models.CharField(max_length=255, null=True, blank=True)
    time_aspct = models.CharField(max_length=255, null=True, blank=True)
    system = models.CharField(max_length=255, null=True, blank=True)
    scale_typ = models.CharField(max_length=255, null=True, blank=True)
    method_typ = models.CharField(max_length=255, null=True, blank=True)
    # Original name is class not class_name (class is pythonic keyword)
    class_name = models.CharField(max_length=255, null=True, blank=True)
    class_type = models.CharField(max_length=255, null=True, blank=True)
    long_common_name = models.CharField(max_length=255, null=True, blank=True)
    short_name = models.CharField(max_length=255, null=True, blank=True)
    external_copyright_notice = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    version_first_released = models.CharField(max_length=255, null=True, blank=True)
    version_last_changed = models.CharField(max_length=255, null=True, blank=True)
    related_names_2 = models.CharField(max_length=255, null=True, blank=True)
    linguistic_variant_display_name = models.CharField(max_length=255, null=True, blank=True)


class NABM(models.Model):
    code = models.IntegerField(primary_key=True, blank=True)
    chapitre = models.IntegerField(null=True, blank=True)
    sous_chapitre = models.IntegerField(null=True, blank=True)
    coefficient_b = models.IntegerField(null=True, blank=True)
    date_creation = models.DateField(null=True, blank=True)
    libelle = models.CharField(max_length=255, null=True, blank=True)
    entente_prealable = models.BooleanField(null=True, blank=True)
    remboursement_100 = models.BooleanField(null=True, blank=True)
    nbr_maxi_de_code = models.IntegerField(null=True, blank=True)
    n_regle_specifique = models.IntegerField(null=True, blank=True)
    ref_indication_medicale = models.BooleanField(null=True, blank=True)
    actes_reserves = models.BooleanField(null=True, blank=True)
    initiative_biologiste = models.BooleanField(null=True, blank=True)
    contingence_technique = models.IntegerField(null=True, blank=True)
    rmo = models.BooleanField(null=True, blank=True)
    examen_sanguin = models.BooleanField(null=True, blank=True)
    derniere_date_effet = models.DateField(null=True, blank=True)
    codes_incompatibles = models.CharField(max_length=255, null=True, blank=True)


class NABM_LOINC(models.Model):
    nabm = models.ForeignKey(NABM, null=True, blank=True, on_delete=models.PROTECT)
    loinc = models.ForeignKey(LOINC, null=True, blank=True, on_delete=models.PROTECT)
