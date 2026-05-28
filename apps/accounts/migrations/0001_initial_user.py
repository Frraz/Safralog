# Generated manually — split to break circular dependency with tenants
import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='E-mail')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Telefone')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/%Y/%m/', verbose_name='Avatar')),
                ('role', models.CharField(choices=[('admin', 'Administrador'), ('manager', 'Gerente'), ('operator', 'Operador'), ('driver', 'Motorista'), ('viewer', 'Visualizador')], db_index=True, default='operator', max_length=20, verbose_name='Papel')),
                ('timezone', models.CharField(default='America/Sao_Paulo', max_length=50, verbose_name='Fuso horário')),
                ('is_active', models.BooleanField(default=True)),
                ('last_seen_at', models.DateTimeField(blank=True, null=True, verbose_name='Último acesso')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Usuário',
                'verbose_name_plural': 'Usuários',
                'ordering': ['first_name', 'last_name'],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
