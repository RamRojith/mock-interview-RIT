from django.urls import path, include
from stock_management.views import admin_stock_views
from stock_management.urls import stock_control_urls, stock_curd_urls

urlpatterns = [
    path('stock_settings/', include(stock_control_urls)),
    path('stock_home/', admin_stock_views.stock_home, name='stock_home'),
    path('stock_crud/', include(stock_curd_urls)),
]
