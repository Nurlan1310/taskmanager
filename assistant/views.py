# assistant/views.py

import os
import json
from datetime import date, datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from openai import OpenAI

from .prompts import ASSISTANT_SYSTEM_PROMPT
from .services import analytics_for_user, workload_by_employee, insights

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Специальный упаковщик, чтобы даты не ломали JSON
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

class AssistantQueryApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        if not question:
            return Response({"error": "Пустой вопрос"}, status=400)

        # 1. ОПРЕДЕЛЯЕМ РОЛЬ
        employee = getattr(request.user, "employee", None)
        user_role = employee.role if employee else "staff"
        can_view_department = user_role in ["director", "deputy", "head"]

        # 2. СОБИРАЕМ ДАННЫЕ
        try:
            stats = analytics_for_user(request.user)
            
            workload = None
            insight_text = None
            
            if can_view_department:
                workload = workload_by_employee(request.user)
                if workload:
                    insight_text = insights(stats, workload)

            # 3. ФОРМИРУЕМ КОНТЕКСТ ДЛЯ GPT
            context = {
                "user_role": user_role,
                "stats": stats,
                "workload": workload if can_view_department else "ACCESS_DENIED",
                "insights": insight_text,
            }

            # Безопасно превращаем контекст в текст (теперь даты не страшны)
            context_json = json.dumps(context, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

            # 4. ЗАПРОС К OPENAI (Исправлен метод и модель)
            messages = [
                {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Вопрос: {question}\n\nДанные из системы:\n{context_json}"
                },
            ]

            # Испольуем gpt-4o-mini (самая быстрая и дешевая для аналитики)
            response = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=messages,
                temperature=0.2, # Низкая температура для точности цифр
            )

            answer = response.choices[0].message.content

            return Response({
                "answer": answer,
                "meta": {
                    "role": user_role,
                    "scope": "department" if can_view_department else "personal",
                }
            })

        except Exception as e:
            # Если что-то пошло не так, мы увидим ошибку в логах, а не просто 500
            print(f"Ошибка ассистента: {str(e)}")
            return Response({"error": f"Ошибка на стороне сервера: {str(e)}"}, status=500)