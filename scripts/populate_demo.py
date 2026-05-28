# apps/core/management/commands/seed_safralog.py
"""
Popular SafraLog com dados realistas.

Uso:
    python manage.py seed_safralog
    python manage.py seed_safralog --days 120 --drivers 15 --waybills 2500

Objetivo:
- Simular uso REAL do sistema
- Popular financeiro + operacional
- Gerar ledger consistente
- Criar settlements
- Criar abastecimentos
- Criar adiantamentos
- Criar romaneios

ATENÇÃO:
- NÃO execute em produção.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.finance.models import Advance, FinancialAccount
from apps.finance.services.ledger_service import (
    record_advance_debit,
    record_fueling_debit,
    record_waybill_production,
)
from apps.finance.services.settlement_service import create_settlement
from apps.logistics.models import Driver, Fueling, Vehicle
from apps.operations.models import Field, Harvest, Waybill
from apps.tenants.models import Tenant

FIRST_NAMES = [
    "João",
    "Pedro",
    "Carlos",
    "Marcos",
    "Antônio",
    "Lucas",
    "Mateus",
    "Fernando",
    "Raimundo",
    "José",
]

LAST_NAMES = [
    "Silva",
    "Souza",
    "Oliveira",
    "Almeida",
    "Costa",
    "Ferreira",
    "Barbosa",
    "Rocha",
]

PLATES = [
    "QWE",
    "RTY",
    "UIO",
    "PAS",
    "DFG",
    "HJK",
    "ZXC",
]


def money(min_value, max_value):
    return Decimal(str(round(random.uniform(min_value, max_value), 2)))


class Command(BaseCommand):
    help = "Popula o SafraLog com dados realistas"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--drivers", type=int, default=10)
        parser.add_argument("--waybills", type=int, default=1500)

    @transaction.atomic
    def handle(self, *args, **options):
        days = options["days"]
        drivers_count = options["drivers"]
        total_waybills = options["waybills"]

        self.stdout.write(self.style.WARNING("Limpando dados antigos..."))

        Waybill.objects.all().delete()
        Fueling.objects.all().delete()
        Advance.objects.all().delete()
        Driver.objects.all().delete()
        Vehicle.objects.all().delete()
        Field.objects.all().delete()
        Harvest.objects.all().delete()
        FinancialAccount.objects.all().delete()

        tenant = Tenant.objects.first()

        if not tenant:
            raise Exception("Nenhum tenant encontrado.")

        self.stdout.write(self.style.SUCCESS(f"Tenant: {tenant}"))

        # =========================================================
        # HARVEST
        # =========================================================

        harvest = Harvest.objects.create(
            tenant=tenant,
            name="Safra Soja 2026",
            crop_type=Harvest.CropType.SOYBEAN,
            status=Harvest.Status.ACTIVE,
            start_date=timezone.localdate() - timedelta(days=days),
            expected_area_ha=Decimal("4500"),
            expected_yield_ton_ha=Decimal("3.8"),
        )

        self.stdout.write(self.style.SUCCESS("Safra criada"))

        # =========================================================
        # FIELDS
        # =========================================================

        fields = []

        for i in range(1, 9):
            field = Field.objects.create(
                tenant=tenant,
                harvest=harvest,
                name=f"Talhão {i:02d}",
                area_ha=money(200, 1200),
            )
            fields.append(field)

        self.stdout.write(self.style.SUCCESS(f"{len(fields)} talhões criados"))

        # =========================================================
        # DRIVERS + ACCOUNTS
        # =========================================================

        drivers = []

        for i in range(drivers_count):
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

            account = FinancialAccount.objects.create(
                tenant=tenant,
                name=f"Conta {full_name}",
            )

            driver = Driver.objects.create(
                tenant=tenant,
                name=full_name,
                financial_account=account,
                document_cpf=f"{random.randint(10000000000, 99999999999)}",
                document_cnh=f"{random.randint(1000000000, 9999999999)}",
            )

            drivers.append(driver)

        self.stdout.write(self.style.SUCCESS(f"{len(drivers)} motoristas criados"))

        # =========================================================
        # VEHICLES
        # =========================================================

        vehicles = []

        for i in range(drivers_count):
            plate = f"{random.choice(PLATES)}{random.randint(1000, 9999)}"

            vehicle = Vehicle.objects.create(
                tenant=tenant,
                plate=plate,
                model=f"FH {random.randint(440, 540)}",
            )

            vehicles.append(vehicle)

        self.stdout.write(self.style.SUCCESS(f"{len(vehicles)} veículos criados"))

        # =========================================================
        # WAYBILLS
        # =========================================================

        self.stdout.write(self.style.WARNING("Criando romaneios..."))

        created_waybills = []

        for i in range(total_waybills):
            driver = random.choice(drivers)
            vehicle = random.choice(vehicles)
            field = random.choice(fields)

            operation_date = timezone.localdate() - timedelta(days=random.randint(0, days))

            gross_weight = Decimal(random.randint(42000, 54000))
            tare_weight = Decimal(random.randint(14000, 18000))

            waybill = Waybill.objects.create(
                tenant=tenant,
                number=i + 1,
                driver=driver,
                vehicle=vehicle,
                field=field,
                harvest=harvest,
                operation_date=operation_date,
                gross_weight=gross_weight,
                tare_weight=tare_weight,
                unit_price=money(180, 280),
                status=Waybill.Status.CONFIRMED,
            )

            record_waybill_production(
                tenant=tenant,
                account=driver.financial_account,
                waybill=waybill,
            )

            created_waybills.append(waybill)

        self.stdout.write(self.style.SUCCESS(f"{len(created_waybills)} romaneios criados"))

        # =========================================================
        # FUELINGS
        # =========================================================

        self.stdout.write(self.style.WARNING("Criando abastecimentos..."))

        fuelings_created = 0

        for _ in range(total_waybills // 3):
            driver = random.choice(drivers)
            vehicle = random.choice(vehicles)

            fueling = Fueling.objects.create(
                tenant=tenant,
                fueling_date=timezone.localdate() - timedelta(days=random.randint(0, days)),
                driver=driver,
                vehicle=vehicle,
                harvest=harvest,
                liters=money(150, 650),
                price_per_liter=money(5.40, 6.90),
                payment_method=Fueling.PaymentMethod.DRIVER_ACCOUNT,
                fuel_type=Fueling.FuelType.DIESEL_S10,
                odometer=random.randint(10000, 250000),
                station_name="Posto SafraLog",
            )

            entry = record_fueling_debit(
                tenant=tenant,
                account=driver.financial_account,
                fueling=fueling,
            )

            fueling.ledger_entry = entry
            fueling.save(update_fields=["ledger_entry"])

            fuelings_created += 1

        self.stdout.write(self.style.SUCCESS(f"{fuelings_created} abastecimentos criados"))

        # =========================================================
        # ADVANCES
        # =========================================================

        self.stdout.write(self.style.WARNING("Criando adiantamentos..."))

        advances_created = 0

        for _ in range(drivers_count * 8):
            driver = random.choice(drivers)

            advance = Advance.objects.create(
                tenant=tenant,
                driver=driver,
                harvest=harvest,
                financial_account=driver.financial_account,
                amount=money(300, 5000),
                payment_date=timezone.localdate() - timedelta(days=random.randint(0, days)),
                payment_method=random.choice(
                    [
                        Advance.PaymentMethod.PIX,
                        Advance.PaymentMethod.CASH,
                        Advance.PaymentMethod.BANK_TRANSFER,
                    ]
                ),
                reference_code=f"ADV-{random.randint(10000, 99999)}",
                notes="Adiantamento operacional",
            )

            entry = record_advance_debit(
                tenant=tenant,
                account=driver.financial_account,
                advance=advance,
            )

            advance.status = Advance.Status.PAID
            advance.ledger_entry = entry
            advance.save(update_fields=["status", "ledger_entry"])

            advances_created += 1

        self.stdout.write(self.style.SUCCESS(f"{advances_created} adiantamentos criados"))

        # =========================================================
        # SETTLEMENTS
        # =========================================================

        self.stdout.write(self.style.WARNING("Criando fechamentos..."))

        settlements_created = 0

        for driver in drivers:
            try:
                create_settlement(
                    tenant=tenant,
                    driver=driver,
                    period_start=timezone.localdate() - timedelta(days=days),
                    period_end=timezone.localdate(),
                )

                settlements_created += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro settlement {driver.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"{settlements_created} fechamentos criados"))

        # =========================================================
        # FINAL
        # =========================================================

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("SEED FINALIZADO"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Motoristas: {len(drivers)}")
        self.stdout.write(f"Veículos: {len(vehicles)}")
        self.stdout.write(f"Talhões: {len(fields)}")
        self.stdout.write(f"Romaneios: {len(created_waybills)}")
        self.stdout.write(f"Abastecimentos: {fuelings_created}")
        self.stdout.write(f"Adiantamentos: {advances_created}")
        self.stdout.write(f"Fechamentos: {settlements_created}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
