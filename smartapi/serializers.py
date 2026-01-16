from rest_framework import serializers
from django.contrib.auth.models import User
from tasks.models import Employee, Department


class SmartUserSerializer(serializers.ModelSerializer):
    """Сериализатор для auth_user с полями: id, username, last_name, email, first_name, middle_name"""
    middle_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'last_name', 'email', 'first_name', 'middle_name']
    
    def get_middle_name(self, obj):
        """Возвращает middle_name, если поле существует, иначе None"""
        # Пока поле middle_name не добавлено в модель User, возвращаем None
        # Когда поле будет добавлено, можно будет использовать obj.middle_name
        return getattr(obj, 'middle_name', None)


class SmartEmployeeSerializer(serializers.ModelSerializer):
    """Сериализатор для tasks_employee - возвращает все поля"""
    user = SmartUserSerializer(read_only=True)
    department = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    delegate_to_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'position', 'department', 'role', 
            'photo', 'internal_phone', 'delegate_to', 'delegate_until',
            'full_name', 'delegate_to_name'
        ]
    
    def get_department(self, obj):
        """Возвращает информацию об отделе или None"""
        if obj.department:
            return {
                'id': obj.department.id,
                'name': obj.department.name,
                'priority': obj.department.priority
            }
        return None
    
    def get_delegate_to_name(self, obj):
        """Возвращает имя замещающего сотрудника или None"""
        if obj.delegate_to:
            return obj.delegate_to.full_name
        return None


class SmartDepartmentSerializer(serializers.ModelSerializer):
    """Сериализатор для tasks_department - возвращает все поля"""
    class Meta:
        model = Department
        fields = ['id', 'name', 'priority']