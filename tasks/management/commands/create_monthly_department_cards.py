from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tasks.models import Department, EventCard, Category
from django.contrib.auth import get_user_model
import calendar


User = get_user_model()


MONTHS_RU = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


class Command(BaseCommand):
    help = "Создаёт ежемесячные скрытые карточки для каждого отдела"

    def handle(self, *args, **options):
        now = timezone.localtime()
        month_name = MONTHS_RU[now.month]

        # ищем категорию "Внутренняя работа"
        category = Category.objects.filter(slug="vnutrennyaya-rabota").first()
        if not category:
            category = Category.objects.create(name="Внутренняя работа", slug="vnutrennyaya-rabota")

        # admin будет создателем
        admin_user = User.objects.filter(username="admin").first()
        admin_employee = getattr(admin_user, "employee", None)

        created = 0

        for dept in Department.objects.all():
            title = f"{dept.name} {month_name.capitalize()}"

            start_date = now.replace(day=1)
            end_day = calendar.monthrange(now.year, now.month)[1]
            end_date = now.replace(day=end_day)

            # Проверяем, существует ли уже карточка этого отдела за текущий месяц
            exists = EventCard.objects.filter(
                responsible_department=dept,
                start_date__year=now.year,
                start_date__month=now.month,
                title__icontains=dept.name,
                visible=False
            ).exists()

            if exists:
                continue

            card = EventCard.objects.create(
                title=title,
                description="Карточка для задач внутри отдела",
                start_date=start_date,
                end_date=end_date,
                responsible_department=dept,
                created_by=admin_employee,
                visible=False,  # 🔒 скрытая
            )

            # прикрепляем категорию
            card.categories.add(category)

            created += 1

        self.stdout.write(self.style.SUCCESS(f"Создано {created} карточек."))
