"""
SafraLog — Seed de dados de desenvolvimento.
Cria tenant, usuários, safra, motoristas, veículos e romaneios de exemplo.

Uso:
  make seed
  # ou diretamente:
  docker compose ... exec django python scripts/seed_dev_data.py
"""

import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

import django

# Garante que /app (raiz do projeto) está no sys.path.
# Necessário ao rodar com `python scripts/seed_dev_data.py` diretamente,
# pois Python só adiciona o diretório DO SCRIPT (scripts/) ao path, não a raiz.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from apps.finance.models import FinancialAccount
from apps.logistics.models import Driver, Vehicle
from apps.operations.models import Field, Harvest, Waybill
from apps.tenants.models import Tenant

User = get_user_model()

print("🌱 Iniciando seed de dados de desenvolvimento...")
print()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def get_or_create_financial_account(tenant, driver):
    """
    Cria conta financeira para o motorista caso não exista.
    Usa linked_type + linked_id (campos reais do GenericFK no model FinancialAccount).
    NÃO usar 'content_object' — esse não é o nome do campo no model.
    """
    if driver.financial_account_id:
        return driver.financial_account

    driver_ct = ContentType.objects.get_for_model(driver)
    account = FinancialAccount.objects.create(
        tenant=tenant,
        name=f"Conta — {driver.name}",
        account_type="driver",
        linked_type=driver_ct,
        linked_id=driver.pk,
    )
    driver.financial_account = account
    driver.save(update_fields=["financial_account"])
    return account


# ─────────────────────────────────────────────────────────────
# TENANT
# ─────────────────────────────────────────────────────────────

tenant, created = Tenant.objects.get_or_create(
    slug="fazenda-demo",
    defaults={
        "name": "Fazenda Santa Fé Demo",
        "plan": "professional",
        "status": "active",
        "max_users": 50,
    },
)
print(f"{'✅ Criado' if created else '🔄 Existe'} tenant: {tenant.name}")


# ─────────────────────────────────────────────────────────────
# USUÁRIOS
# ─────────────────────────────────────────────────────────────

usuarios = [
    {
        "email": "admin@safralog.dev",
        "username": "admin_safralog",
        "first_name": "Admin",
        "last_name": "SafraLog",
        "role": "admin",
        "password": "admin123",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "email": "gerente@safralog.dev",
        "username": "gerente_safralog",
        "first_name": "Maria",
        "last_name": "Gerente",
        "role": "manager",
        "password": "gerente123",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "email": "operador@safralog.dev",
        "username": "operador_safralog",
        "first_name": "João",
        "last_name": "Operador",
        "role": "operator",
        "password": "op123",
        "is_staff": False,
        "is_superuser": False,
    },
]

created_users = {}
for u in usuarios:
    password = u.pop("password")
    obj, created = User.objects.get_or_create(
        email=u["email"],
        defaults={**u, "tenant": tenant, "is_active": True},
    )
    if created:
        obj.set_password(password)
        obj.save(update_fields=["password"])
    created_users[obj.role] = obj
    u["password"] = password  # restaura para não mutar o dict original
    print(f"  {'✅ Criado' if created else '🔄 Existe'} [{obj.role}]: {obj.email} / {password}")

admin = created_users.get("admin")
print()


# ─────────────────────────────────────────────────────────────
# SAFRA
# ─────────────────────────────────────────────────────────────

harvest, created = Harvest.objects.get_or_create(
    tenant=tenant,
    name="Safra Soja 2024/25",
    defaults={
        "crop_type": "soybean",
        "status": "active",
        "start_date": date(2024, 10, 1),
        "end_date": date(2025, 4, 30),
        "expected_area_ha": Decimal("5000"),
        "expected_yield_ton_ha": Decimal("3.2"),
    },
)
print(f"{'✅ Criada' if created else '🔄 Existe'} safra: {harvest.name}")


# ─────────────────────────────────────────────────────────────
# TALHÕES
# ─────────────────────────────────────────────────────────────

talhoes_data = [
    ("Talhão Norte A", Decimal("500")),
    ("Talhão Norte B", Decimal("420")),
    ("Talhão Sul 1", Decimal("680")),
    ("Talhão Sul 2", Decimal("590")),
    ("Talhão Leste", Decimal("810")),
]
fields = []
for nome, area in talhoes_data:
    f, _ = Field.objects.get_or_create(
        tenant=tenant,
        harvest=harvest,
        name=nome,
        defaults={"area_ha": area},
    )
    fields.append(f)
print(f"✅ {len(fields)} talhões configurados")


# ─────────────────────────────────────────────────────────────
# MOTORISTAS + CONTAS FINANCEIRAS
# ─────────────────────────────────────────────────────────────

motoristas_data = [
    ("Carlos Eduardo Silva", "123.456.789-00", "B"),
    ("Marcos Antônio Pereira", "987.654.321-00", "C"),
    ("João Pedro Oliveira", "111.222.333-44", "C"),
    ("Antônio Carlos Ferreira", "555.666.777-88", "D"),
    ("Luiz Henrique Santos", "444.333.222-11", "C"),
    ("Roberto Alves Costa", "999.888.777-66", "B"),
]

drivers = []
for nome, cpf, cnh_cat in motoristas_data:
    driver, created = Driver.objects.get_or_create(
        tenant=tenant,
        document_cpf=cpf,
        defaults={
            "name": nome,
            "cnh_category": cnh_cat,
            "status": "active",
        },
    )
    get_or_create_financial_account(tenant, driver)
    drivers.append(driver)

print(f"✅ {len(drivers)} motoristas configurados (com contas financeiras)")


# ─────────────────────────────────────────────────────────────
# VEÍCULOS
# ─────────────────────────────────────────────────────────────

veiculos_data = [
    ("ABC-1234", "semi_trailer", "Scania", "R540", 36000),
    ("DEF-5678", "semi_trailer", "Volvo", "FH500", 35000),
    ("GHI-9012", "truck", "Mercedes", "Atego", 14000),
    ("JKL-3456", "semi_trailer", "DAF", "XF480", 37000),
]

vehicles = []
for placa, tipo, marca, modelo, payload in veiculos_data:
    v, _ = Vehicle.objects.get_or_create(
        tenant=tenant,
        plate=placa,
        defaults={
            "vehicle_type": tipo,
            "brand": marca,
            "model": modelo,
            "status": "active",
            "payload_kg": payload,
        },
    )
    vehicles.append(v)

print(f"✅ {len(vehicles)} veículos configurados")


# ─────────────────────────────────────────────────────────────
# ROMANEIOS
# ─────────────────────────────────────────────────────────────

existing = Waybill.objects.filter(tenant=tenant).count()

if existing:
    print(f"🔄 Romaneios já existem: {existing} — pulando geração")
else:
    print("🌾 Gerando 60 romaneios de exemplo...")

    unit_price = Decimal("145.00")
    today = date.today()

    # Pesos realistas por tipo de veículo
    peso_por_tipo = {
        "semi_trailer": (38000, 48000),
        "truck": (18000, 28000),
    }
    tara_por_tipo = {
        "semi_trailer": (14000, 16000),
        "truck": (7000, 9000),
    }

    waybills_criados = 0
    for number in range(1, 61):
        driver = random.choice(drivers)
        vehicle = random.choice(vehicles)
        field = random.choice(fields)

        v_type = vehicle.vehicle_type
        gmin, gmax = peso_por_tipo.get(v_type, (35000, 48000))
        tmin, tmax = tara_por_tipo.get(v_type, (12000, 16000))

        gross = Decimal(str(random.randint(gmin, gmax)))
        tare = Decimal(str(random.randint(tmin, tmax)))

        # Garante tara < bruto
        if tare >= gross:
            tare = gross - Decimal("5000")

        # Distribui as datas nos últimos 45 dias com mais peso nos 15 dias recentes
        days_ago = random.choices(
            range(46),
            weights=[max(1, 46 - d) for d in range(46)],
        )[0]
        op_date = today - timedelta(days=days_ago)

        status = random.choices(
            ["draft", "confirmed", "settled"],
            weights=[10, 65, 25],
        )[0]

        Waybill.objects.create(
            tenant=tenant,
            number=number,
            harvest=harvest,
            field=field,
            driver=driver,
            vehicle=vehicle,
            culture="soybean",
            status=status,
            operation_date=op_date,
            gross_weight=gross,
            tare_weight=tare,
            unit_price=unit_price,
            destination="Cooperativa Central — Rondonópolis/MT",
        )
        waybills_criados += 1

    print(f"✅ {waybills_criados} romaneios criados")


# ─────────────────────────────────────────────────────────────
# RESUMO FINAL
# ─────────────────────────────────────────────────────────────

print()
print("═" * 52)
print("✅  SEED CONCLUÍDO")
print("═" * 52)
print(f"  🏢 Tenant:  {tenant.name}")
print("  👤 Admin:   admin@safralog.dev     / admin123")
print("  👤 Gerente: gerente@safralog.dev   / gerente123")
print("  👤 Operador: operador@safralog.dev / op123")
print(f"  🚛 Motoristas: {len(drivers)}")
print(f"  🚜 Veículos:   {len(vehicles)}")
print(f"  🌾 Romaneios:  {Waybill.objects.filter(tenant=tenant).count()}")
print()
print("  🌐  http://localhost:8000")
print("  🔧  http://localhost:8000/admin")
print("═" * 52)
