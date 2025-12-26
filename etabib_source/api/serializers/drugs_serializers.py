from rest_framework import serializers

from drugs.models import ChangeLog, Medicament, NomCommercial, DciAtc, MapAutorise, MapCnas, ChangeDrugs


class ChageLogSerializer(serializers.Serializer):
    uuid = serializers.CharField(max_length=255)

    def save(self):
        uuid = self.validated_data['uuid']
        logs = None
        out = []
        if uuid == "NEW":
            logs = ChangeLog.objects.all().order_by("date_mise_a_jour")
        else:
            temp = ChangeLog.objects.filter(id=uuid)
            if temp.exists():
                logs = ChangeLog.objects.filter(date_mise_a_jour__gt=temp.first().date_mise_a_jour).order_by(
                    "date_mise_a_jour")
        if logs:
            for l in logs[:20]:
                if isinstance(l.source, Medicament):
                    r_sql = "UPDATE medicament SET {}={} WHERE unique_id='{}';"
                    for field in l.fields:
                        if "deleted" in field:
                            out.append(
                                {
                                    "sql": r_sql.format("deleted", l.fields.get("deleted"), l.source.unique_id),
                                    "uuid": l.id
                                }
                            )

                if isinstance(l.source, NomCommercial):
                    r_sql = "UPDATE nom_commercial SET {}={} WHERE unique_id='{}';"
                    if "deleted" in l.fields:
                        out.append(
                            {
                                "sql": r_sql.format(
                                    "deleted",
                                    l.fields.get("deleted"),
                                    l.source.unique_id
                                ),
                                "uuid": l.id
                            }
                        )

                if isinstance(l.source, DciAtc):
                    r_sql = "UPDATE dci_atc SET {}={} WHERE unique_id='{}';"
                    if "deleted" in l.fields:
                        out.append(
                            {
                                "sql": r_sql.format(
                                    "deleted",
                                    l.fields.get("deleted"),
                                    l.source.unique_id
                                ),
                                "uuid": l.id
                            }
                        )

                if isinstance(l.source, MapAutorise):
                    r_sql = "UPDATE map_autorise SET {}='{}' WHERE medicament_id='{}';"
                    if l.source.medicament:
                        if "autorise" in l.fields:
                            out.append(
                                {
                                    "sql": r_sql.format(
                                        "autorise",
                                        l.fields.get("autorise"),
                                        l.source.medicament.unique_id
                                    ),
                                    "uuid": l.id
                                }
                            )

                if isinstance(l.source, MapCnas):
                    r_sql = "UPDATE map_cnas SET {}='{}' WHERE medicament_id='{}';"
                    if l.source.medicament:
                        if "remborsable" in l.fields:
                            out.append(
                                {
                                    "sql": r_sql.format(
                                        "remborsable",
                                        l.fields.get("remborsable"),
                                        l.source.medicament.unique_id
                                    ),
                                    "uuid": l.id
                                }
                            )
        return out


class ChageDrugsSerializer(serializers.Serializer):
    uuid = serializers.CharField(max_length=255)

    def save(self):
        uuid = self.validated_data['uuid']
        logs = None
        out = []
        if uuid == "NEW":
            logs = ChangeDrugs.objects.all().order_by("date_mise_a_jour")
        else:
            temp = ChangeDrugs.objects.filter(id=uuid)
            if temp.exists():
                logs = ChangeDrugs.objects.filter(date_mise_a_jour__gt=temp.first().date_mise_a_jour).order_by(
                    "date_mise_a_jour")
        if logs:
            for l in logs[:20]:
                out.append(
                    {
                        "sql": l.query,
                        "uuid": l.id
                    }
                )
        return out
