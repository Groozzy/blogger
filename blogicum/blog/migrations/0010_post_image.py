# Generated by Django 3.2.16 on 2023-06-05 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, upload_to='birthday_images', verbose_name='Фото'),
        ),
    ]
