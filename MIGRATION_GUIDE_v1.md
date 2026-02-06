# РЕАЛИЗАЦИЯ: Нормализация Цепочек Согласования (Пункт 1)

## 📋 Что было сделано

### 1. **Новые модели (tasks/models.py)**
Вместо JSON полей создали три нормализованные модели:

```python
✅ TaskApprovalChain - Цепочка согласующих при создании задачи
   - task (FK)
   - approver (FK на Employee)
   - order (int, для сортировки)
   - status (pending/approved/rejected)
   - approved_at, rejection_reason

✅ TaskReviewChain - Цепочка проверяющих при проверке выполнения
   - task (FK)
   - reviewer (FK на Employee)
   - order (int)
   - status (pending/approved/rejected)
   - reviewed_at, review_comment

✅ TaskRedirectChain - Цепочка перенаправлений задачи
   - task (FK)
   - from_employee (FK)
   - to_employee (FK)
   - order (int)
   - redirected_at, reason
```

### 2. **Удалены JSON поля из Task (tasks/models.py)**
```python
❌ creation_approval_chain = JSONField    → ✅ TaskApprovalChain.objects.filter(task=...)
❌ reviewers_chain = JSONField           → ✅ TaskReviewChain.objects.filter(task=...)
❌ redirect_chain = JSONField            → ✅ TaskRedirectChain.objects.filter(task=...)
❌ current_approval_index = IntegerField → ✅ TaskApprovalChain.filter(status='pending').first()
```

### 3. **Helper методы в Task модель (tasks/models.py)**
```python
# Получение текущего согласующего
task.get_current_approver()          # TaskApprovalChain

# Получение всех цепочек
task.get_approval_chain_display()    # List[dict]
task.get_review_chain_display()      # List[dict]
task.get_redirect_chain_display()    # List[dict]

# Добавление в цепочки
task.add_to_approval_chain(approver, order)
task.add_to_review_chain(reviewer, order)

# Действия с согласованиями
task.approve_by(employee)            # Одобрить
task.reject_by(employee, reason)     # Отклонить
```

### 4. **Обновлены миграции (tasks/migrations/)**
```
0050_normalize_approval_chains.py    - Создание новых моделей, индексов, удаление JSON полей
0051_migrate_chain_data.py           - Миграция данных из JSON в новые таблицы
```

### 5. **Обновлены API endpoints (tasks/api_views.py)**

#### ✅ TaskViewSet.create() - Создание задач
**Было:**
```python
task_data['creation_approval_chain'] = [a.id for a in approvers]
task_data['current_approval_index'] = 0
```

**Стало:**
```python
# После создания задачи
for order, approver in enumerate(approvers, 1):
    task.add_to_approval_chain(approver, order=order)
```

#### ✅ TaskViewSet.update() - Редактирование задач
**Было:**
```python
if instance.creation_approval_chain:
    approver_ids = instance.creation_approval_chain
    # парсить JSON...
```

**Стало:**
```python
existing_chain = instance.approval_chain.all()
if existing_chain.exists():
    approvers = [ac.approver for ac in existing_chain.order_by('order')]
```

#### ✅ execute_task_view() - Отправка на проверку
**Было:**
```python
task.reviewers_chain = [r.id for r in reviewers_chain]
task.save(update_fields=['reviewers_chain'])
```

**Стало:**
```python
task.review_chain.all().delete()
for order, reviewer in enumerate(reviewers_list, 1):
    task.add_to_review_chain(reviewer, order=order)
```

#### ✅ redirect_task_view() - Перенаправление задачи
**Было:**
```python
if not task.redirect_chain:
    task.redirect_chain = []
task.redirect_chain.append(employee.id)
task.save(update_fields=['redirect_chain'])
```

**Стало:**
```python
order = task.redirect_chain.aggregate(max_order=models.Max('order'))['max_order'] or 0
task.redirect_chain.create(
    from_employee=employee,
    to_employee=new_employee,
    order=order+1,
    reason=request.data.get('reason', '')
)
```

#### ✅ get_queryset() - Фильтрация по перенаправлениям
**Было:**
```python
if connection.vendor == 'postgresql':
    queryset = Task.objects.filter(
        Q(redirect_chain__contains=[effective_employee.id])
    )
else:
    # RawSQL для SQLite...
```

**Стало:**
```python
queryset = Task.objects.filter(
    Q(created_by=effective_employee) |
    Q(redirect_chain__from_employee=effective_employee)
).distinct()
```

### 6. **Обновлены сериализаторы (tasks/serializers.py)**

```python
# Новые поля в TaskSerializer
approval_chain = serializers.SerializerMethodField()     # Цепочка согласующих
review_chain = serializers.SerializerMethodField()       # Цепочка проверяющих

# Удалены старые поля
# ❌ creation_approval_chain = ListField
# ❌ current_approval_index

# Методы для отдачи цепочек в API
def get_approval_chain(self, obj):
    return [{
        'id': ac.approver.id,
        'name': ac.approver.full_name,
        'status': ac.status,
        'approved_at': ac.approved_at,
        'rejection_reason': ac.rejection_reason,
    } for ac in obj.approval_chain.all().order_by('order')]

def get_review_chain(self, obj):
    # Аналогично...

def get_current_approver(self, obj):
    current_approval = obj.get_current_approver()
    return EmployeeSerializer(current_approval.approver).data if current_approval else None

def get_current_reviewer(self, obj):
    current_review = obj.get_current_reviewer()
    return EmployeeSerializer(current_review.reviewer).data if current_review else None
```

---

## 🎯 Преимущества новой структуры

| Аспект | JSON (Было) | Нормализованная БД (Стало) |
|--------|------------|---------------------------|
| **Запросы** | `WHERE json_each` (Raw SQL) | ORM фильтры `Q()` |
| **История** | Нет отслеживания статусов | Каждое действие в таблице |
| **Индексы** | Нельзя индексировать | `db_index=True` на approver |
| **Валидация** | Ручная парсинг JSON | Конструктор модели |
| **Масштабируемость** | Сложно с большими цепочками | Линейная масштабируемость |
| **Перенаправления** | Список ID: `[1,2,3]` | Полная история с временем и причинами |
| **Откат действий** | Невозможен | Можно удалить/изменить строку цепочки |

---

## 🔧 Как применить изменения

```bash
# 1. Применить миграции структуры
python manage.py migrate tasks 0050_normalize_approval_chains

# 2. Применить миграцию данных
python manage.py migrate tasks 0051_migrate_chain_data

# 3. Проверить данные
python manage.py shell
>>> from tasks.models import Task, TaskApprovalChain
>>> task = Task.objects.first()
>>> task.approval_chain.all()  # Должны быть записи

# 4. Проверить API
curl http://localhost:8000/api/tasks/1/
# approval_chain теперь содержит список с информацией о каждом согласующем
```

---

## 📝 API примеры

### Создание задачи с согласованием
```json
POST /api/tasks/
{
  "title": "Важная задача",
  "is_according_to_plan": false,
  "creation_deputy_id": 5,
  "recipients_ids": [3, 4]
}

Response:
{
  "id": 123,
  "status": "send_for_approve",
  "approval_chain": [
    {
      "id": 2,
      "name": "Иван Петров",
      "status": "pending",
      "approved_at": null
    },
    {
      "id": 5,
      "name": "Петр Иванов",
      "status": "pending",
      "approved_at": null
    }
  ]
}
```

### Перенаправление задачи
```json
POST /api/tasks/123/redirect/
{
  "to_employee": 7,
  "reason": "На отпуске"
}

Response:
{
  "redirect_chain_employees": [
    {
      "from_id": 3,
      "from_name": "Мария Сидорова",
      "to_id": 7,
      "to_name": "Анна Смирнова",
      "redirected_at": "2026-02-06T10:30:00Z",
      "reason": "На отпуске"
    }
  ]
}
```

### Отправка на проверку
```json
POST /api/tasks/123/execute/
{
  "execution_comment": "Выполнено"
}

Response:
{
  "status": "sent_for_review",
  "review_chain": [
    {
      "id": 2,
      "name": "Вышестоящий начальник",
      "status": "pending",
      "reviewed_at": null
    }
  ]
}
```

---

## ✅ Что нужно проверить

- [ ] Миграции применяются без ошибок
- [ ] API возвращает новые цепочки в нужном формате
- [ ] Фильтрация по перенаправлениям работает
- [ ] История согласования заполняется правильно
- [ ] Следующий шаг: Обновить views_tasks.py для согласования планов мероприятий
