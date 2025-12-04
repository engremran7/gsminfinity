"""
Stub views for distribution app to satisfy URL includes in development.
"""

from django.http import HttpResponse


def placeholder(request):
    return HttpResponse("Distribution module placeholder", content_type="text/plain")
