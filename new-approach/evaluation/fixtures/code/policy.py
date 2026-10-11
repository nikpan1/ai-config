def can_approve(age: int, active: bool) -> bool:
    if not active:
        return False
    return age >= 18
