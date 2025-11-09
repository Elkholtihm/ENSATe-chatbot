from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """Split a string by a delimiter"""
    if value:
        return value.split(arg)
    return []

@register.filter(name='trim')
def trim(value):
    """Trim whitespace from a string"""
    if value:
        return value.strip()
    return value

@register.filter(name='get_filename')
def get_filename(value):
    """Extract filename from full path"""
    if value:
        # Handle both forward slashes and backslashes
        return value.replace('\\', '/').split('/')[-1]
    return ''