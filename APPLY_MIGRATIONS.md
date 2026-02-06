# 📌 ЧЕКЛИСТ ПРИМЕНЕНИЯ МИГРАЦИЙ

## ✅ Шаги применения

### 1️⃣ Резервная копия БД (ОБЯЗАТЕЛЬНО!)
```bash
# Скопировать db.sqlite3 перед применением
cp db.sqlite3 db.sqlite3.backup
```

### 2️⃣ Применить структурную миграцию
```bash
cd c:\Users\RUMCDO\Desktop\taskmanager
python manage.py migrate tasks 0050_normalize_approval_chains
```

✅ Ожидаемый результат:
```
Running migrations:
  Applying tasks.0050_normalize_approval_chains... OK
```

### 3️⃣ Применить миграцию данных
```bash
python manage.py migrate tasks 0051_migrate_chain_data
```

✅ Ожидаемый результат:
```
Running migrations:
  Applying tasks.0051_migrate_chain_data... OK
```

### 4️⃣ Проверить, что данные мигрировали
```bash
python manage.py shell
```

```python
from tasks.models import Task, TaskApprovalChain, TaskReviewChain, TaskRedirectChain

# Проверить что цепочки заполнены
total_tasks = Task.objects.count()
approval_chains = TaskApprovalChain.objects.count()
review_chains = TaskReviewChain.objects.count()
redirect_chains = TaskRedirectChain.objects.count()

print(f"Tasks: {total_tasks}")
print(f"Approval chains: {approval_chains}")
print(f"Review chains: {review_chains}")
print(f"Redirect chains: {redirect_chains}")

# Проверить пример задачи с согласованием
task = Task.objects.filter(approval_chain__isnull=False).first()
if task:
    print(f"\nПример задачи: {task.title}")
    for ac in task.approval_chain.all().order_by('order'):
        print(f"  - {ac.approver.full_name} ({ac.get_status_display()})")

exit()
```

### 5️⃣ Запустить тесты (опционально)
```bash
python manage.py test tasks --no-migrations
```

### 6️⃣ Запустить приложение
```bash
python manage.py runserver 8001
```

### 7️⃣ Протестировать API
```bash
# Получить задачу с новыми цепочками
curl http://localhost:8001/api/tasks/1/
```

Должны увидеть в ответе:
```json
{
  "id": 1,
  "title": "...",
  "approval_chain": [
    {
      "id": 2,
      "name": "Иван Петров",
      "status": "pending",
      "approved_at": null,
      "rejection_reason": null
    }
  ],
  "review_chain": [...],
  "redirect_chain_employees": [...]
}
```

---

## ⚠️ Возможные проблемы и решения

### Проблема: "No changes detected"
```
No changes detected in app 'tasks'
```
**Решение:** Убедитесь, что файлы миграций находятся в `tasks/migrations/`

### Проблема: "duplicate key value violates unique constraint"
```
UNIQUE constraint failed: tasks_taskapprovalchain.task_id, tasks_taskapprovalchain.order
```
**Решение:** Удалить и заново применить миграцию
```bash
python manage.py migrate tasks 0049_last_working  # вернуться на шаг назад
python manage.py migrate tasks 0050  # заново применить
```

### Проблема: API возвращает ошибку после миграции
```
AttributeError: 'Task' object has no attribute 'creation_approval_chain'
```
**Решение:** Перезагрузить сервер Django
```bash
# Остановить текущий сервер (Ctrl+C)
# Заново запустить
python manage.py runserver 8001
```

---

## 🔍 Проверка целостности данных

```bash
python manage.py shell
```

```python
from tasks.models import Task, TaskApprovalChain

# Проверить что нет задач с пустыми цепочками, где должны быть
tasks_with_old_status = Task.objects.filter(
    status='send_for_approve',
    approval_chain__isnull=True  # ❌ Плохо - есть задачи на согласовании без цепочки
)

if tasks_with_old_status.exists():
    print("⚠️  Найдены задачи без цепочек согласования:")
    for task in tasks_with_old_status:
        print(f"  - Task #{task.id}: {task.title}")
else:
    print("✅ Все задачи на согласовании имеют цепочки")

# Проверить дублирование
duplicates = TaskApprovalChain.objects.values('task_id', 'order').annotate(
    count=Count('*')
).filter(count__gt=1)

if duplicates.exists():
    print("⚠️  Найдены дублирующиеся записи в цепочке!")
else:
    print("✅ Дублирований нет")

exit()
```

---

## 📊 Результат после миграции

### Таблицы ДО:
```
Task (with JSON fields)
├── creation_approval_chain: [1, 2, 3]  (JSON)
├── reviewers_chain: [4, 5]              (JSON)
├── redirect_chain: [1, 2]               (JSON)
└── current_approval_index: 0            (INT)
```

### Таблицы ПОСЛЕ:
```
Task (cleaned)
├── (все JSON поля удалены)

TaskApprovalChain (NEW)
├── task_id: 1
├── approver_id: 1
├── order: 1
├── status: "pending"
└── approved_at: NULL

TaskReviewChain (NEW)
├── task_id: 1
├── reviewer_id: 4
├── order: 1
├── status: "pending"
└── reviewed_at: NULL

TaskRedirectChain (NEW)
├── task_id: 1
├── from_employee_id: 1
├── to_employee_id: 2
├── order: 1
└── redirected_at: "2026-02-06..."
```

---

## 🎯 Что дальше?

После успешной миграции:

1. ✅ **Протестировать создание задач** - должны создаваться с цепочками согласования
2. ✅ **Протестировать редактирование задач** - цепочки должны пересоздаваться
3. ✅ **Протестировать перенаправления** - должны добавляться в `TaskRedirectChain`
4. ✅ **Обновить views_tasks.py** для согласования планов мероприятий
5. ✅ **Реализовать механизм отката согласований** (пункт 3 из плана улучшений)

---

## 💬 Нужна помощь?

Если при применении миграций возникнут проблемы:
1. Проверьте что файлы миграций в `tasks/migrations/`
2. Проверьте что БД имеет права на запись
3. Откатитесь на одну миграцию назад и повторите попытку
4. Восстановите из резервной копии и попробуйте снова
