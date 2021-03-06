# Generated by Django 2.2.17 on 2020-11-18 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0016_historicalgeneratedcertificate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificatetemplate',
            name='mode',
            field=models.CharField(blank=True, choices=[('verified', 'verified'), ('honor', 'honor'), ('audit', 'audit'), ('professional', 'professional'), ('no-id-professional', 'no-id-professional'), ('masters', 'masters'), ('executive-education', 'executive-education')], default='honor', help_text='The course mode for this template.', max_length=125, null=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='mode',
            field=models.CharField(choices=[('verified', 'verified'), ('honor', 'honor'), ('audit', 'audit'), ('professional', 'professional'), ('no-id-professional', 'no-id-professional'), ('masters', 'masters'), ('executive-education', 'executive-education')], default='honor', max_length=32),
        ),
        migrations.AlterField(
            model_name='historicalgeneratedcertificate',
            name='mode',
            field=models.CharField(choices=[('verified', 'verified'), ('honor', 'honor'), ('audit', 'audit'), ('professional', 'professional'), ('no-id-professional', 'no-id-professional'), ('masters', 'masters'), ('executive-education', 'executive-education')], default='honor', max_length=32),
        ),
    ]
