from __future__ import annotations
import os, sys
from sqlalchemy import create_engine, text
url=os.getenv('DATABASE_URL','')
if not url.startswith(('postgresql://','postgresql+psycopg://','postgres://')):
    raise SystemExit('DATABASE_URL must point to the pilot PostgreSQL database')
if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
elif url.startswith('postgresql://') and '+psycopg' not in url: url=url.replace('postgresql://','postgresql+psycopg://',1)
expected={'term_progress','exam_results','course_day_results','gamification_profiles','xp_events','practice_results','game_sessions','learning_preferences','notification_preferences','learning_nudges','srs_cards','question_attempts','pilot_daily_usage'}
eng=create_engine(url,pool_pre_ping=True)
with eng.connect() as c:
    rows=c.execute(text("""select c.relname,c.relrowsecurity,c.relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=current_schema() and c.relname = any(:tables)"""),{'tables':list(expected)}).all()
    policies=c.execute(text("select tablename,policyname,qual,with_check from pg_policies where schemaname=current_schema() and policyname='mgc_department_scope'")).all()
    role=c.execute(text("select current_user, rolsuper, rolbypassrls from pg_roles where rolname=current_user")).one()
state={r[0]:(bool(r[1]),bool(r[2])) for r in rows}; policy_tables={r[0] for r in policies}
missing=sorted(expected-set(state)); bad=sorted(t for t,v in state.items() if v!=(True,True)); no_policy=sorted(expected-policy_tables)
weak_policy=sorted(r[0] for r in policies if not r[2] or 'app.user_id' not in r[2] or 'app.role' not in r[2] or not r[3])
print('DB role:',role[0],'superuser=',bool(role[1]),'bypassrls=',bool(role[2]))
print('RLS tables:',len(state),'policies:',len(policy_tables))
if role[1] or role[2]:
    print('FAIL: application DB role must not be superuser or BYPASSRLS'); sys.exit(3)
if missing or bad or no_policy or weak_policy:
    print('MISSING:',missing); print('NOT FORCE ENABLED:',bad); print('NO POLICY:',no_policy); print('WEAK POLICY:',weak_policy); sys.exit(2)
print('PASS: PostgreSQL RLS is ENABLED + FORCED, policies bind app identity, and the application role cannot bypass RLS')
