"""
SafraLog — tests/factories/core.py
Factories com factory_boy para todos os models principais.
"""

from __future__ import annotations

from decimal import Decimal

import factory
from django.contrib.contenttypes.models import ContentType
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.tenants.models import Tenant

# ─────────────────────────────────────────────────────────────
# TENANTS E ACCOUNTS
# ─────────────────────────────────────────────────────────────


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Fazenda Demo {n}")
    slug = factory.Sequence(lambda n: f"fazenda-demo-{n}")
    plan = "starter"
    status = "active"
    max_users = 10


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    # username único garante que criar múltiplos usuários no mesmo teste
    # nunca viola a constraint unique "accounts_user_username_key"
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user{n}@safralog.dev")
    first_name = factory.Faker("first_name", locale="pt_BR")
    last_name = factory.Faker("last_name", locale="pt_BR")
    tenant = factory.SubFactory(TenantFactory)
    role = "operator"
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


# ─────────────────────────────────────────────────────────────
# OPERATIONS
# ─────────────────────────────────────────────────────────────


class HarvestFactory(DjangoModelFactory):
    class Meta:
        model = "operations.Harvest"

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Safra Soja {2024 + n}")
    crop_type = "soybean"
    status = "active"
    start_date = factory.Faker("date_this_year")


class FieldFactory(DjangoModelFactory):
    class Meta:
        model = "operations.Field"

    tenant = factory.LazyAttribute(lambda o: o.harvest.tenant)
    harvest = factory.SubFactory(HarvestFactory)
    name = factory.Sequence(lambda n: f"Talhão {n + 1}")
    area_ha = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)


# ─────────────────────────────────────────────────────────────
# LOGISTICS
# ─────────────────────────────────────────────────────────────


class FinancialAccountFactory(DjangoModelFactory):
    class Meta:
        model = "finance.FinancialAccount"

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Conta {n}")
    account_type = "driver"
    # linked_type e linked_id configurados no DriverFactory


class DriverFactory(DjangoModelFactory):
    class Meta:
        model = "logistics.Driver"
        skip_postgeneration_save = True  # evita o DeprecationWarning

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Faker("name", locale="pt_BR")
    status = "active"
    document_cpf = factory.Sequence(lambda n: f"{n:011d}")
    cnh_category = "E"

    @factory.post_generation
    def financial_account(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.financial_account = extracted
            obj.save(update_fields=["financial_account"])
        else:
            ct = ContentType.objects.get_for_model(obj)
            account = FinancialAccountFactory(
                tenant=obj.tenant,
                name=f"Conta {obj.name}",
                linked_type=ct,
                linked_id=obj.pk,
            )
            obj.financial_account = account
            obj.save(update_fields=["financial_account"])


class VehicleFactory(DjangoModelFactory):
    class Meta:
        model = "logistics.Vehicle"

    tenant = factory.SubFactory(TenantFactory)
    plate = factory.Sequence(lambda n: f"ABC-{1000 + n}")
    vehicle_type = "truck"
    brand = "Scania"
    model = "R450"
    status = "active"
    payload_kg = 35000


class FuelingFactory(DjangoModelFactory):
    class Meta:
        model = "logistics.Fueling"

    tenant = factory.LazyAttribute(lambda o: o.driver.tenant)
    driver = factory.SubFactory(DriverFactory)
    vehicle = factory.SubFactory(VehicleFactory)
    fueling_date = factory.Faker("date_this_month")
    liters = Decimal("200.00")
    price_per_liter = Decimal("6.50")
    fuel_type = "diesel"


class WaybillFactory(DjangoModelFactory):
    class Meta:
        model = "operations.Waybill"

    tenant = factory.LazyAttribute(lambda o: o.harvest.tenant)
    harvest = factory.SubFactory(HarvestFactory)
    field = factory.SubFactory(
        FieldFactory,
        harvest=factory.SelfAttribute("..harvest"),
        tenant=factory.SelfAttribute("..tenant"),
    )
    driver = factory.SubFactory(
        DriverFactory,
        tenant=factory.SelfAttribute("..tenant"),
    )
    vehicle = factory.SubFactory(
        VehicleFactory,
        tenant=factory.SelfAttribute("..tenant"),
    )
    number = factory.Sequence(lambda n: n + 1)
    status = "draft"
    operation_date = factory.Faker("date_this_month")
    culture = "soybean"
    gross_weight = Decimal("50000")
    tare_weight = Decimal("14000")
    unit_price = Decimal("120.00")


# ─────────────────────────────────────────────────────────────
# FINANCE
# ─────────────────────────────────────────────────────────────


class LedgerEntryFactory(DjangoModelFactory):
    class Meta:
        model = "finance.LedgerEntry"

    tenant = factory.LazyAttribute(lambda o: o.account.tenant)
    account = factory.SubFactory(FinancialAccountFactory)
    entry_type = "waybill_production"
    direction = "credit"
    amount = Decimal("1200.00")
    description = factory.Sequence(lambda n: f"Lançamento #{n}")
    competence_date = factory.Faker("date_this_month")
    is_reversed = False


class AdvanceFactory(DjangoModelFactory):
    class Meta:
        model = "finance.Advance"

    tenant = factory.LazyAttribute(lambda o: o.driver.tenant)
    driver = factory.SubFactory(DriverFactory)
    financial_account = factory.LazyAttribute(lambda o: o.driver.financial_account)
    amount = Decimal("500.00")
    payment_date = factory.Faker("date_this_month")
    payment_method = "pix"
    status = "pending"
