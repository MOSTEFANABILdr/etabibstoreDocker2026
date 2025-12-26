import uuid
from datetime import datetime

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from drugs.utils import PHONES, CODES


class DciAtc(models.Model):
    unique_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    designation_en = models.CharField(max_length=255, blank=True, null=True)
    designation_ar = models.CharField(max_length=255, blank=True, null=True)
    designation_sp = models.CharField(max_length=255, blank=True, null=True)
    designation_ch = models.CharField(max_length=255, blank=True, null=True)
    designation_de = models.CharField(max_length=255, blank=True, null=True)
    designation_nl = models.CharField(db_column='designation__nl', max_length=255, blank=True,
                                      null=True)
    designation_fr = models.CharField(max_length=255, blank=True, null=True)
    mpgrp = models.CharField(db_column='MPGRP', max_length=255, blank=True, null=True)
    ti = models.CharField(db_column='TI', max_length=255, blank=True, null=True)
    intro = models.TextField(db_column='INTRO', blank=True, null=True)
    posol = models.TextField(db_column='POSOL', blank=True, null=True)
    narcotic = models.CharField(db_column='Narcotic', max_length=255, blank=True, null=True)
    deleted = models.BooleanField(default=False)

    # this field is not a database field , it is used to quering and filtering from the related object
    logs = GenericRelation(
        "ChangeLog",
        object_id_field="source_id",
        content_type_field="source_type",
        related_query_name='dciatc'
    )

    def __str__(self):
        return self.designation_fr

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'dci_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)


class FormeHomogene(models.Model):
    unique_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.designation

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'frm_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)


class Interaction(models.Model):
    id = models.IntegerField(primary_key=True)
    type_interraction = models.CharField(max_length=25, blank=True, null=True)
    risque = models.CharField(max_length=422, blank=True, null=True)
    cat = models.CharField(max_length=461, blank=True, null=True)
    dci_atc_a = models.ForeignKey(DciAtc, models.DO_NOTHING, blank=True, null=True,
                                  related_name="interaction_dci_atc_a_set")
    dci_atc_b = models.ForeignKey(DciAtc, models.DO_NOTHING, blank=True, null=True,
                                  related_name="interaction_dci_atc_b_set")


class Laboratoire(models.Model):
    designation = models.CharField(max_length=255)
    pays = models.CharField(max_length=255)
    unique_id = models.CharField(max_length=255, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'labo_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)


class MedicCategorie(models.Model):
    unique_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'Medic_Cat_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.designation


class Medicament(models.Model):
    unique_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    pays_marche = models.ForeignKey('Pays', models.DO_NOTHING, db_column='pays_marche')
    dci_pays = models.CharField(max_length=255)
    dci_atc = models.ForeignKey(DciAtc, models.DO_NOTHING, to_field="unique_id", blank=True, null=True,
                                related_name='medicaments_dci_atc_new')
    nom_commercial = models.ForeignKey('NomCommercial', models.DO_NOTHING, to_field="unique_id", blank=True,
                                       null=True, related_name='medicaments_nom_commercial_new')
    num_enregistrement = models.CharField(max_length=25, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    forme = models.CharField(max_length=255, blank=True, null=True)
    dosage = models.CharField(max_length=255, blank=True, null=True)
    cond = models.CharField(max_length=255, blank=True, null=True)
    liste = models.CharField(max_length=64, blank=True, null=True)
    p1 = models.IntegerField(blank=True, null=True)
    p2 = models.IntegerField(blank=True, null=True)
    obs = models.CharField(max_length=255, blank=True, null=True)
    laboratoire = models.CharField(max_length=255, blank=True, null=True)
    note_medecin = models.CharField(max_length=255, blank=True, null=True)
    observation = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    duree_stabilitee = models.CharField(max_length=255, blank=True, null=True)
    remboursable = models.CharField(max_length=5, blank=True, null=True)
    forme_homogene = models.ForeignKey(FormeHomogene, models.DO_NOTHING, to_field="unique_id", blank=True,
                                       null=True, related_name='medicaments_forme_homogene_new')
    etat = models.IntegerField(blank=True, null=True)
    autorise = models.CharField(max_length=5, blank=True, null=True)
    date_retrait = models.CharField(max_length=255, blank=True, null=True)
    motif_retrait = models.TextField(blank=True, null=True)
    categorie = models.ForeignKey(MedicCategorie, models.DO_NOTHING, to_field="unique_id", blank=True, null=True,
                                  related_name='medicaments_categorie_new')
    pays_labo = models.CharField(max_length=255, blank=True, null=True)
    labo = models.ForeignKey(Laboratoire, models.DO_NOTHING, to_field="unique_id", blank=True, null=True,
                             related_name='medicaments_labo_new')
    deleted = models.BooleanField(default=False)

    # this field is not a database field , it is used to quering and filtering from the related object
    logs = GenericRelation(
        "ChangeLog",
        object_id_field="source_id",
        content_type_field="source_type",
        related_query_name='medicament'
    )

    @property
    def country(self):
        if self.pays_labo and self.pays_labo in PHONES:
            pays_code = CODES[PHONES.index(self.pays_labo)]
            if pays_code:
                return pays_code
        if "/" in self.num_enregistrement:
            labo = Laboratoire.objects.filter(unique_id=self.num_enregistrement.split("/")[0]).first()
            pays_code = CODES[PHONES.index(labo.pays)] if labo else None
            if pays_code:
                return pays_code
        return None

    @property
    def image(self):
        return "drugs/image/%s.png" % (self.forme_homogene)

    @property
    def name_laboratoire(self):
        lab = Laboratoire.objects.filter(unique_id=self.num_enregistrement.split("/")[0]).first()
        return lab.designation

    @property
    def forme_posologie(self):
        if self.forme_homogene.designation == "AUTRE" or self.forme_homogene.designation == "BUV" \
                or self.forme_homogene.designation == "POUDRE" or self.forme_homogene.designation == "SPRAY":
            result = "dose"
        elif self.forme_homogene.designation == "COMP":
            result = "comp"
        elif self.forme_homogene.designation == "DROP":
            result = "gtte"
        elif self.forme_homogene.designation == "INJ":
            result = "Amp"
        elif self.forme_homogene.designation == "POMMADE":
            result = "application"
        elif self.forme_homogene.designation == "SUPPO":
            result = "supp"
        elif self.forme_homogene.designation == "DISPO" or self.forme_homogene.designation == "PANS":
            result = "usage"
        elif self.forme_homogene.designation == "SOINS":
            result = "soins"
        elif self.forme_homogene.designation == "INFU":
            result = "infusion"
        return result

    def __str__(self):
        return "%s: %s - %s" % (
            self.unique_id, self.nom_commercial.nom_fr if self.nom_commercial else "", self.dci_pays)

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'med_{uuid.uuid4().hex}'
        qr = ""
        super().save(*args, **kwargs)


class NomCommercial(models.Model):
    unique_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    nom_fr = models.CharField(max_length=255, blank=True, null=True)
    nom_ar = models.CharField(max_length=255, blank=True, null=True)
    nom_en = models.CharField(max_length=255, blank=True, null=True)
    nom_sp = models.CharField(max_length=255, blank=True, null=True)
    nom_de = models.CharField(max_length=255, blank=True, null=True)
    nom_ch = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(default=False)

    # this field is not a database field , it is used to quering and filtering from the related object
    logs = GenericRelation(
        "ChangeLog",
        object_id_field="source_id",
        content_type_field="source_type",
        related_query_name='nomcommercial'
    )

    def __str__(self):
        return self.nom_fr

    @property
    def nomcommercial_formes(self):
        qs = Medicament.objects.filter(nom_commercial=self)
        formes = dict()
        for medic in qs:
            if medic.forme_homogene.designation not in formes:
                # init list
                formes[medic.forme_homogene.designation] = list()
            formes[medic.forme_homogene.designation].append(medic.pk)
        return {'formes': formes}

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'nc_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)


class Pays(models.Model):
    code_pays = models.CharField(max_length=10, blank=True, null=True)
    designation_fr = models.CharField(max_length=255)
    en = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "%s %s" % (self.code_pays, self.designation_fr)


class Stock(models.Model):
    professionnel_sante = models.ForeignKey('core.ProfessionnelSante', on_delete=models.PROTECT)
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    valide = models.BooleanField(default=True)
    date_update = models.DateTimeField(blank=True)

    def save(self, *args, **kwargs):
        self.date_update = datetime.now()
        super().save(*args, **kwargs)


class CodeAtc(models.Model):
    designation = models.CharField(max_length=255, null=True, blank=True)
    dciAtc = models.ForeignKey(DciAtc, models.DO_NOTHING, to_field="unique_id", blank=True, null=True,
                               related_name='codeatc_dci_atc_new')
    ddd = models.FloatField(null=True, blank=True)
    ddu = models.CharField(max_length=5, null=True, blank=True)
    ti = models.CharField(max_length=255, null=True, blank=True)
    intro = models.TextField(null=True, blank=True)
    narcotic = models.IntegerField(null=True, blank=True)
    unique_id = models.CharField(unique=True, max_length=255, null=True, blank=True)
    link = models.CharField(max_length=255, null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        import uuid
        if not self.unique_id:
            self.unique_id = f'ca_{uuid.uuid4().hex}'
        super().save(*args, **kwargs)


class MedicamentCnasForme(models.Model):
    code = models.IntegerField(unique=True)
    libelle = models.CharField(max_length=255, null=True, blank=True)
    libelle_court = models.CharField(max_length=255, null=True, blank=True)


class MedicamentCnas(models.Model):
    n_enregistrement = models.CharField(unique=True, max_length=255, null=True, blank=True)
    nom_commercial = models.CharField(max_length=255, null=True, blank=True)
    nom_dci = models.CharField(max_length=255, null=True, blank=True)
    dosage = models.CharField(max_length=255, null=True, blank=True)
    unite = models.CharField(max_length=255, null=True, blank=True)
    conditionnement = models.CharField(max_length=255, null=True, blank=True)
    convention = models.CharField(max_length=255, null=True, blank=True)
    remboursable = models.CharField(max_length=255, null=True, blank=True)
    date_remboursement = models.CharField(max_length=255, null=True, blank=True)
    date_arret_remboursement = models.CharField(max_length=255, null=True, blank=True)
    date_decision = models.CharField(max_length=255, null=True, blank=True)
    tarif_de_reference = models.CharField(max_length=255, null=True, blank=True)
    taux = models.CharField(max_length=255, null=True, blank=True)
    forme = models.IntegerField(null=True, blank=True)
    tableau = models.CharField(max_length=255, null=True, blank=True)
    hopital = models.CharField(max_length=255, null=True, blank=True)
    secteur_sanitaire = models.CharField(max_length=255, null=True, blank=True)
    officine = models.CharField(max_length=255, null=True, blank=True)
    pays = models.CharField(max_length=255, null=True, blank=True)
    laboratoire = models.CharField(max_length=255, null=True, blank=True)
    cm = models.CharField(max_length=255, null=True, blank=True)
    code_medic = models.CharField(max_length=255, null=True, blank=True)
    date_tr = models.CharField(max_length=255, null=True, blank=True)
    observation = models.TextField(null=True, blank=True)
    code_dci = models.CharField(max_length=255, null=True, blank=True)
    inf_tr = models.CharField(max_length=255, null=True, blank=True)
    generic = models.CharField(max_length=255, null=True, blank=True)

    @property
    def forme_cnas(self):
        form = MedicamentCnasForme.objects.filter(code=self.forme)
        if form.exist():
            return form.first().libelle

    def __str__(self):
        return f'{self.n_enregistrement} {self.nom_commercial}'


class MapCnas(models.Model):
    REMB_CHOICES = (
        ("O", "O"),
        ("H", "H"),
        ("N", "N"),
    )
    medicamentcnas = models.ForeignKey(MedicamentCnas, to_field="n_enregistrement", on_delete=models.CASCADE,
                                       blank=True, null=True)
    medicament = models.OneToOneField(Medicament, to_field="unique_id", on_delete=models.CASCADE)
    remborsable = models.CharField(max_length=5, blank=True, null=True, choices=REMB_CHOICES)

    # this field is not a database field , it is used to quering and filtering from the related object
    logs = GenericRelation(
        "ChangeLog",
        related_query_name='mapcnas',
        object_id_field="source_id",
        content_type_field="source_type",
    )


class Amm(models.Model):
    medicament = models.ForeignKey(Medicament, to_field="unique_id", on_delete=models.CASCADE)
    amm = models.CharField(max_length=255, blank=True, null=True)
    date_retrait = models.CharField(max_length=255, blank=True, null=True)
    motif_retrait = models.CharField(max_length=255, blank=True, null=True)


class Prescription(models.Model):
    medecin = models.ForeignKey("core.Medecin", on_delete=models.CASCADE)
    patient = models.ForeignKey("core.Patient", on_delete=models.CASCADE, null=True, blank=True)
    numero = models.CharField(max_length=255, unique=True, editable=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)


class MedicPrescription(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)
    posologie = models.CharField(max_length=255)


class MapAutorise(models.Model):
    AUTORISE_CHOICES = (
        ("NR", "NR"),
        ("A", "A"),
        ("R", "R"),
    )
    medicament = models.OneToOneField(Medicament, to_field="unique_id", on_delete=models.CASCADE)
    autorise = models.CharField(max_length=5, blank=True, null=True, choices=AUTORISE_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    # this field is not a database field , it is used to quering and filtering from the related object
    logs = GenericRelation(
        "ChangeLog",
        object_id_field="source_id",
        content_type_field="source_type",
        related_query_name='mapautorise'
    )


class ChangeLog(models.Model):
    """
    THIS model is used to store changes made in drugs app models
    THEN eTabib Worksapce will update their drugs tables according
    to changes made here
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')
    fields = models.JSONField(blank=True, null=True)
    date_mise_a_jour = models.DateTimeField(auto_now_add=True)


class ChangeDrugs(models.Model):
    """
    THIS model is used to store changes made in drugs app models
    THEN eTabib Worksapce will update their drugs tables according
    to changes made here
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(max_length=3000, blank=False, null=False)
    date_mise_a_jour = models.DateTimeField(auto_now_add=True)
