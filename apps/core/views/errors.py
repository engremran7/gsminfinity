from django.http import JsonResponse

async def error_400_view(request, exception):
    return JsonResponse({"error": "bad_request"}, status=400)

async def error_403_view(request, exception):
    return JsonResponse({"error": "forbidden"}, status=403)

async def error_404_view(request, exception):
    return JsonResponse({"error": "not_found"}, status=404)

async def error_500_view(request):
    return JsonResponse({"error": "server_error"}, status=500)
