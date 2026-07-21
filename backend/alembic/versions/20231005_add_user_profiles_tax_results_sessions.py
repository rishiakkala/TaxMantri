from alembic import op
import sqlalchemy as sa

revision = '20231005_add_user_profiles_tax_results_sessions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('personal_details', sa.JSON, nullable=False),
        sa.Column('financial_details', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'tax_results',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('user_id', sa.String, sa.ForeignKey('user_profiles.id'), nullable=False),
        sa.Column('old_regime', sa.JSON, nullable=False),
        sa.Column('new_regime', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'sessions',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('user_id', sa.String, sa.ForeignKey('user_profiles.id'), nullable=False),
        sa.Column('actions', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'chat_history',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('user_id', sa.String, sa.ForeignKey('user_profiles.id'), nullable=False),
        sa.Column('messages', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('chat_history')
    op.drop_table('sessions')
    op.drop_table('tax_results')
    op.drop_table('user_profiles')