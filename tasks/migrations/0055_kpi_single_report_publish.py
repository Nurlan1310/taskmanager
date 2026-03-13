# KPI: один отчёт на месяц, статусы draft/published, убрана formula_version

from django.db import migrations, models


def migrate_kpi_reports(apps, schema_editor):
    KPIReport = apps.get_model("tasks", "KPIReport")
    # completed -> published
    KPIReport.objects.filter(status="completed").update(status="published")
    # Оставить один отчёт на (year, month): с максимальным id
    from django.db.models import Max
    from django.db.models.functions import Greatest
    kept_ids = (
        KPIReport.objects.values("year", "month")
        .annotate(max_id=Max("id"))
        .values_list("max_id", flat=True)
    )
    KPIReport.objects.exclude(id__in=kept_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0054_task_complexity_kpiroleconfig"),
    ]

    operations = [
        migrations.RunPython(migrate_kpi_reports, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="kpireport",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Черновик"),
                    ("published", "Опубликован"),
                    ("failed", "Ошибка формирования"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Статус",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="kpireport",
            unique_together={("year", "month")},
        ),
        migrations.RemoveField(
            model_name="kpireport",
            name="formula_version",
        ),
    ]
