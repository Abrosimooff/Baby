from django.conf.urls import url
from django.urls import path

from bot.base import VkCallback
from web.views import *

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('logout/', logout, name='logout'),  # Выйти из профиля
    path('album/photo/<int:photo_id>/', AlbumPhotoEdit.as_view(), name='album_photo_edit'),
    path('<slug:hashids>', AlbumPrintSecret.as_view(), name='album_print_secret'),
    path('vk/app/', VkApp.as_view(), name='vk_app'),
    path('vk/auth/', VkAuth.as_view(), name='vk_auth'),
    path('vk/callback/', VkCallback.as_view(), name='vk_callback'),
]