# Generated by Django 2.2.5 on 2019-09-13 07:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_baby_babyuservk'),
    ]

    operations = [
        migrations.CreateModel(
            name='BabyHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='Текст сообщения')),
                ('message_vk_id', models.IntegerField(verbose_name='ID сообщения ВК')),
                ('date_vk', models.DateTimeField(verbose_name='Дата время сообщения')),
                ('other_attach_vk', models.BooleanField(default=False, verbose_name='Есть ли другие вложения в сообщении кроме фото')),
                ('baby', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.Baby', verbose_name='Младенец')),
                ('user_vk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.UserVK', verbose_name='Автор заметки')),
            ],
        ),
        migrations.RemoveField(
            model_name='babyuservk',
            name='last_message_date',
        ),
        migrations.CreateModel(
            name='BabyHistoryAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attachment_type', models.CharField(max_length=50)),
                ('url', models.URLField(verbose_name='Путь')),
                ('history', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.BabyHistory')),
            ],
        ),
    ]
