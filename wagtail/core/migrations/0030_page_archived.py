# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-28 15:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0029_private_title'),
        # ('common', '0014_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='archived',
            field=models.BooleanField(default=False, help_text='Whether this content is archived', serialize='ignore_in_revision'),
        ),
    ]
