from django import template

register = template.Library()


@register.filter
def is_staff_role(user):
    return user.groups.filter(name='Airline Staff').exists()