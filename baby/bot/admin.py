from django.contrib import admin
from bot.models import *


class UserVKAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'id', 'url', 'album_pk', 'album_url', 'wait_payload']
    list_filter = ['first_name', 'last_name']

    def url(self, obj):
        return obj.vk_url

    def album_url(self, obj):
        return obj.album_url
    album_url.short_description = 'URL альбома'


class BabyAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'birth_date', 'gender', 'age']
    list_filter = ['first_name', 'gender']

    def age(self, obj):
        return obj.get_birth_date_delta_string()
    age.short_description = 'Возраст'


class BabyUserVKAdmin(admin.ModelAdmin):
    list_display = ['user_vk', 'baby']


class BabyHistoryAdmin(admin.ModelAdmin):
    list_display = ['date_vk', 'id', 'user_vk', 'baby', 'text', 'message_vk_id', 'month']
    list_filter = ['user_vk', 'baby']
    ordering = ('-date_vk', )


class BabyHistoryAttachAdmin(admin.ModelAdmin):
    list_display = ['user_vk', 'baby', 'history_id', 'date', 'text', 'url']
    list_filter = ['history__user_vk', 'history__baby']
    ordering = ('-history_id', 'id')

    def text(self, obj):
        return obj.history.text
    text.short_description = 'Текст сообщения'

    def date(self, obj):
        return obj.history.date_vk
    date.short_description = 'Дата сообщения'

    def user_vk(self, obj):
        return obj.history.user_vk
    user_vk.short_description = 'Пользователь ВК'

    def baby(self, obj):
        return obj.history.baby
    baby.short_description = 'Ребёнок'


class BabyHeightAdmin(admin.ModelAdmin):
    list_display = ['baby', 'id', 'date', 'height_str']
    list_filter = ['baby']
    ordering = ('-date',)


class BabyWeightAdmin(admin.ModelAdmin):
    list_display = ['baby', 'id', 'date', 'weight_str']
    list_filter = ['baby']
    ordering = ('-date',)


admin.site.register(UserVK, UserVKAdmin)
admin.site.register(Baby, BabyAdmin)
admin.site.register(BabyUserVK, BabyUserVKAdmin)
admin.site.register(BabyHistory, BabyHistoryAdmin)
admin.site.register(BabyHistoryAttachment, BabyHistoryAttachAdmin)
admin.site.register(BabyHeight, BabyHeightAdmin)
admin.site.register(BabyWeight, BabyWeightAdmin)