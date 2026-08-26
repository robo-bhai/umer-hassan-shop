from django import template
from collections import defaultdict

register = template.Library()

@register.filter
def sum_attribute(objects, attr):
    """
    Custom filter to sum the values of a specific attribute across a queryset.
    """
    total = 0
    for obj in objects:
        value = getattr(obj, attr, 0)  # Get the attribute
        if callable(value):           # Check if it's a method
            value = value()           # Call the method to get the value
        total += value
    return total

@register.filter
def dict_groupby(value, key):
    """
    Groups a list of dictionaries or objects by a specified key.
    Usage: {% for key, group in items|dict_groupby:"key_name" %}
    """
    grouped = defaultdict(list)
    for item in value:
        keys = key.split('.')
        group_key = item
        try:
            for k in keys:
                group_key = getattr(group_key, k)
        except AttributeError:
            raise AttributeError(f"Key '{key}' not found on object '{item}'")
        grouped[group_key].append(item)
    return grouped.items()

