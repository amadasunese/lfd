"""empty message

Revision ID: 1c339205290a
Revises: 
Create Date: 2025-11-26 17:45:28.558057

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c339205290a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('paystack_ref', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('payment_status', sa.String(length=20), nullable=True))
        # 👇 add a name
        batch_op.create_unique_constraint('uq_order_paystack_ref', ['paystack_ref'])


def downgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        # 👇 use the **same** name
        batch_op.drop_constraint('uq_order_paystack_ref', type_='unique')
        batch_op.drop_column('payment_status')
        batch_op.drop_column('paystack_ref')

    # ### end Alembic commands ###
