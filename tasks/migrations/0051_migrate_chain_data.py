from django.db import migrations
import json


def migrate_chain_data_forward(apps, schema_editor):
    """
    Перенос данных из старых JSON-полей Task в новые нормализованные таблицы:
    - creation_approval_chain + current_approval_index  → TaskApprovalChain
    - reviewers_chain                                   → TaskReviewChain
    - redirect_chain                                    → TaskRedirectChain

    Работает напрямую по таблице tasks_task, не инстанциируя модель Task,
    чтобы избежать конфликта имён поля redirect_chain (JSON) и обратной связи.
    """
    Employee = apps.get_model('tasks', 'Employee')
    TaskApprovalChain = apps.get_model('tasks', 'TaskApprovalChain')
    TaskReviewChain = apps.get_model('tasks', 'TaskReviewChain')
    TaskRedirectChain = apps.get_model('tasks', 'TaskRedirectChain')

    connection = schema_editor.connection
    cursor = connection.cursor()

    # Пробуем прочитать старые JSON-поля напрямую из таблицы
    try:
        cursor.execute(
            """
            SELECT
                id,
                creation_approval_chain,
                reviewers_chain,
                redirect_chain,
                current_approval_index,
                assigned_employee_id,
                created_by_id
            FROM tasks_task
            """
        )
    except Exception:
        # Если колонок уже нет — ничего не делаем, чтобы не падать на уже обновлённых БД
        return

    rows = cursor.fetchall()

    def parse_json(value):
        if value in (None, "", "null"):
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except Exception:
            return []

    for (
        task_id,
        creation_json,
        reviewers_json,
        redirect_json,
        current_idx,
        assigned_employee_id,
        created_by_id,
    ) in rows:

        # ---- 1. Цепочка согласования создания (TaskApprovalChain) ----
        approver_ids = parse_json(creation_json)
        # current_approval_index: все до него считаем "approved", остальные "pending"
        try:
            idx = int(current_idx) if current_idx is not None else None
        except (TypeError, ValueError):
            idx = None

        order = 1
        for pos, emp_id in enumerate(approver_ids):
            try:
                approver = Employee.objects.get(pk=emp_id)
            except Employee.DoesNotExist:
                continue

            status = 'pending'
            if idx is not None and pos < idx:
                status = 'approved'

            TaskApprovalChain.objects.get_or_create(
                task_id=task_id,
                approver=approver,
                order=order,
                defaults={'status': status},
            )
            order += 1

        # ---- 2. Цепочка проверяющих выполнения (TaskReviewChain) ----
        reviewer_ids = parse_json(reviewers_json)
        order = 1
        for emp_id in reviewer_ids:
            try:
                reviewer = Employee.objects.get(pk=emp_id)
            except Employee.DoesNotExist:
                continue

            TaskReviewChain.objects.get_or_create(
                task_id=task_id,
                reviewer=reviewer,
                order=order,
                defaults={'status': 'pending'},
            )
            order += 1

        # ---- 3. Цепочка перенаправлений (TaskRedirectChain) ----
        redirect_ids = parse_json(redirect_json)
        if redirect_ids:
            # В старом формате redirect_chain был просто списком ID сотрудников,
            # которые перенаправляли задачу, в порядке перенаправлений.
            # В новом формате нужно знать from_employee и to_employee.
            # Точного исторического адресата нет, поэтому принимаем упрощённый подход:
            # считаем, что все перенаправления вели к текущему исполнителю
            # (или к создателю, если исполнителя нет).
            to_emp_id = assigned_employee_id or created_by_id
            if not to_emp_id:
                continue

            order = 1
            for emp_id in redirect_ids:
                try:
                    from_emp = Employee.objects.get(pk=emp_id)
                except Employee.DoesNotExist:
                    continue

                TaskRedirectChain.objects.get_or_create(
                    task_id=task_id,
                    from_employee=from_emp,
                    to_employee_id=to_emp_id,
                    order=order,
                )
                order += 1


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0050_normalize_approval_chains'),
    ]

    operations = [
        # 1. Перенос данных из JSON-полей в новые таблицы цепочек
        migrations.RunPython(migrate_chain_data_forward, migrations.RunPython.noop),

        # 2. Удаляем старые JSON-поля из Task
        migrations.RemoveField(
            model_name='task',
            name='creation_approval_chain',
        ),
        migrations.RemoveField(
            model_name='task',
            name='reviewers_chain',
        ),
        migrations.RemoveField(
            model_name='task',
            name='redirect_chain',
        ),
        migrations.RemoveField(
            model_name='task',
            name='current_approval_index',
        ),
    ]
