import django_mongodb_backend.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Measurement",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("station_id", models.CharField(max_length=100)),
                ("observed_at", models.DateTimeField()),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("location_name", models.CharField(blank=True, max_length=200)),
                ("source", models.CharField(default="open-meteo", max_length=30)),
                ("risk_score", models.FloatField()),
                ("metrics", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "Measurement",
                "ordering": ["-observed_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=["-observed_at", "-id"], name="measurement_time_idx"
                    ),
                    models.Index(
                        fields=["station_id", "-observed_at", "-id"],
                        name="measurement_station_idx",
                    ),
                    models.Index(
                        fields=["risk_score", "-observed_at"],
                        name="measurement_risk_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("station_id", "observed_at"),
                        name="measurement_station_time_unique",
                    )
                ],
            },
        ),
    ]
