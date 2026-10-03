from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# 1. FIX: Import views from the specific app that contains your payment_webhook function.
# Assuming you wrote it in the 'events' app. If you wrote it in 'accounts', change this to 'from accounts import views'
from events import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    
    # 2. FIX: The webhook path MUST be placed above the empty '' path
    path('webhook/payment/', views.payment_webhook, name='payment_webhook'),
    
    # The empty catch-all path goes last
    path('', include('events.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)