# tasks/utils.py

def get_effective_employee(employee):
    """Если сотрудник делегировал свои полномочия, вернуть замещающего."""
    if not employee:
        return None
    delegate = employee.get_active_delegate()
    return delegate if delegate else employee
