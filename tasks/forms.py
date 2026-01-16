from django import forms
from django.db.models import Q
from .models import Task, Employee,EventCard, Department, Category



# forms.py

class TaskForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.none(),
        required=True,
        label="Адресаты"
    )

    class Meta:
        model = Task
        fields = [
            "card", "title", "description", "recipients", "due_date",
            "google_drive_link", "attachment", "status",
            "assigned_employee", "assigned_department", "cc"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "google_drive_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://drive.google.com/..."}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["status"].required = False

        employee = getattr(user, "employee", None)
        if employee:
            if employee.role == "director":
                self.fields["recipients"].queryset = Employee.objects.all()
            elif employee.role == "deputy":
                self.fields["recipients"].queryset = Employee.objects.exclude(role="director")
            elif employee.role in ["head", "senior"]:
                self.fields["recipients"].queryset = Employee.objects.filter(
                    Q(department=employee.department) | Q(role__in=["head", "senior"])
                ).exclude(id=employee.id)
            else:
                self.fields["recipients"].queryset = Employee.objects.none()
        else:
            self.fields["recipients"].queryset = Employee.objects.none()

        self.fields["assigned_employee"].queryset = Employee.objects.all()
        self.fields["cc"].queryset = Employee.objects.all()




# forms.py
from django import forms
from .models import EventCard, Department, Employee

class EventCardForm(forms.ModelForm):
    # делаем approvers и shared_departments явными и необязательными,
    # чтобы пустые значения не вызывали ошибки в валидации
    approvers = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.exclude(role="staff"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
        label="Согласующие"
    )

    shared_departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Смежные отделы"
    )

    final_approver = forms.ModelChoiceField(
        queryset=Employee.objects.filter(role__in=("director","deputy")),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Утверждающий"
    )

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Категории"
    )

    def clean(self):
        cleaned_data = super().clean()
        has_plan = cleaned_data.get("has_plan")
        final_approver = cleaned_data.get("final_approver")

        if has_plan and not final_approver:
            raise forms.ValidationError("Если у карточки есть план, необходимо указать финального утверждающего.")
        return cleaned_data

    class Meta:
        model = EventCard
        fields = [
            "title", "description", "has_plan", "plan_file",
            "start_date", "end_date",
            "responsible_department", "shared_departments",
            "approvers", "final_approver", "categories"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "plan_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "has_plan": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "responsible_department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # при необходимости можно динамически фильтровать список
        self.fields["categories"].queryset = Category.objects.all()




class PlanReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[("approve", "Утвердить"), ("reject", "Отклонить")], widget=forms.RadioSelect)
    reason = forms.CharField(widget=forms.Textarea, required=False, help_text="При отклонении укажите причину")



class DelegationForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["delegate_to"]

    def __init__(self, *args, **kwargs):
        current_employee = kwargs.pop("current_employee", None)
        super().__init__(*args, **kwargs)

        # Ограничиваем список сотрудников только отделом текущего
        if current_employee and current_employee.department:
            self.fields["delegate_to"].queryset = Employee.objects.filter(
                department=current_employee.department
            ).exclude(id=current_employee.id)
        else:
            self.fields["delegate_to"].queryset = Employee.objects.none()
