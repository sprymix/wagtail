# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-03 14:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0015_auto_20170210_2058'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='advertwithtabbedinterface',
            options={'ordering': ('text',)},
        ),
    ]
