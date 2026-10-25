"""order_items: per-farmer response for multi-farmer orders

Revision ID: a1c4f7d9e2b3
Revises: 90d96d683b85
Create Date: 2026-10-25 03:10:00.000000

Every order line now records its own farmer's response, so an order only
moves forward once every farmer in the order has answered.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4f7d9e2b3'
down_revision: Union[str, None] = '90d96d683b85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'order_items',
        sa.Column(
            'farmer_response',
            sa.Enum(
                'PENDING', 'ACCEPTED', 'REJECTED',
                name='farmer_response_status', native_enum=False,
            ),
            nullable=False,
            server_default='PENDING',
        ),
    )
    op.create_index(
        op.f('ix_order_items_farmer_response'),
        'order_items',
        ['farmer_response'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_order_items_farmer_response'), table_name='order_items'
    )
    op.drop_column('order_items', 'farmer_response')
