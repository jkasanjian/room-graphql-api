# Generated by Django 2.2.10 on 2020-04-29 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_bill_billcycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='num_split',
            field=models.IntegerField(default=1),
        ),
    ]
