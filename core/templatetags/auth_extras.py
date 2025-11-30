from django import template

register = template.Library()


@register.filter
def has_role(user, role_name):
    """Check if user has a specific role"""
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.has_role(role_name)
    return False


