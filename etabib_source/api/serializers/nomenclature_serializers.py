from enum import Enum

from rest_framework import serializers

from nomenclature.models import NABM, LOINC, FR18LinguisticVariant, AnswerList, Motif, SnomedD, SnomedP, SnomedF


class NomenclatureCat(Enum):
    SNOMED_D = (1, 6)  # Pair(Numenclature_id, Categorie_id)
    SNOMED_F = (2, 2)
    SNOMED_P = (3, 8)
    MOTIF = (4, None)


class FindNomenclatureSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=255, required=True)
    v = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)

    def save(self, **kwargs):
        q = self.validated_data['q']
        v = self.validated_data.get('v', None)

        out = []
        if v == "2":
            motifs = Motif.objects.filter(motif__icontains=q, active=True)[:20]
            for motif in motifs:
                d = dict()
                d['id'] = motif.id
                d['code_class'] = motif.code_class
                d['name_class'] = motif.name_class
                d['version_class'] = motif.version_class
                d['motif'] = motif.motif
                d['motif_ar'] = motif.motif_ar
                d['motif_en'] = motif.motif_en
                d['motif_es'] = motif.motif_es
                d['cat_id'] = motif.categorie.id
                d['cat_name'] = motif.categorie.designation
                d['nomc_id'] = NomenclatureCat.MOTIF.value[0]
                out.append(d)
        else:
            l = []
            snds = SnomedD.objects.filter(fnomen__istartswith=q)
            snfs = SnomedF.objects.filter(fnomen__istartswith=q)
            snps = SnomedP.objects.filter(fnomen__istartswith=q)
            # mtfs = Motif.objects.filter(motif__istartswith=q)[:5]
            l.extend(snds)
            l.extend(snfs)
            l.extend(snps)
            # l.extend(mtfs)
            for r in l[:15]:
                d = dict()
                if isinstance(r, SnomedD):
                    d['id'] = r.id
                    d['code'] = r.termcode
                    d['val'] = r.fnomen
                    d['cat_id'] = NomenclatureCat.SNOMED_D.value[1]
                    d['nomc_id'] = NomenclatureCat.SNOMED_D.value[0]
                if isinstance(r, SnomedP):
                    d['id'] = r.id
                    d['code'] = r.termcode
                    d['val'] = r.fnomen
                    d['cat_id'] = NomenclatureCat.SNOMED_P.value[1]
                    d['nomc_id'] = NomenclatureCat.SNOMED_P.value[0]
                if isinstance(r, SnomedF):
                    d['id'] = r.id
                    d['code'] = r.termcode
                    d['val'] = r.fnomen
                    d['cat_id'] = NomenclatureCat.SNOMED_P.value[1]
                    d['nomc_id'] = NomenclatureCat.SNOMED_P.value[0]
                if isinstance(r, Motif):
                    d['id'] = r.id
                    d['code'] = r.id
                    d['val'] = r.motif
                    d['cat_id'] = r.categorie.id
                    d['nomc_id'] = NomenclatureCat.MOTIF.value[0]
                out.append(d)
        return out


class NABMSerializer(serializers.ModelSerializer):
    class Meta:
        model = NABM
        fields = "__all__"


class LOINCSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOINC
        fields = "__all__"


class FR18LinguisticVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FR18LinguisticVariant
        fields = "__all__"

class MotifSerializer(serializers.ModelSerializer):
    cat_id = serializers.SerializerMethodField()
    cat_name = serializers.SerializerMethodField()
    nomc_id = serializers.SerializerMethodField()

    class Meta:
        model = Motif
        fields = (
        "id", "code_class", "name_class", "version_class", "motif", "motif_ar", "motif_en", "motif_es", "cat_id",
        "cat_name", "nomc_id")

    def get_cat_id(self, obj):
        return obj.categorie.id

    def get_cat_name(self, obj):
        return obj.categorie.designation

    def get_nomc_id(self, obj):
        return NomenclatureCat.MOTIF.value[0]
