"""initial schema: all 44 tables

Revision ID: 90d96d683b85
Revises: 
Create Date: 2026-10-25 02:24:38.745357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90d96d683b85'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alembic autogenerate - please adjust!
    op.create_table('commodities',
    sa.Column('name_en', sa.String(length=80), nullable=False),
    sa.Column('name_te', sa.String(length=80), nullable=True),
    sa.Column('name_hi', sa.String(length=80), nullable=True),
    sa.Column('category', sa.Enum('FRUIT', 'VEGETABLE', 'GRAIN', 'PULSE', 'OTHER', name='commodity_category', native_enum=False), nullable=False),
    sa.Column('default_unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_commodities'))
    )
    op.create_index(op.f('ix_commodities_category'), 'commodities', ['category'], unique=False)
    op.create_index(op.f('ix_commodities_name_en'), 'commodities', ['name_en'], unique=True)
    op.create_table('fpo_profiles',
    sa.Column('name', sa.String(length=180), nullable=False),
    sa.Column('registration_number', sa.String(length=60), nullable=True),
    sa.Column('district', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=120), nullable=False),
    sa.Column('address_line', sa.String(length=255), nullable=True),
    sa.Column('lat', sa.Double(), nullable=True),
    sa.Column('lng', sa.Double(), nullable=True),
    sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fpo_profiles')),
    sa.UniqueConstraint('registration_number', name=op.f('uq_fpo_profiles_registration_number'))
    )
    op.create_index(op.f('ix_fpo_profiles_district'), 'fpo_profiles', ['district'], unique=False)
    op.create_index(op.f('ix_fpo_profiles_name'), 'fpo_profiles', ['name'], unique=False)
    op.create_index(op.f('ix_fpo_profiles_verification_status'), 'fpo_profiles', ['verification_status'], unique=False)
    op.create_table('model_runs',
    sa.Column('model_type', sa.Enum('PRICE_RECOMMENDATION', 'DEMAND_FORECAST', 'ROUTING', 'QUALITY', name='model_type', native_enum=False), nullable=False),
    sa.Column('model_version', sa.String(length=40), nullable=False),
    sa.Column('trained_on_from', sa.Date(), nullable=True),
    sa.Column('trained_on_to', sa.Date(), nullable=True),
    sa.Column('training_data_description', sa.Text(), nullable=True),
    sa.Column('metrics', sa.JSON(), nullable=True),
    sa.Column('parameters', sa.JSON(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('ran_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_model_runs'))
    )
    op.create_index(op.f('ix_model_runs_model_type'), 'model_runs', ['model_type'], unique=False)
    op.create_table('otp_codes',
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_otp_codes'))
    )
    op.create_index(op.f('ix_otp_codes_expires_at'), 'otp_codes', ['expires_at'], unique=False)
    op.create_index(op.f('ix_otp_codes_phone'), 'otp_codes', ['phone'], unique=False)
    op.create_table('collection_centres',
    sa.Column('fpo_id', sa.Uuid(), nullable=True),
    sa.Column('name', sa.String(length=180), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=120), nullable=False),
    sa.Column('address_line', sa.String(length=255), nullable=True),
    sa.Column('lat', sa.Double(), nullable=True),
    sa.Column('lng', sa.Double(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['fpo_id'], ['fpo_profiles.id'], name=op.f('fk_collection_centres_fpo_id_fpo_profiles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_collection_centres'))
    )
    op.create_index(op.f('ix_collection_centres_district'), 'collection_centres', ['district'], unique=False)
    op.create_index(op.f('ix_collection_centres_fpo_id'), 'collection_centres', ['fpo_id'], unique=False)
    op.create_table('commodity_varieties',
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_commodity_varieties_commodity_id_commodities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_commodity_varieties'))
    )
    op.create_index(op.f('ix_commodity_varieties_commodity_id'), 'commodity_varieties', ['commodity_id'], unique=False)
    op.create_table('demand_forecasts',
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('forecast_for', sa.Date(), nullable=False),
    sa.Column('horizon_days', sa.Integer(), nullable=False),
    sa.Column('predicted_demand_qty', sa.Float(), nullable=True),
    sa.Column('predicted_price_paise', sa.Integer(), nullable=True),
    sa.Column('lower_bound_paise', sa.Integer(), nullable=True),
    sa.Column('upper_bound_paise', sa.Integer(), nullable=True),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=True),
    sa.Column('trend', sa.String(length=20), nullable=True),
    sa.Column('planning_notes', sa.Text(), nullable=True),
    sa.Column('model_run_id', sa.Uuid(), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_demand_forecasts_commodity_id_commodities')),
    sa.ForeignKeyConstraint(['model_run_id'], ['model_runs.id'], name=op.f('fk_demand_forecasts_model_run_id_model_runs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_demand_forecasts'))
    )
    op.create_index(op.f('ix_demand_forecasts_commodity_id'), 'demand_forecasts', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_demand_forecasts_district'), 'demand_forecasts', ['district'], unique=False)
    op.create_index(op.f('ix_demand_forecasts_forecast_for'), 'demand_forecasts', ['forecast_for'], unique=False)
    op.create_index(op.f('ix_demand_forecasts_model_run_id'), 'demand_forecasts', ['model_run_id'], unique=False)
    op.create_table('market_price_observations',
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('market_name', sa.String(length=160), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=120), nullable=False),
    sa.Column('observed_on', sa.Date(), nullable=False),
    sa.Column('min_price_paise', sa.Integer(), nullable=True),
    sa.Column('modal_price_paise', sa.Integer(), nullable=True),
    sa.Column('max_price_paise', sa.Integer(), nullable=True),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=True),
    sa.Column('arrival_quantity', sa.Float(), nullable=True),
    sa.Column('source', sa.Enum('AGMARKNET', 'CONSUMER_AFFAIRS', 'PLATFORM_TRANSACTION', 'SYNTHETIC', name='price_source_type', native_enum=False), nullable=False),
    sa.Column('source_ref', sa.String(length=200), nullable=True),
    sa.Column('data_quality', sa.Enum('VALID', 'STALE', 'ANOMALOUS', 'MISSING_FIELDS', name='data_quality_status', native_enum=False), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=True),
    sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_market_price_observations_commodity_id_commodities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_market_price_observations'))
    )
    op.create_index(op.f('ix_market_price_observations_commodity_id'), 'market_price_observations', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_market_price_observations_data_quality'), 'market_price_observations', ['data_quality'], unique=False)
    op.create_index(op.f('ix_market_price_observations_district'), 'market_price_observations', ['district'], unique=False)
    op.create_index('ix_mpo_commodity_district_date', 'market_price_observations', ['commodity_id', 'district', 'observed_on'], unique=False)
    op.create_table('users',
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=True),
    sa.Column('preferred_language', sa.String(length=10), nullable=False),
    sa.Column('demo_code', sa.String(length=40), nullable=True),
    sa.Column('fpo_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'SUSPENDED', name='user_status', native_enum=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['fpo_id'], ['fpo_profiles.id'], name=op.f('fk_users_fpo_id_fpo_profiles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('demo_code', name=op.f('uq_users_demo_code'))
    )
    op.create_index(op.f('ix_users_fpo_id'), 'users', ['fpo_id'], unique=False)
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)
    op.create_table('audit_logs',
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_role', sa.String(length=30), nullable=True),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('entity_type', sa.String(length=60), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=True),
    sa.Column('before', sa.JSON(), nullable=True),
    sa.Column('after', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_logs_actor_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    op.create_table('business_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('business_name', sa.String(length=160), nullable=False),
    sa.Column('business_type', sa.Enum('KIRANA', 'HOTEL', 'RESTAURANT', 'CANTEEN', 'INSTITUTION', 'OTHER', name='business_type', native_enum=False), nullable=False),
    sa.Column('gstin', sa.String(length=20), nullable=True),
    sa.Column('address_line', sa.String(length=255), nullable=True),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('state', sa.String(length=120), nullable=True),
    sa.Column('pincode', sa.String(length=10), nullable=True),
    sa.Column('lat', sa.Double(), nullable=True),
    sa.Column('lng', sa.Double(), nullable=True),
    sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_business_profiles_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_business_profiles')),
    sa.UniqueConstraint('user_id', name='uq_business_profiles_user_id')
    )
    op.create_index(op.f('ix_business_profiles_district'), 'business_profiles', ['district'], unique=False)
    op.create_index(op.f('ix_business_profiles_user_id'), 'business_profiles', ['user_id'], unique=False)
    op.create_index(op.f('ix_business_profiles_verification_status'), 'business_profiles', ['verification_status'], unique=False)
    op.create_table('buyer_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('address_line', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=120), nullable=True),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('state', sa.String(length=120), nullable=True),
    sa.Column('pincode', sa.String(length=10), nullable=True),
    sa.Column('lat', sa.Double(), nullable=True),
    sa.Column('lng', sa.Double(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_buyer_profiles_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_buyer_profiles')),
    sa.UniqueConstraint('user_id', name='uq_buyer_profiles_user_id')
    )
    op.create_index(op.f('ix_buyer_profiles_district'), 'buyer_profiles', ['district'], unique=False)
    op.create_index(op.f('ix_buyer_profiles_user_id'), 'buyer_profiles', ['user_id'], unique=False)
    op.create_table('carts',
    sa.Column('buyer_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], name=op.f('fk_carts_buyer_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_carts')),
    sa.UniqueConstraint('buyer_id', name='uq_carts_buyer_id')
    )
    op.create_index(op.f('ix_carts_buyer_id'), 'carts', ['buyer_id'], unique=False)
    op.create_table('data_import_jobs',
    sa.Column('source', sa.Enum('AGMARKNET', 'CONSUMER_AFFAIRS', 'PLATFORM_TRANSACTION', 'SYNTHETIC', name='price_source_type', native_enum=False), nullable=False),
    sa.Column('status', sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='import_job_status', native_enum=False), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('records_read', sa.Integer(), nullable=False),
    sa.Column('records_written', sa.Integer(), nullable=False),
    sa.Column('records_rejected', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('triggered_by', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], name=op.f('fk_data_import_jobs_triggered_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_data_import_jobs'))
    )
    op.create_table('driver_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('license_number', sa.String(length=40), nullable=True),
    sa.Column('service_district', sa.String(length=120), nullable=True),
    sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.Column('last_lat', sa.Double(), nullable=True),
    sa.Column('last_lng', sa.Double(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_driver_profiles_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_driver_profiles')),
    sa.UniqueConstraint('user_id', name='uq_driver_profiles_user_id')
    )
    op.create_index(op.f('ix_driver_profiles_service_district'), 'driver_profiles', ['service_district'], unique=False)
    op.create_index(op.f('ix_driver_profiles_user_id'), 'driver_profiles', ['user_id'], unique=False)
    op.create_index(op.f('ix_driver_profiles_verification_status'), 'driver_profiles', ['verification_status'], unique=False)
    op.create_table('farmer_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('village', sa.String(length=120), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=120), nullable=False),
    sa.Column('farm_lat', sa.Double(), nullable=True),
    sa.Column('farm_lng', sa.Double(), nullable=True),
    sa.Column('fpo_id', sa.Uuid(), nullable=True),
    sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verified_by', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['fpo_id'], ['fpo_profiles.id'], name=op.f('fk_farmer_profiles_fpo_id_fpo_profiles')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_farmer_profiles_user_id_users')),
    sa.ForeignKeyConstraint(['verified_by'], ['users.id'], name=op.f('fk_farmer_profiles_verified_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_farmer_profiles')),
    sa.UniqueConstraint('user_id', name='uq_farmer_profiles_user_id')
    )
    op.create_index(op.f('ix_farmer_profiles_district'), 'farmer_profiles', ['district'], unique=False)
    op.create_index(op.f('ix_farmer_profiles_fpo_id'), 'farmer_profiles', ['fpo_id'], unique=False)
    op.create_index(op.f('ix_farmer_profiles_user_id'), 'farmer_profiles', ['user_id'], unique=False)
    op.create_index(op.f('ix_farmer_profiles_verification_status'), 'farmer_profiles', ['verification_status'], unique=False)
    op.create_table('orders',
    sa.Column('buyer_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('CREATED', 'AWAITING_FARMER_CONFIRMATION', 'ACCEPTED', 'PAYMENT_PENDING', 'CONFIRMED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'PAYMENT_FAILED', 'REFUND_PENDING', 'REFUNDED', 'DELIVERY_FAILED', 'DISPUTED', name='order_status', native_enum=False), nullable=False),
    sa.Column('payment_status', sa.Enum('INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'REFUND_PENDING', 'PARTIALLY_REFUNDED', 'REFUNDED', name='payment_status', native_enum=False), nullable=False),
    sa.Column('fulfilment', sa.Enum('DELIVERY', 'PICKUP', name='fulfilment_type', native_enum=False), nullable=False),
    sa.Column('delivery_name', sa.String(length=160), nullable=True),
    sa.Column('delivery_phone', sa.String(length=20), nullable=True),
    sa.Column('delivery_address', sa.String(length=400), nullable=True),
    sa.Column('delivery_district', sa.String(length=120), nullable=True),
    sa.Column('delivery_lat', sa.Double(), nullable=True),
    sa.Column('delivery_lng', sa.Double(), nullable=True),
    sa.Column('subtotal_paise', sa.Integer(), nullable=False),
    sa.Column('delivery_fee_paise', sa.Integer(), nullable=False),
    sa.Column('platform_fee_paise', sa.Integer(), nullable=False),
    sa.Column('total_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('idempotency_key', sa.String(length=80), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('cancel_reason', sa.Text(), nullable=True),
    sa.Column('placed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], name=op.f('fk_orders_buyer_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_orders')),
    sa.UniqueConstraint('idempotency_key', name='uq_orders_idempotency_key')
    )
    op.create_index(op.f('ix_orders_buyer_id'), 'orders', ['buyer_id'], unique=False)
    op.create_index('ix_orders_buyer_status_created', 'orders', ['buyer_id', 'status', 'created_at'], unique=False)
    op.create_index(op.f('ix_orders_delivery_district'), 'orders', ['delivery_district'], unique=False)
    op.create_index(op.f('ix_orders_idempotency_key'), 'orders', ['idempotency_key'], unique=False)
    op.create_index(op.f('ix_orders_payment_status'), 'orders', ['payment_status'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index('ix_orders_status_created', 'orders', ['status', 'created_at'], unique=False)
    op.create_table('platform_settings',
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('value', sa.JSON(), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_platform_settings_updated_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_platform_settings'))
    )
    op.create_index(op.f('ix_platform_settings_key'), 'platform_settings', ['key'], unique=True)
    op.create_table('produce_listings',
    sa.Column('farmer_id', sa.Uuid(), nullable=False),
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('variety_id', sa.Uuid(), nullable=True),
    sa.Column('collection_centre_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('quantity_total', sa.Double(), nullable=False),
    sa.Column('quantity_reserved', sa.Double(), nullable=False),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=False),
    sa.Column('quality_grade', sa.Enum('A', 'B', 'C', 'UNGRADED', name='quality_grade', native_enum=False), nullable=False),
    sa.Column('harvest_date', sa.Date(), nullable=True),
    sa.Column('available_from', sa.Date(), nullable=True),
    sa.Column('min_price_paise', sa.Integer(), nullable=False),
    sa.Column('listed_price_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'PAUSED', 'SOLD_OUT', 'WITHDRAWN', name='listing_status', native_enum=False), nullable=False),
    sa.Column('farm_lat', sa.Double(), nullable=True),
    sa.Column('farm_lng', sa.Double(), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['collection_centre_id'], ['collection_centres.id'], name=op.f('fk_produce_listings_collection_centre_id_collection_centres')),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_produce_listings_commodity_id_commodities')),
    sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], name=op.f('fk_produce_listings_farmer_id_users')),
    sa.ForeignKeyConstraint(['variety_id'], ['commodity_varieties.id'], name=op.f('fk_produce_listings_variety_id_commodity_varieties')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_produce_listings'))
    )
    op.create_index(op.f('ix_produce_listings_collection_centre_id'), 'produce_listings', ['collection_centre_id'], unique=False)
    op.create_index(op.f('ix_produce_listings_commodity_id'), 'produce_listings', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_produce_listings_farmer_id'), 'produce_listings', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_produce_listings_status'), 'produce_listings', ['status'], unique=False)
    op.create_index('ix_produce_listings_status_commodity', 'produce_listings', ['status', 'commodity_id'], unique=False)
    op.create_table('purchase_requests',
    sa.Column('business_user_id', sa.Uuid(), nullable=False),
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('quantity', sa.Double(), nullable=False),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=False),
    sa.Column('needed_by', sa.Date(), nullable=True),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('max_price_paise', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('OPEN', 'QUOTED', 'CLOSED', 'CANCELLED', name='purchase_request_status', native_enum=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['business_user_id'], ['users.id'], name=op.f('fk_purchase_requests_business_user_id_users')),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_purchase_requests_commodity_id_commodities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_requests'))
    )
    op.create_index(op.f('ix_purchase_requests_business_user_id'), 'purchase_requests', ['business_user_id'], unique=False)
    op.create_index(op.f('ix_purchase_requests_commodity_id'), 'purchase_requests', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_purchase_requests_district'), 'purchase_requests', ['district'], unique=False)
    op.create_index(op.f('ix_purchase_requests_status'), 'purchase_requests', ['status'], unique=False)
    op.create_table('user_roles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.Enum('FARMER', 'BUYER', 'BUSINESS', 'DRIVER', 'FPO_OPERATOR', 'ADMIN', name='role_enum', native_enum=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_roles')),
    sa.UniqueConstraint('user_id', 'role', name='uq_user_roles_user_id_role')
    )
    op.create_index(op.f('ix_user_roles_user_id'), 'user_roles', ['user_id'], unique=False)
    op.create_table('vehicles',
    sa.Column('driver_id', sa.Uuid(), nullable=True),
    sa.Column('plate_number', sa.String(length=20), nullable=False),
    sa.Column('vehicle_type', sa.Enum('BIKE', 'AUTO', 'MINI_TRUCK', 'TEMPO', 'TRUCK', name='vehicle_type', native_enum=False), nullable=False),
    sa.Column('capacity_kg', sa.Integer(), nullable=False),
    sa.Column('service_district', sa.String(length=120), nullable=True),
    sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], name=op.f('fk_vehicles_driver_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicles')),
    sa.UniqueConstraint('plate_number', name=op.f('uq_vehicles_plate_number'))
    )
    op.create_index(op.f('ix_vehicles_driver_id'), 'vehicles', ['driver_id'], unique=False)
    op.create_index(op.f('ix_vehicles_service_district'), 'vehicles', ['service_district'], unique=False)
    op.create_table('cart_items',
    sa.Column('cart_id', sa.Uuid(), nullable=False),
    sa.Column('listing_id', sa.Uuid(), nullable=False),
    sa.Column('quantity', sa.Double(), nullable=False),
    sa.Column('unit_price_paise', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], name=op.f('fk_cart_items_cart_id_carts')),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_cart_items_listing_id_produce_listings')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cart_items')),
    sa.UniqueConstraint('cart_id', 'listing_id', name='uq_cart_items_cart_listing')
    )
    op.create_index(op.f('ix_cart_items_cart_id'), 'cart_items', ['cart_id'], unique=False)
    op.create_index(op.f('ix_cart_items_listing_id'), 'cart_items', ['listing_id'], unique=False)
    op.create_table('farmer_settlements',
    sa.Column('farmer_id', sa.Uuid(), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('gross_paise', sa.Integer(), nullable=False),
    sa.Column('deductions_paise', sa.Integer(), nullable=False),
    sa.Column('net_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('breakdown', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'PAID', 'FAILED', name='settlement_status', native_enum=False), nullable=False),
    sa.Column('payout_ref', sa.String(length=100), nullable=True),
    sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], name=op.f('fk_farmer_settlements_farmer_id_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_farmer_settlements_order_id_orders')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_farmer_settlements')),
    sa.UniqueConstraint('order_id', 'farmer_id', name='uq_farmer_settlements')
    )
    op.create_index(op.f('ix_farmer_settlements_farmer_id'), 'farmer_settlements', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_farmer_settlements_order_id'), 'farmer_settlements', ['order_id'], unique=False)
    op.create_index(op.f('ix_farmer_settlements_status'), 'farmer_settlements', ['status'], unique=False)
    op.create_table('inventory_reservations',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('listing_id', sa.Uuid(), nullable=False),
    sa.Column('quantity', sa.Double(), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'CONSUMED', 'RELEASED', name='reservation_status', native_enum=False), nullable=False),
    sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_inventory_reservations_listing_id_produce_listings')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_inventory_reservations_order_id_orders'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inventory_reservations')),
    sa.UniqueConstraint('order_id', 'listing_id', name='uq_res_order_listing')
    )
    op.create_index(op.f('ix_inventory_reservations_listing_id'), 'inventory_reservations', ['listing_id'], unique=False)
    op.create_index(op.f('ix_inventory_reservations_order_id'), 'inventory_reservations', ['order_id'], unique=False)
    op.create_index(op.f('ix_inventory_reservations_status'), 'inventory_reservations', ['status'], unique=False)
    op.create_table('listing_images',
    sa.Column('listing_id', sa.Uuid(), nullable=False),
    sa.Column('image_path', sa.String(length=500), nullable=False),
    sa.Column('content_type', sa.String(length=60), nullable=True),
    sa.Column('size_bytes', sa.Integer(), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_listing_images_listing_id_produce_listings'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_listing_images'))
    )
    op.create_index(op.f('ix_listing_images_listing_id'), 'listing_images', ['listing_id'], unique=False)
    op.create_table('offers',
    sa.Column('purchase_request_id', sa.Uuid(), nullable=False),
    sa.Column('farmer_id', sa.Uuid(), nullable=False),
    sa.Column('listing_id', sa.Uuid(), nullable=True),
    sa.Column('quantity', sa.Double(), nullable=False),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=False),
    sa.Column('price_paise', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'WITHDRAWN', name='offer_status', native_enum=False), nullable=False),
    sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], name=op.f('fk_offers_farmer_id_users')),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_offers_listing_id_produce_listings')),
    sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], name=op.f('fk_offers_purchase_request_id_purchase_requests')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_offers'))
    )
    op.create_index(op.f('ix_offers_farmer_id'), 'offers', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_offers_purchase_request_id'), 'offers', ['purchase_request_id'], unique=False)
    op.create_index(op.f('ix_offers_status'), 'offers', ['status'], unique=False)
    op.create_table('order_items',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('listing_id', sa.Uuid(), nullable=False),
    sa.Column('farmer_id', sa.Uuid(), nullable=False),
    sa.Column('commodity_id', sa.Uuid(), nullable=True),
    sa.Column('quantity', sa.Double(), nullable=False),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=True),
    sa.Column('unit_price_paise', sa.Integer(), nullable=False),
    sa.Column('line_total_paise', sa.Integer(), nullable=False),
    sa.Column('quality_grade', sa.Enum('A', 'B', 'C', 'UNGRADED', name='quality_grade', native_enum=False), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_order_items_commodity_id_commodities')),
    sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], name=op.f('fk_order_items_farmer_id_users')),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_order_items_listing_id_produce_listings')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_order_items_order_id_orders'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_items'))
    )
    op.create_index(op.f('ix_order_items_farmer_id'), 'order_items', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_order_items_listing_id'), 'order_items', ['listing_id'], unique=False)
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'], unique=False)
    op.create_table('order_status_events',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('from_status', sa.Enum('CREATED', 'AWAITING_FARMER_CONFIRMATION', 'ACCEPTED', 'PAYMENT_PENDING', 'CONFIRMED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'PAYMENT_FAILED', 'REFUND_PENDING', 'REFUNDED', 'DELIVERY_FAILED', 'DISPUTED', name='order_status', native_enum=False), nullable=True),
    sa.Column('to_status', sa.Enum('CREATED', 'AWAITING_FARMER_CONFIRMATION', 'ACCEPTED', 'PAYMENT_PENDING', 'CONFIRMED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'PAYMENT_FAILED', 'REFUND_PENDING', 'REFUNDED', 'DELIVERY_FAILED', 'DISPUTED', name='order_status', native_enum=False), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_role', sa.String(length=30), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_order_status_events_actor_user_id_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_order_status_events_order_id_orders'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_status_events'))
    )
    op.create_index(op.f('ix_order_status_events_order_id'), 'order_status_events', ['order_id'], unique=False)
    op.create_index('ix_ose_order_created', 'order_status_events', ['order_id', 'created_at'], unique=False)
    op.create_table('payment_transactions',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('provider', sa.Enum('MOCK', 'RAZORPAY', name='payment_provider_kind', native_enum=False), nullable=False),
    sa.Column('provider_ref', sa.String(length=100), nullable=True),
    sa.Column('amount_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.Enum('INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'REFUND_PENDING', 'PARTIALLY_REFUNDED', 'REFUNDED', name='payment_status', native_enum=False), nullable=False),
    sa.Column('is_sandbox', sa.Boolean(), nullable=False),
    sa.Column('initiated_by', sa.Uuid(), nullable=True),
    sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('provider_payload', sa.JSON(), nullable=True),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], name=op.f('fk_payment_transactions_initiated_by_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_payment_transactions_order_id_orders')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_transactions')),
    sa.UniqueConstraint('provider_ref', name=op.f('uq_payment_transactions_provider_ref'))
    )
    op.create_index(op.f('ix_payment_transactions_order_id'), 'payment_transactions', ['order_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_status'), 'payment_transactions', ['status'], unique=False)
    op.create_index('ix_paytxn_order_status', 'payment_transactions', ['order_id', 'status'], unique=False)
    op.create_table('price_recommendations',
    sa.Column('listing_id', sa.Uuid(), nullable=True),
    sa.Column('commodity_id', sa.Uuid(), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('recommended_min_paise', sa.Integer(), nullable=True),
    sa.Column('recommended_modal_paise', sa.Integer(), nullable=True),
    sa.Column('recommended_max_paise', sa.Integer(), nullable=True),
    sa.Column('unit', sa.Enum('KG', 'QUINTAL', 'TONNE', 'DOZEN', 'PIECE', 'LITRE', 'BUNCH', name='unit_enum', native_enum=False), nullable=True),
    sa.Column('benchmark_market', sa.String(length=160), nullable=True),
    sa.Column('benchmark_observed_on', sa.Date(), nullable=True),
    sa.Column('benchmark_source', sa.Enum('AGMARKNET', 'CONSUMER_AFFAIRS', 'PLATFORM_TRANSACTION', 'SYNTHETIC', name='price_source_type', native_enum=False), nullable=True),
    sa.Column('confidence', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='recommendation_confidence', native_enum=False), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('model_run_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_price_recommendations_commodity_id_commodities')),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_price_recommendations_listing_id_produce_listings')),
    sa.ForeignKeyConstraint(['model_run_id'], ['model_runs.id'], name=op.f('fk_price_recommendations_model_run_id_model_runs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_price_recommendations'))
    )
    op.create_index(op.f('ix_price_recommendations_commodity_id'), 'price_recommendations', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_price_recommendations_district'), 'price_recommendations', ['district'], unique=False)
    op.create_index(op.f('ix_price_recommendations_listing_id'), 'price_recommendations', ['listing_id'], unique=False)
    op.create_index(op.f('ix_price_recommendations_model_run_id'), 'price_recommendations', ['model_run_id'], unique=False)
    op.create_table('reviews',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Uuid(), nullable=False),
    sa.Column('farmer_id', sa.Uuid(), nullable=True),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name=op.f('ck_reviews_ck_reviews_rating_range')),
    sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], name=op.f('fk_reviews_farmer_id_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_reviews_order_id_orders')),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], name=op.f('fk_reviews_reviewer_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reviews')),
    sa.UniqueConstraint('order_id', name='uq_reviews_order_id')
    )
    op.create_index(op.f('ix_reviews_farmer_id'), 'reviews', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_reviews_order_id'), 'reviews', ['order_id'], unique=False)
    op.create_index(op.f('ix_reviews_reviewer_id'), 'reviews', ['reviewer_id'], unique=False)
    op.create_table('shipments',
    sa.Column('driver_id', sa.Uuid(), nullable=True),
    sa.Column('vehicle_id', sa.Uuid(), nullable=True),
    sa.Column('collection_centre_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.Enum('PLANNED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'FAILED', name='shipment_status', native_enum=False), nullable=False),
    sa.Column('planned_start_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('route_distance_km', sa.Float(), nullable=True),
    sa.Column('route_duration_min', sa.Integer(), nullable=True),
    sa.Column('route_data', sa.JSON(), nullable=True),
    sa.Column('solver', sa.String(length=40), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['collection_centre_id'], ['collection_centres.id'], name=op.f('fk_shipments_collection_centre_id_collection_centres')),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], name=op.f('fk_shipments_driver_id_users')),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_shipments_vehicle_id_vehicles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_shipments'))
    )
    op.create_index(op.f('ix_shipments_collection_centre_id'), 'shipments', ['collection_centre_id'], unique=False)
    op.create_index(op.f('ix_shipments_driver_id'), 'shipments', ['driver_id'], unique=False)
    op.create_index(op.f('ix_shipments_status'), 'shipments', ['status'], unique=False)
    op.create_table('crate_labels',
    sa.Column('shipment_id', sa.Uuid(), nullable=True),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('listing_id', sa.Uuid(), nullable=True),
    sa.Column('commodity_id', sa.Uuid(), nullable=True),
    sa.Column('quantity', sa.Double(), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('grade', sa.String(length=20), nullable=True),
    sa.Column('code', sa.String(length=24), nullable=False),
    sa.Column('qr_token', sa.String(length=64), nullable=False),
    sa.Column('status', sa.Enum('CREATED', 'SCANNED_PICKUP', 'SCANNED_DELIVERY', name='crate_status', native_enum=False), nullable=False),
    sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], name=op.f('fk_crate_labels_commodity_id_commodities')),
    sa.ForeignKeyConstraint(['listing_id'], ['produce_listings.id'], name=op.f('fk_crate_labels_listing_id_produce_listings')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_crate_labels_order_id_orders')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_crate_labels_shipment_id_shipments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_crate_labels'))
    )
    op.create_index(op.f('ix_crate_labels_code'), 'crate_labels', ['code'], unique=True)
    op.create_index(op.f('ix_crate_labels_listing_id'), 'crate_labels', ['listing_id'], unique=False)
    op.create_index(op.f('ix_crate_labels_order_id'), 'crate_labels', ['order_id'], unique=False)
    op.create_index(op.f('ix_crate_labels_qr_token'), 'crate_labels', ['qr_token'], unique=True)
    op.create_index(op.f('ix_crate_labels_shipment_id'), 'crate_labels', ['shipment_id'], unique=False)
    op.create_table('delivery_manifests',
    sa.Column('shipment_id', sa.Uuid(), nullable=False),
    sa.Column('manifest_number', sa.String(length=30), nullable=False),
    sa.Column('content', sa.JSON(), nullable=True),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_delivery_manifests_shipment_id_shipments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_delivery_manifests')),
    sa.UniqueConstraint('manifest_number', name=op.f('uq_delivery_manifests_manifest_number')),
    sa.UniqueConstraint('shipment_id', name='uq_manifests_shipment_id')
    )
    op.create_index(op.f('ix_delivery_manifests_shipment_id'), 'delivery_manifests', ['shipment_id'], unique=False)
    op.create_table('driver_settlements',
    sa.Column('driver_id', sa.Uuid(), nullable=False),
    sa.Column('shipment_id', sa.Uuid(), nullable=False),
    sa.Column('amount_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'PAID', 'FAILED', name='settlement_status', native_enum=False), nullable=False),
    sa.Column('payout_ref', sa.String(length=100), nullable=True),
    sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], name=op.f('fk_driver_settlements_driver_id_users')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_driver_settlements_shipment_id_shipments')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_driver_settlements')),
    sa.UniqueConstraint('driver_id', 'shipment_id', name='uq_driver_settlements')
    )
    op.create_index(op.f('ix_driver_settlements_driver_id'), 'driver_settlements', ['driver_id'], unique=False)
    op.create_index(op.f('ix_driver_settlements_shipment_id'), 'driver_settlements', ['shipment_id'], unique=False)
    op.create_index(op.f('ix_driver_settlements_status'), 'driver_settlements', ['status'], unique=False)
    op.create_table('grievances',
    sa.Column('raised_by', sa.Uuid(), nullable=False),
    sa.Column('category', sa.Enum('ORDER', 'PAYMENT', 'QUALITY', 'DELIVERY', 'OTHER', name='grievance_category', native_enum=False), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('shipment_id', sa.Uuid(), nullable=True),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'IN_PROGRESS', 'RESOLVED', 'REJECTED', 'CLOSED', name='grievance_status', native_enum=False), nullable=False),
    sa.Column('assigned_to', sa.Uuid(), nullable=True),
    sa.Column('ack_deadline_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], name=op.f('fk_grievances_assigned_to_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_grievances_order_id_orders')),
    sa.ForeignKeyConstraint(['raised_by'], ['users.id'], name=op.f('fk_grievances_raised_by_users')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_grievances_shipment_id_shipments')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_grievances'))
    )
    op.create_index(op.f('ix_grievances_order_id'), 'grievances', ['order_id'], unique=False)
    op.create_index(op.f('ix_grievances_raised_by'), 'grievances', ['raised_by'], unique=False)
    op.create_index(op.f('ix_grievances_shipment_id'), 'grievances', ['shipment_id'], unique=False)
    op.create_index(op.f('ix_grievances_status'), 'grievances', ['status'], unique=False)
    op.create_index('ix_grievances_status_created', 'grievances', ['status', 'created_at'], unique=False)
    op.create_table('ledger_entries',
    sa.Column('entry_type', sa.Enum('PAYMENT_IN', 'FARMER_PROCEEDS', 'PLATFORM_FEE', 'DELIVERY_FEE_IN', 'DRIVER_PAYOUT', 'REFUND_OUT', 'ADJUSTMENT', name='ledger_entry_type', native_enum=False), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('shipment_id', sa.Uuid(), nullable=True),
    sa.Column('payment_transaction_id', sa.Uuid(), nullable=True),
    sa.Column('debit_account', sa.String(length=100), nullable=False),
    sa.Column('credit_account', sa.String(length=100), nullable=False),
    sa.Column('amount_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('memo', sa.String(length=255), nullable=True),
    sa.Column('idempotency_key', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_ledger_entries_order_id_orders')),
    sa.ForeignKeyConstraint(['payment_transaction_id'], ['payment_transactions.id'], name=op.f('fk_ledger_entries_payment_transaction_id_payment_transactions')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_ledger_entries_shipment_id_shipments')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ledger_entries')),
    sa.UniqueConstraint('idempotency_key', name='uq_ledger_idempotency_key'),
    sa.UniqueConstraint('idempotency_key', name=op.f('uq_ledger_entries_idempotency_key'))
    )
    op.create_index(op.f('ix_ledger_entries_order_id'), 'ledger_entries', ['order_id'], unique=False)
    op.create_index(op.f('ix_ledger_entries_shipment_id'), 'ledger_entries', ['shipment_id'], unique=False)
    op.create_index('ix_ledger_order_type', 'ledger_entries', ['order_id', 'entry_type'], unique=False)
    op.create_table('notifications',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel', sa.Enum('IN_APP', 'SMS', 'VOICE', name='notification_channel', native_enum=False), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('status', sa.Enum('QUEUED', 'SENT', 'DELIVERED', 'READ', 'FAILED', name='notification_status', native_enum=False), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('related_order_id', sa.Uuid(), nullable=True),
    sa.Column('related_shipment_id', sa.Uuid(), nullable=True),
    sa.Column('meta', sa.JSON(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['related_order_id'], ['orders.id'], name=op.f('fk_notifications_related_order_id_orders')),
    sa.ForeignKeyConstraint(['related_shipment_id'], ['shipments.id'], name=op.f('fk_notifications_related_shipment_id_shipments')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index(op.f('ix_notifications_category'), 'notifications', ['category'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_user_status', 'notifications', ['user_id', 'status'], unique=False)
    op.create_table('payment_webhook_events',
    sa.Column('provider', sa.Enum('MOCK', 'RAZORPAY', name='payment_provider_kind', native_enum=False), nullable=False),
    sa.Column('event_id', sa.String(length=120), nullable=False),
    sa.Column('event_type', sa.String(length=80), nullable=False),
    sa.Column('signature_valid', sa.Boolean(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processing_error', sa.Text(), nullable=True),
    sa.Column('transaction_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['transaction_id'], ['payment_transactions.id'], name=op.f('fk_payment_webhook_events_transaction_id_payment_transactions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_webhook_events'))
    )
    op.create_index(op.f('ix_payment_webhook_events_event_id'), 'payment_webhook_events', ['event_id'], unique=True)
    op.create_table('refunds',
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('payment_transaction_id', sa.Uuid(), nullable=True),
    sa.Column('amount_paise', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('REQUESTED', 'PROCESSING', 'PROCESSED', 'FAILED', name='refund_status', native_enum=False), nullable=False),
    sa.Column('requested_by', sa.Uuid(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('provider_ref', sa.String(length=100), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_refunds_order_id_orders')),
    sa.ForeignKeyConstraint(['payment_transaction_id'], ['payment_transactions.id'], name=op.f('fk_refunds_payment_transaction_id_payment_transactions')),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_refunds_requested_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refunds'))
    )
    op.create_index(op.f('ix_refunds_order_id'), 'refunds', ['order_id'], unique=False)
    op.create_index(op.f('ix_refunds_status'), 'refunds', ['status'], unique=False)
    op.create_table('shipment_stops',
    sa.Column('shipment_id', sa.Uuid(), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('stop_type', sa.Enum('PICKUP', 'DELIVERY', name='stop_type', native_enum=False), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ARRIVED', 'COMPLETED', 'FAILED', name='stop_status', native_enum=False), nullable=False),
    sa.Column('lat', sa.Double(), nullable=True),
    sa.Column('lng', sa.Double(), nullable=True),
    sa.Column('label', sa.String(length=160), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_shipment_stops_order_id_orders')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_shipment_stops_shipment_id_shipments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_shipment_stops')),
    sa.UniqueConstraint('shipment_id', 'sequence', name='uq_stops_shipment_sequence')
    )
    op.create_index(op.f('ix_shipment_stops_order_id'), 'shipment_stops', ['order_id'], unique=False)
    op.create_index(op.f('ix_shipment_stops_shipment_id'), 'shipment_stops', ['shipment_id'], unique=False)
    op.create_index('ix_stops_shipment_status', 'shipment_stops', ['shipment_id', 'status'], unique=False)
    op.create_table('communication_logs',
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('notification_id', sa.Uuid(), nullable=True),
    sa.Column('channel', sa.Enum('IN_APP', 'SMS', 'VOICE', name='notification_channel', native_enum=False), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('provider_message_id', sa.String(length=120), nullable=True),
    sa.Column('recipient', sa.String(length=30), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('status', sa.Enum('QUEUED', 'SENT', 'DELIVERED', 'FAILED', name='communication_status', native_enum=False), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], name=op.f('fk_communication_logs_notification_id_notifications')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_communication_logs_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_communication_logs'))
    )
    op.create_index(op.f('ix_communication_logs_user_id'), 'communication_logs', ['user_id'], unique=False)
    op.create_table('qr_verification_events',
    sa.Column('qr_code', sa.String(length=64), nullable=False),
    sa.Column('purpose', sa.Enum('PICKUP_VERIFICATION', 'DELIVERY_VERIFICATION', name='qr_purpose', native_enum=False), nullable=False),
    sa.Column('method', sa.Enum('QR_SCAN', 'MANUAL_CODE', 'OPERATOR_OVERRIDE', name='qr_method', native_enum=False), nullable=False),
    sa.Column('shipment_id', sa.Uuid(), nullable=True),
    sa.Column('stop_id', sa.Uuid(), nullable=True),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_qr_verification_events_actor_user_id_users')),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_qr_verification_events_order_id_orders')),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], name=op.f('fk_qr_verification_events_shipment_id_shipments')),
    sa.ForeignKeyConstraint(['stop_id'], ['shipment_stops.id'], name=op.f('fk_qr_verification_events_stop_id_shipment_stops')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qr_verification_events'))
    )
    op.create_index('ix_qr_stop_purpose', 'qr_verification_events', ['stop_id', 'purpose'], unique=False)
    op.create_index(op.f('ix_qr_verification_events_qr_code'), 'qr_verification_events', ['qr_code'], unique=False)
    op.create_index(op.f('ix_qr_verification_events_shipment_id'), 'qr_verification_events', ['shipment_id'], unique=False)
    op.create_index(op.f('ix_qr_verification_events_stop_id'), 'qr_verification_events', ['stop_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Alembic autogenerate - please adjust!
    op.drop_index(op.f('ix_qr_verification_events_stop_id'), table_name='qr_verification_events')
    op.drop_index(op.f('ix_qr_verification_events_shipment_id'), table_name='qr_verification_events')
    op.drop_index(op.f('ix_qr_verification_events_qr_code'), table_name='qr_verification_events')
    op.drop_index('ix_qr_stop_purpose', table_name='qr_verification_events')
    op.drop_table('qr_verification_events')
    op.drop_index(op.f('ix_communication_logs_user_id'), table_name='communication_logs')
    op.drop_table('communication_logs')
    op.drop_index('ix_stops_shipment_status', table_name='shipment_stops')
    op.drop_index(op.f('ix_shipment_stops_shipment_id'), table_name='shipment_stops')
    op.drop_index(op.f('ix_shipment_stops_order_id'), table_name='shipment_stops')
    op.drop_table('shipment_stops')
    op.drop_index(op.f('ix_refunds_status'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_order_id'), table_name='refunds')
    op.drop_table('refunds')
    op.drop_index(op.f('ix_payment_webhook_events_event_id'), table_name='payment_webhook_events')
    op.drop_table('payment_webhook_events')
    op.drop_index('ix_notifications_user_status', table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_category'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_ledger_order_type', table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_shipment_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_order_id'), table_name='ledger_entries')
    op.drop_table('ledger_entries')
    op.drop_index('ix_grievances_status_created', table_name='grievances')
    op.drop_index(op.f('ix_grievances_status'), table_name='grievances')
    op.drop_index(op.f('ix_grievances_shipment_id'), table_name='grievances')
    op.drop_index(op.f('ix_grievances_raised_by'), table_name='grievances')
    op.drop_index(op.f('ix_grievances_order_id'), table_name='grievances')
    op.drop_table('grievances')
    op.drop_index(op.f('ix_driver_settlements_status'), table_name='driver_settlements')
    op.drop_index(op.f('ix_driver_settlements_shipment_id'), table_name='driver_settlements')
    op.drop_index(op.f('ix_driver_settlements_driver_id'), table_name='driver_settlements')
    op.drop_table('driver_settlements')
    op.drop_index(op.f('ix_delivery_manifests_shipment_id'), table_name='delivery_manifests')
    op.drop_table('delivery_manifests')
    op.drop_index(op.f('ix_crate_labels_shipment_id'), table_name='crate_labels')
    op.drop_index(op.f('ix_crate_labels_qr_token'), table_name='crate_labels')
    op.drop_index(op.f('ix_crate_labels_order_id'), table_name='crate_labels')
    op.drop_index(op.f('ix_crate_labels_listing_id'), table_name='crate_labels')
    op.drop_index(op.f('ix_crate_labels_code'), table_name='crate_labels')
    op.drop_table('crate_labels')
    op.drop_index(op.f('ix_shipments_status'), table_name='shipments')
    op.drop_index(op.f('ix_shipments_driver_id'), table_name='shipments')
    op.drop_index(op.f('ix_shipments_collection_centre_id'), table_name='shipments')
    op.drop_table('shipments')
    op.drop_index(op.f('ix_reviews_reviewer_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_order_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_farmer_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_price_recommendations_model_run_id'), table_name='price_recommendations')
    op.drop_index(op.f('ix_price_recommendations_listing_id'), table_name='price_recommendations')
    op.drop_index(op.f('ix_price_recommendations_district'), table_name='price_recommendations')
    op.drop_index(op.f('ix_price_recommendations_commodity_id'), table_name='price_recommendations')
    op.drop_table('price_recommendations')
    op.drop_index('ix_paytxn_order_status', table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_status'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_order_id'), table_name='payment_transactions')
    op.drop_table('payment_transactions')
    op.drop_index('ix_ose_order_created', table_name='order_status_events')
    op.drop_index(op.f('ix_order_status_events_order_id'), table_name='order_status_events')
    op.drop_table('order_status_events')
    op.drop_index(op.f('ix_order_items_order_id'), table_name='order_items')
    op.drop_index(op.f('ix_order_items_listing_id'), table_name='order_items')
    op.drop_index(op.f('ix_order_items_farmer_id'), table_name='order_items')
    op.drop_table('order_items')
    op.drop_index(op.f('ix_offers_status'), table_name='offers')
    op.drop_index(op.f('ix_offers_purchase_request_id'), table_name='offers')
    op.drop_index(op.f('ix_offers_farmer_id'), table_name='offers')
    op.drop_table('offers')
    op.drop_index(op.f('ix_listing_images_listing_id'), table_name='listing_images')
    op.drop_table('listing_images')
    op.drop_index(op.f('ix_inventory_reservations_status'), table_name='inventory_reservations')
    op.drop_index(op.f('ix_inventory_reservations_order_id'), table_name='inventory_reservations')
    op.drop_index(op.f('ix_inventory_reservations_listing_id'), table_name='inventory_reservations')
    op.drop_table('inventory_reservations')
    op.drop_index(op.f('ix_farmer_settlements_status'), table_name='farmer_settlements')
    op.drop_index(op.f('ix_farmer_settlements_order_id'), table_name='farmer_settlements')
    op.drop_index(op.f('ix_farmer_settlements_farmer_id'), table_name='farmer_settlements')
    op.drop_table('farmer_settlements')
    op.drop_index(op.f('ix_cart_items_listing_id'), table_name='cart_items')
    op.drop_index(op.f('ix_cart_items_cart_id'), table_name='cart_items')
    op.drop_table('cart_items')
    op.drop_index(op.f('ix_vehicles_service_district'), table_name='vehicles')
    op.drop_index(op.f('ix_vehicles_driver_id'), table_name='vehicles')
    op.drop_table('vehicles')
    op.drop_index(op.f('ix_user_roles_user_id'), table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index(op.f('ix_purchase_requests_status'), table_name='purchase_requests')
    op.drop_index(op.f('ix_purchase_requests_district'), table_name='purchase_requests')
    op.drop_index(op.f('ix_purchase_requests_commodity_id'), table_name='purchase_requests')
    op.drop_index(op.f('ix_purchase_requests_business_user_id'), table_name='purchase_requests')
    op.drop_table('purchase_requests')
    op.drop_index('ix_produce_listings_status_commodity', table_name='produce_listings')
    op.drop_index(op.f('ix_produce_listings_status'), table_name='produce_listings')
    op.drop_index(op.f('ix_produce_listings_farmer_id'), table_name='produce_listings')
    op.drop_index(op.f('ix_produce_listings_commodity_id'), table_name='produce_listings')
    op.drop_index(op.f('ix_produce_listings_collection_centre_id'), table_name='produce_listings')
    op.drop_table('produce_listings')
    op.drop_index(op.f('ix_platform_settings_key'), table_name='platform_settings')
    op.drop_table('platform_settings')
    op.drop_index('ix_orders_status_created', table_name='orders')
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_payment_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_idempotency_key'), table_name='orders')
    op.drop_index(op.f('ix_orders_delivery_district'), table_name='orders')
    op.drop_index('ix_orders_buyer_status_created', table_name='orders')
    op.drop_index(op.f('ix_orders_buyer_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_farmer_profiles_verification_status'), table_name='farmer_profiles')
    op.drop_index(op.f('ix_farmer_profiles_user_id'), table_name='farmer_profiles')
    op.drop_index(op.f('ix_farmer_profiles_fpo_id'), table_name='farmer_profiles')
    op.drop_index(op.f('ix_farmer_profiles_district'), table_name='farmer_profiles')
    op.drop_table('farmer_profiles')
    op.drop_index(op.f('ix_driver_profiles_verification_status'), table_name='driver_profiles')
    op.drop_index(op.f('ix_driver_profiles_user_id'), table_name='driver_profiles')
    op.drop_index(op.f('ix_driver_profiles_service_district'), table_name='driver_profiles')
    op.drop_table('driver_profiles')
    op.drop_table('data_import_jobs')
    op.drop_index(op.f('ix_carts_buyer_id'), table_name='carts')
    op.drop_table('carts')
    op.drop_index(op.f('ix_buyer_profiles_user_id'), table_name='buyer_profiles')
    op.drop_index(op.f('ix_buyer_profiles_district'), table_name='buyer_profiles')
    op.drop_table('buyer_profiles')
    op.drop_index(op.f('ix_business_profiles_verification_status'), table_name='business_profiles')
    op.drop_index(op.f('ix_business_profiles_user_id'), table_name='business_profiles')
    op.drop_index(op.f('ix_business_profiles_district'), table_name='business_profiles')
    op.drop_table('business_profiles')
    op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index('ix_audit_entity', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_users_status'), table_name='users')
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_index(op.f('ix_users_fpo_id'), table_name='users')
    op.drop_table('users')
    op.drop_index('ix_mpo_commodity_district_date', table_name='market_price_observations')
    op.drop_index(op.f('ix_market_price_observations_district'), table_name='market_price_observations')
    op.drop_index(op.f('ix_market_price_observations_data_quality'), table_name='market_price_observations')
    op.drop_index(op.f('ix_market_price_observations_commodity_id'), table_name='market_price_observations')
    op.drop_table('market_price_observations')
    op.drop_index(op.f('ix_demand_forecasts_model_run_id'), table_name='demand_forecasts')
    op.drop_index(op.f('ix_demand_forecasts_forecast_for'), table_name='demand_forecasts')
    op.drop_index(op.f('ix_demand_forecasts_district'), table_name='demand_forecasts')
    op.drop_index(op.f('ix_demand_forecasts_commodity_id'), table_name='demand_forecasts')
    op.drop_table('demand_forecasts')
    op.drop_index(op.f('ix_commodity_varieties_commodity_id'), table_name='commodity_varieties')
    op.drop_table('commodity_varieties')
    op.drop_index(op.f('ix_collection_centres_fpo_id'), table_name='collection_centres')
    op.drop_index(op.f('ix_collection_centres_district'), table_name='collection_centres')
    op.drop_table('collection_centres')
    op.drop_index(op.f('ix_otp_codes_phone'), table_name='otp_codes')
    op.drop_index(op.f('ix_otp_codes_expires_at'), table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_index(op.f('ix_model_runs_model_type'), table_name='model_runs')
    op.drop_table('model_runs')
    op.drop_index(op.f('ix_fpo_profiles_verification_status'), table_name='fpo_profiles')
    op.drop_index(op.f('ix_fpo_profiles_name'), table_name='fpo_profiles')
    op.drop_index(op.f('ix_fpo_profiles_district'), table_name='fpo_profiles')
    op.drop_table('fpo_profiles')
    op.drop_index(op.f('ix_commodities_name_en'), table_name='commodities')
    op.drop_index(op.f('ix_commodities_category'), table_name='commodities')
    op.drop_table('commodities')
    # ### end Alembic commands ###
