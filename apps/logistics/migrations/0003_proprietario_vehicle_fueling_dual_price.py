import decimal
import django.db.models.deletion
import simple_history.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
        ('logistics', '0002_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Criar Proprietario ───────────────────────────────────────────────
        migrations.CreateModel(
            name='Proprietario',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Observações')),
                ('name', models.CharField(max_length=200, verbose_name='Nome completo / Razão social')),
                ('document', models.CharField(blank=True, default='', max_length=20, verbose_name='CPF / CNPJ')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Telefone')),
                ('bank_name', models.CharField(blank=True, default='', max_length=100, verbose_name='Banco')),
                ('bank_agency', models.CharField(blank=True, default='', max_length=20, verbose_name='Agência')),
                ('bank_account', models.CharField(blank=True, default='', max_length=30, verbose_name='Conta')),
                ('bank_account_type', models.CharField(
                    blank=True,
                    choices=[('corrente', 'Conta Corrente'), ('poupanca', 'Conta Poupança'), ('salario', 'Conta Salário')],
                    default='corrente',
                    max_length=20,
                    verbose_name='Tipo de conta',
                )),
                ('pix_key', models.CharField(blank=True, default='', max_length=150, verbose_name='Chave PIX')),
                ('pix_key_type', models.CharField(
                    blank=True,
                    choices=[('cpf', 'CPF'), ('cnpj', 'CNPJ'), ('email', 'E-mail'), ('telefone', 'Telefone'), ('aleatoria', 'Chave aleatória')],
                    default='',
                    max_length=20,
                    verbose_name='Tipo da chave PIX',
                )),
                ('driver', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='proprietario',
                    to='logistics.driver',
                    verbose_name='Motorista (se for o próprio dono)',
                )),
                ('financial_account', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='proprietario',
                    to='finance.financialaccount',
                    verbose_name='Conta financeira',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(app_label)s_%(class)s_set',
                    to='tenants.tenant',
                    verbose_name='Empresa',
                )),
            ],
            options={
                'verbose_name': 'Proprietário',
                'verbose_name_plural': 'Proprietários',
                'ordering': ['name'],
                'abstract': False,
            },
        ),
        # ── 2. Criar HistoricalProprietario ────────────────────────────────────
        migrations.CreateModel(
            name='HistoricalProprietario',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, db_index=True, editable=False, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(blank=True, editable=False, verbose_name='Atualizado em')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Observações')),
                ('name', models.CharField(max_length=200, verbose_name='Nome completo / Razão social')),
                ('document', models.CharField(blank=True, default='', max_length=20, verbose_name='CPF / CNPJ')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Telefone')),
                ('bank_name', models.CharField(blank=True, default='', max_length=100, verbose_name='Banco')),
                ('bank_agency', models.CharField(blank=True, default='', max_length=20, verbose_name='Agência')),
                ('bank_account', models.CharField(blank=True, default='', max_length=30, verbose_name='Conta')),
                ('bank_account_type', models.CharField(
                    blank=True,
                    choices=[('corrente', 'Conta Corrente'), ('poupanca', 'Conta Poupança'), ('salario', 'Conta Salário')],
                    default='corrente',
                    max_length=20,
                    verbose_name='Tipo de conta',
                )),
                ('pix_key', models.CharField(blank=True, default='', max_length=150, verbose_name='Chave PIX')),
                ('pix_key_type', models.CharField(
                    blank=True,
                    choices=[('cpf', 'CPF'), ('cnpj', 'CNPJ'), ('email', 'E-mail'), ('telefone', 'Telefone'), ('aleatoria', 'Chave aleatória')],
                    default='',
                    max_length=20,
                    verbose_name='Tipo da chave PIX',
                )),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.TextField(null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('driver', models.ForeignKey(
                    blank=True,
                    db_constraint=False,
                    null=True,
                    on_delete=django.db.models.deletion.DO_NOTHING,
                    related_name='+',
                    to='logistics.driver',
                    verbose_name='Motorista (se for o próprio dono)',
                )),
                ('financial_account', models.ForeignKey(
                    blank=True,
                    db_constraint=False,
                    null=True,
                    on_delete=django.db.models.deletion.DO_NOTHING,
                    related_name='+',
                    to='finance.financialaccount',
                    verbose_name='Conta financeira',
                )),
                ('history_user', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('tenant', models.ForeignKey(
                    blank=True,
                    db_constraint=False,
                    null=True,
                    on_delete=django.db.models.deletion.DO_NOTHING,
                    related_name='+',
                    to='tenants.tenant',
                    verbose_name='Empresa',
                )),
            ],
            options={
                'verbose_name': 'historical Proprietário',
                'verbose_name_plural': 'historical Proprietários',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        # ── 3. Index em Proprietario ───────────────────────────────────────────
        migrations.AddIndex(
            model_name='proprietario',
            index=models.Index(fields=['tenant', 'name'], name='logistics_proprietario_tenant_name_idx'),
        ),
        # ── 4. Adicionar FK proprietario em Vehicle ────────────────────────────
        migrations.AddField(
            model_name='vehicle',
            name='proprietario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='vehicles',
                to='logistics.proprietario',
                verbose_name='Proprietário',
            ),
        ),
        # ── 5. Adicionar FK proprietario em HistoricalVehicle ──────────────────
        migrations.AddField(
            model_name='historicalvehicle',
            name='proprietario',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='logistics.proprietario',
                verbose_name='Proprietário',
            ),
        ),
        # ── 6. Fueling: renomear price_per_liter → driver_price_per_liter ──────
        migrations.RenameField(
            model_name='fueling',
            old_name='price_per_liter',
            new_name='driver_price_per_liter',
        ),
        migrations.RenameField(
            model_name='historicalfueling',
            old_name='price_per_liter',
            new_name='driver_price_per_liter',
        ),
        # ── 7. Alterar verbose_name do campo renomeado ─────────────────────────
        migrations.AlterField(
            model_name='fueling',
            name='driver_price_per_liter',
            field=models.DecimalField(
                decimal_places=4,
                max_digits=8,
                verbose_name='Preço descontado do motorista (R$/L)',
                help_text='Valor efetivamente descontado do motorista. Pode ser menor que o valor do posto.',
            ),
        ),
        migrations.AlterField(
            model_name='historicalfueling',
            name='driver_price_per_liter',
            field=models.DecimalField(
                decimal_places=4,
                max_digits=8,
                verbose_name='Preço descontado do motorista (R$/L)',
                help_text='Valor efetivamente descontado do motorista. Pode ser menor que o valor do posto.',
            ),
        ),
        # ── 8. Adicionar posted_price_per_liter ───────────────────────────────
        migrations.AddField(
            model_name='fueling',
            name='posted_price_per_liter',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=8,
                null=True,
                verbose_name='Preço do posto (R$/L)',
                help_text='Valor real cobrado pelo posto. Deixe em branco se igual ao desconto.',
            ),
        ),
        migrations.AddField(
            model_name='historicalfueling',
            name='posted_price_per_liter',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=8,
                null=True,
                verbose_name='Preço do posto (R$/L)',
            ),
        ),
        # ── 9. Adicionar extras_amount ─────────────────────────────────────────
        migrations.AddField(
            model_name='fueling',
            name='extras_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('0'),
                max_digits=10,
                verbose_name='Outros produtos no cupom (R$)',
                help_text='Valor total de outros produtos comprados no mesmo cupom (ex.: ARLA 32, lubrificantes).',
            ),
        ),
        migrations.AddField(
            model_name='historicalfueling',
            name='extras_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('0'),
                max_digits=10,
                verbose_name='Outros produtos no cupom (R$)',
            ),
        ),
        # ── 10. Adicionar novas constraints de validação ───────────────────────
        migrations.AddConstraint(
            model_name='fueling',
            constraint=models.CheckConstraint(
                condition=models.Q(driver_price_per_liter__gt=0),
                name='fueling_driver_price_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='fueling',
            constraint=models.CheckConstraint(
                condition=models.Q(extras_amount__gte=0),
                name='fueling_extras_non_negative',
            ),
        ),
    ]
