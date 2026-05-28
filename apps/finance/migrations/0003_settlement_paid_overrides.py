import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Alterar status choices para incluir 'paid'
        migrations.AlterField(
            model_name='settlement',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Rascunho'),
                    ('pending_approval', 'Aguardando aprovação'),
                    ('approved', 'Aprovado'),
                    ('paid', 'Pago'),
                    ('closed', 'Fechado'),
                    ('cancelled', 'Cancelado'),
                ],
                db_index=True,
                default='draft',
                max_length=20,
                verbose_name='Status',
            ),
        ),
        # 2. Alterar status choices em HistoricalSettlement também
        migrations.AlterField(
            model_name='historicalsettlement',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Rascunho'),
                    ('pending_approval', 'Aguardando aprovação'),
                    ('approved', 'Aprovado'),
                    ('paid', 'Pago'),
                    ('closed', 'Fechado'),
                    ('cancelled', 'Cancelado'),
                ],
                db_index=True,
                default='draft',
                max_length=20,
                verbose_name='Status',
            ),
        ),
        # 3. Adicionar campos de pagamento
        migrations.AddField(
            model_name='settlement',
            name='payment_date',
            field=models.DateField(blank=True, null=True, verbose_name='Data do pagamento'),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='payment_date',
            field=models.DateField(blank=True, null=True, verbose_name='Data do pagamento'),
        ),
        migrations.AddField(
            model_name='settlement',
            name='payment_notes',
            field=models.TextField(blank=True, default='', verbose_name='Observações do pagamento'),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='payment_notes',
            field=models.TextField(blank=True, default='', verbose_name='Observações do pagamento'),
        ),
        migrations.AddField(
            model_name='settlement',
            name='payment_proof',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='settlements/comprovantes/%Y/%m/',
                verbose_name='Comprovante de pagamento',
            ),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='payment_proof',
            field=models.TextField(blank=True, max_length=100, null=True, verbose_name='Comprovante de pagamento'),
        ),
        migrations.AddField(
            model_name='settlement',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Marcado como pago em'),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Marcado como pago em'),
        ),
        migrations.AddField(
            model_name='settlement',
            name='paid_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='paid_settlements',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Pago registrado por',
            ),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='paid_by',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Pago registrado por',
            ),
        ),
        # 4. Adicionar custom_overrides
        migrations.AddField(
            model_name='settlement',
            name='custom_overrides',
            field=models.JSONField(blank=True, default=dict, verbose_name='Ajustes manuais'),
        ),
        migrations.AddField(
            model_name='historicalsettlement',
            name='custom_overrides',
            field=models.JSONField(blank=True, default=dict, verbose_name='Ajustes manuais'),
        ),
    ]
