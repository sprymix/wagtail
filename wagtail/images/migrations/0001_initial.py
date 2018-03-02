# -*- coding: utf-8 -*-
import taggit.managers
from django.conf import settings
from django.db import migrations, models

import wagtail.images.models
import wagtail.search.index


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('spec', models.CharField(db_index=True, max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('title', models.CharField(verbose_name='Title', max_length=255)),
                ('file', models.ImageField(
                    width_field='width', upload_to=wagtail.images.models.get_upload_to,
                    verbose_name='File', height_field='height'
                )),
                ('width', models.IntegerField(editable=False)),
                ('height', models.IntegerField(editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('focal_point_x', models.PositiveIntegerField(editable=False, null=True)),
                ('focal_point_y', models.PositiveIntegerField(editable=False, null=True)),
                ('focal_point_width', models.PositiveIntegerField(editable=False, null=True)),
                ('focal_point_height', models.PositiveIntegerField(editable=False, null=True)),
                ('tags', taggit.managers.TaggableManager(blank=True, help_text='To enter multi-word tags, use double quotes: "some tag".', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('uploaded_by_user', models.ForeignKey(
                    on_delete=models.CASCADE,
                    editable=False, blank=True, null=True, to=settings.AUTH_USER_MODEL
                )),
                ('show_in_catalogue', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, wagtail.search.index.Indexed),
        ),
        migrations.CreateModel(
            name='Rendition',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('file', models.ImageField(width_field='width', upload_to='images', height_field='height')),
                ('width', models.IntegerField(editable=False)),
                ('height', models.IntegerField(editable=False)),
                ('focal_point_key', models.CharField(editable=False, max_length=18, null=True)),
                ('filter', models.ForeignKey(on_delete=models.CASCADE, related_name='+', to='wagtailimages.Filter')),
                ('image', models.ForeignKey(on_delete=models.CASCADE, related_name='renditions', to='wagtailimages.Image')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='rendition',
            unique_together=set([('image', 'filter', 'focal_point_key')]),
        ),
        migrations.CreateModel(
            name='UserRendition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.ImageField(height_field='height', upload_to=wagtail.images.models.get_rendition_upload_to, width_field='width')),
                ('width', models.IntegerField(editable=False)),
                ('height', models.IntegerField(editable=False)),
                ('focal_point_key', models.CharField(blank=True, default='', editable=False, max_length=255)),
                ('filter', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', to='wagtailimages.Filter')),
                ('image', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='user_renditions', to='wagtailimages.Image')),
            ],
            bases=(models.Model, wagtail.images.models.WillowImageWrapper),
        ),
    ]
