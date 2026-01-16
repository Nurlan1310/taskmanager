# assistant/permissions.py

def is_director(employee):
    return bool(employee and employee.role == "director")


def is_deputy(employee):
    return bool(employee and employee.role == "deputy")


def is_head(employee):
    return bool(employee and employee.role == "head")


def is_management(employee):
    """
    Руководящий состав:
    - director
    - deputy
    - head
    """
    return bool(
        employee and employee.role in ["director", "deputy", "head"]
    )


def can_view_department_analytics(employee):
    """
    Кто может видеть аналитику по отделу / сотрудникам
    """
    return is_management(employee)


def can_view_all_analytics(employee):
    """
    Кто может видеть аналитику по всей организации
    """
    return bool(
        employee and employee.role in ["director", "deputy"]
    )