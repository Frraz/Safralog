# Generated manually — adds tenant FK after tenants app is created
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial_user'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='tenant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='tenants.tenant',
                verbose_name='Empresa',
            ),
        ),
        migrations.CreateModel(
            name='UserTenantMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('admin', 'Administrador'), ('manager', 'Gerente'), ('operator', 'Operador'), ('driver', 'Motorista'), ('viewer', 'Visualizador')], default='operator', max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tenants.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Membro do Tenant',
                'verbose_name_plural': 'Membros do Tenant',
                'ordering': ['-joined_at'],
                'unique_together': {('user', 'tenant')},
            },
        ),
    ]
