"""Fee and money-breakdown calculations.

All arithmetic is integer paise with round-half-up; percentages are resolved
from configurable platform settings at calculation time.

Buyer pays: subtotal + delivery fee + platform fee.
Farmer receives: gross (= subtotal) minus any explicitly configured
seller-side deduction (default 0 — farmers pay nothing on KhetSe).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services import settings_service


def _percent_of(amount_paise: int, percent: float) -> int:
    return int(amount_paise * percent / 100 + 0.5)


@dataclass
class OrderMoney:
    subtotal_paise: int
    delivery_fee_paise: int
    platform_fee_paise: int
    total_paise: int
    farmer_gross_paise: int
    farmer_deduction_paise: int
    farmer_net_paise: int
    driver_compensation_paise: int
    platform_revenue_paise: int


def delivery_fee_paise(
    db: Session, subtotal_paise: int, *, distance_km: float | None = None
) -> int:
    base = int(settings_service.get_setting(db, "delivery_fee_base_paise"))
    per_km = int(settings_service.get_setting(db, "delivery_fee_per_km_paise"))
    fee = base + (int(distance_km * per_km) if distance_km is not None else 0)
    # Cap the distance component so far-away buyers get a quote, not a shock.
    return min(fee, base + per_km * 50)


def compute_order_money(
    db: Session,
    subtotal_paise: int,
    *,
    fulfilment: str = "delivery",
    distance_km: float | None = None,
) -> OrderMoney:
    fee_pct = float(settings_service.get_setting(db, "platform_fee_percent") or 0)
    platform_fee = _percent_of(subtotal_paise, fee_pct)

    if fulfilment == "pickup":
        delivery_fee = 0
    else:
        delivery_fee = delivery_fee_paise(db, subtotal_paise, distance_km=distance_km)

    total = subtotal_paise + delivery_fee + platform_fee

    farmer_gross = subtotal_paise
    farmer_deduction_pct = float(
        settings_service.get_setting(db, "farmer_deduction_percent") or 0
    )
    farmer_deduction = _percent_of(farmer_gross, farmer_deduction_pct)
    farmer_net = farmer_gross - farmer_deduction

    driver_share_pct = float(settings_service.get_setting(db, "driver_fee_share_percent") or 0)
    driver_compensation = _percent_of(delivery_fee, driver_share_pct) if delivery_fee else 0
    platform_revenue = platform_fee + (delivery_fee - driver_compensation)

    return OrderMoney(
        subtotal_paise=subtotal_paise,
        delivery_fee_paise=delivery_fee,
        platform_fee_paise=platform_fee,
        total_paise=total,
        farmer_gross_paise=farmer_gross,
        farmer_deduction_paise=farmer_deduction,
        farmer_net_paise=farmer_net,
        driver_compensation_paise=driver_compensation,
        platform_revenue_paise=platform_revenue,
    )
