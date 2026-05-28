import django.db.models.deletion
import simple_history.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0001_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Criar model Region
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('name', models.CharField(max_length=100, verbose_name='Nome da região')),
                ('default_price_per_ton', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor padrão por tonelada (R$)')),
                ('description', models.TextField(blank=True, default='', verbose_name='Descrição / Referência')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_set', to='tenants.tenant', verbose_name='Empresa')),
            ],
            options={
                'verbose_name': 'Região',
                'verbose_name_plural': 'Regiões',
                'ordering': ['name'],
                'abstract': False,
            },
        ),
        # 2. Criar HistoricalRegion (django-simple-history)
        migrations.CreateModel(
            name='HistoricalRegion',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, db_index=True, editable=False, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(blank=True, editable=False, verbose_name='Atualizado em')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('name', models.CharField(max_length=100, verbose_name='Nome da região')),
                ('default_price_per_ton', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor padrão por tonelada (R$)')),
                ('description', models.TextField(blank=True, default='', verbose_name='Descrição / Referência')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.TextField(null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tenants.tenant', verbose_name='Empresa')),
            ],
            options={
                'verbose_name': 'historical Região',
                'verbose_name_plural': 'historical Regiões',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        # 3. Index + UniqueConstraint em Region
        migrations.AddIndex(
            model_name='region',
            index=models.Index(fields=['tenant', 'name'], name='operations__region_tenant_name_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='region',
            unique_together={('tenant', 'name')},
        ),
        # 4. Adicionar FK region em Field
        migrations.AddField(
            model_name='field',
            name='region',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fields',
                to='operations.region',
                verbose_name='Região',
            ),
        ),
        # 5. Adicionar FK region em HistoricalField
        migrations.AddField(
            model_name='historicalfield',
            name='region',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='operations.region',
                verbose_name='Região',
            ),
        ),
    ]
