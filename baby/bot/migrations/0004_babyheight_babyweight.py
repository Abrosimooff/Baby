# Generated by Django 2.2.5 on 2019-09-16 09:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_auto_20190913_0757'),
    ]

    operations = [
        migrations.CreateModel(
            name='BabyWeight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата измерения')),
                ('weight', models.PositiveSmallIntegerField(verbose_name='Вес в граммах')),
                ('baby', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.Baby')),
            ],
            options={
                'unique_together': {('baby', 'date')},
            },
        ),
        migrations.CreateModel(
            name='BabyHeight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата измерения')),
                ('height', models.PositiveSmallIntegerField(verbose_name='Рост в сантиметрах')),
                ('baby', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.Baby')),
            ],
            options={
                'unique_together': {('baby', 'date')},
            },
        ),
    ]
