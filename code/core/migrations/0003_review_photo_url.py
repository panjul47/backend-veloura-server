from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_review_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='photo_url',
            field=models.URLField(
                blank=True, null=True,
                verbose_name='foto klien (URL)',
                help_text='Isi URL gambar eksternal (imgur, dll) jika tidak upload file'
            ),
        ),
    ]
