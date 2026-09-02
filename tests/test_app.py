import os
import sys
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['SKILLARC_DATABASE_URI'] = 'sqlite:///:memory:'
from app import (app, db, assistant_answer, impact, metrics, warnings, User, District, TEAM_ACCOUNTS, ensure_demo_users,
                 TrainingProgram, TrainingProvider, Employer, Skill, SkillGap, Trainee,
                 Assessment, EmploymentRecord, FollowUp, Consent, AuditLog)


@pytest.fixture(autouse=True)
def clean_database():
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', SECRET_KEY='test-key')
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        db.session.add_all([
            User(email='admin@test.demo', name='Admin', role='State Administrator', password_hash=generate_password_hash('DemoPass1!')),
            User(email='employer@test.demo', name='Employer User', role='Employer', password_hash=generate_password_hash('DemoPass1!')),
        ])
        db.session.commit()
    yield
    with app.app_context():
        db.session.remove()


def login(client, email='admin@test.demo', password='DemoPass1!'):
    return client.post('/login', data={'email': email, 'password': password})


def controlled_outcomes():
    """Build a deliberately small dataset whose ratios can be verified exactly."""
    d = District(name='Pune')
    program = TrainingProgram(name='Data Analytics', category='Technology')
    provider = TrainingProvider(name='Test Institute', satisfaction=80)
    employer = Employer(company='Verified Works', industry='Technology', district=d, verification_status='VERIFIED')
    skill = Skill(name='Python')
    db.session.add_all([d, program, provider, employer, skill])
    db.session.flush()
    today = date.today()
    trainees = [
        Trainee(trainee_code='T-001', name='Placed One', district=d, program=program, provider=provider,
                enrolled_date=today - timedelta(days=300), completion_date=today - timedelta(days=200), certified=True,
                placement_date=today - timedelta(days=180), employment_status='Employed', retention_months=12, skills='Python'),
        Trainee(trainee_code='T-002', name='Placed Two', district=d, program=program, provider=provider,
                enrolled_date=today - timedelta(days=300), completion_date=today - timedelta(days=200), certified=True,
                placement_date=today - timedelta(days=170), employment_status='Employed', retention_months=6, skills='Python'),
        Trainee(trainee_code='T-003', name='Certified Not Placed', district=d, program=program, provider=provider,
                enrolled_date=today - timedelta(days=300), completion_date=today - timedelta(days=150), certified=True,
                employment_status='Unemployed', retention_months=0, skills='Python'),
        Trainee(trainee_code='T-004', name='Not Certified', district=d, program=program, provider=provider,
                enrolled_date=today - timedelta(days=20), certified=False, employment_status='Unemployed', retention_months=0, skills='Python'),
    ]
    db.session.add_all(trainees)
    db.session.flush()
    db.session.add_all([
        EmploymentRecord(trainee=trainees[0], employer=employer, role='Analyst', start_date=today - timedelta(days=180), starting_salary=20000, current_salary=26000, verified=True),
        EmploymentRecord(trainee=trainees[1], employer=employer, role='Associate', start_date=today - timedelta(days=170), starting_salary=18000, current_salary=22000, verified=True),
        SkillGap(skill=skill, demand=80, supply=50, recommendation='Increase practical Python capacity.'),
    ])
    db.session.commit()
    return trainees, employer


def test_login_logout_and_authorization():
    client = app.test_client()
    assert client.get('/dashboard').status_code == 302
    assert login(client, password='wrong').status_code == 200
    assert login(client).status_code == 302
    assert client.get('/dashboard').status_code == 200
    assert client.get('/logout').status_code == 302
    assert client.get('/dashboard').status_code == 302
    login(client, email='employer@test.demo')
    with app.app_context():
        _, employer = controlled_outcomes()
        employer_id = employer.id
    response = client.post(f'/employers/{employer_id}', data={'verification_status': 'VERIFIED'})
    assert response.status_code == 403


def test_six_named_demo_accounts_share_password_and_enforce_scope():
    with app.app_context():
        ensure_demo_users()
        users = User.query.filter(User.email.in_([entry[0] for entry in TEAM_ACCOUNTS])).all()
        assert {(u.email, u.name, u.role) for u in users} == set(TEAM_ACCOUNTS)
    for email, _, _ in TEAM_ACCOUNTS:
        client = app.test_client()
        assert login(client, email=email, password='Skillarc@2026').status_code == 302
        assert client.get('/dashboard').status_code == 200
    client = app.test_client(); login(client, email='nidhi@skillarc.demo', password='Skillarc@2026')
    assert client.get('/employers').status_code == 403


def test_dashboard_calculations_render_and_change_with_database():
    with app.app_context():
        trainees, _ = controlled_outcomes()
        actual = metrics()
        assert actual['total'] == 4
        assert (actual['completed'], actual['certified'], actual['placed'], actual['employed']) == (3, 3, 2, 2)
        assert (actual['placement_rate'], actual['employment_rate'], actual['r6'], actual['r12']) == (67, 67, 100, 50)
        assert (actual['start_wage'], actual['current_wage'], actual['verified_employers'], actual['skill_gap_alerts']) == (19000, 24000, 1, 1)
    client = app.test_client(); login(client)
    page = client.get('/dashboard').data
    assert b'Total Trainees</small><b>4' in page
    assert b'Employment Rate</small><b>67%' in page
    assert b'Average Current Wage</small><b>' in page
    with app.app_context():
        trainees[2].employment_status = 'Employed'
        trainees[2].retention_months = 6
        db.session.add(EmploymentRecord(trainee=trainees[2], employer_id=1, role='Analyst', start_date=date.today(), starting_salary=21000, current_salary=21000))
        db.session.commit()
        assert metrics()['employment_rate'] == 100
    assert b'Employment Rate</small><b>100%' in client.get('/dashboard').data


def test_skill_gap_policy_answer_and_filters_are_database_driven():
    with app.app_context():
        trainees, _ = controlled_outcomes()
        assert assistant_answer('Which skill gap should we prioritize?').startswith('Python is the highest recorded gap')
        gap = SkillGap.query.one(); gap.supply = 75; db.session.commit()
        assert '80% employer demand versus 50% trainee supply' not in assistant_answer('Which skill gap should we prioritize?')
        assert 'demand 80%, supply 75%' in assistant_answer('Which skill gap should we prioritize?')
    client = app.test_client(); login(client)
    assert b'Placed One' in client.get('/trainees?placement=placed&retention=6m').data
    filtered = client.get('/trainees?placement=not_placed').data
    assert b'Certified Not Placed' in filtered and b'Placed One' not in filtered


def test_early_warning_rules_and_persistent_workflows():
    with app.app_context():
        trainees, employer = controlled_outcomes()
        delayed, employed = trainees[2], trainees[0]
        db.session.add(Assessment(trainee=employed, skill='Python', score=40))
        db.session.add(FollowUp(trainee=employed, followup_type='6 Month', due_date=date.today() - timedelta(days=1), status='Overdue', channel='Phone'))
        db.session.add(Consent(trainee=employed, purpose='Wage progression', status='Pending'))
        db.session.commit()
        triggered = {(row[0].trainee_code, row[1]) for row in warnings()}
        assert ('T-003', 'Placement delay') in triggered
        assert ('T-001', 'Assessment') in triggered
        assert ('T-001', 'Follow-up') in triggered
        assert ('T-004', 'Placement delay') not in triggered
        followup_id = FollowUp.query.one().id
        consent_id = Consent.query.one().id
    client = app.test_client(); login(client)
    assert client.post('/followups', data={'followup_id': followup_id, 'status': 'Completed', 'response': 'Employed', 'notes': 'Confirmed'}).status_code == 302
    assert client.post('/privacy', data={'consent_id': consent_id, 'status': 'Consented'}).status_code == 302
    with app.app_context():
        assert FollowUp.query.get(followup_id).status == 'Completed'
        assert Consent.query.get(consent_id).status == 'Consented'
        actions = {row.action for row in AuditLog.query.all()}
        assert {'Follow-up updated', 'Consent changed'} <= actions


def test_empty_data_and_404_do_not_crash():
    client = app.test_client(); login(client)
    with app.app_context():
        assert metrics()['total'] == 0
    assert client.get('/dashboard').status_code == 200
    assert client.post('/policy-assistant', data={'question': 'Which skill gap should we prioritize?'}).status_code == 200
    assert client.get('/trainees?q=none').status_code == 200
    assert client.get('/does-not-exist').status_code == 404


def test_authenticated_shell_and_policy_chat_api():
    with app.app_context():
        controlled_outcomes()
    client = app.test_client(); login(client)
    page = client.get('/dashboard').data
    assert b'id="nav-toggle"' in page and b'aria-controls="site-navigation"' in page
    assert b'Dashboard' in page and b'Settings' not in page and b'Log out' in page
    assert b'id="policy-mascot"' in page and b'class="arco-name">ARKO' in page
    assert b'images/arko-researcher.svg' in page
    assert client.get('/static/images/arko-researcher.svg').status_code == 200
    response = client.post('/api/policy-assistant', json={'question':'Which skill gap should we prioritize?'})
    assert response.status_code == 200
    assert response.json['answer'].startswith('Python is the highest recorded gap')
    assert client.post('/api/policy-assistant', json={'question':''}).status_code == 400


def test_arko_intents_and_lightweight_context_are_database_driven():
    with app.app_context():
        trainees, _ = controlled_outcomes()
        db.session.add(FollowUp(trainee=trainees[0], followup_type='6 Month', due_date=date.today(), status='Overdue', channel='Phone'))
        db.session.commit()
        overview = assistant_answer('How many trainees are there?')
        assert '4 trainees' in overview and 'Employment rate 67%' in overview
        state_answer = assistant_answer('Which state has the lowest employment rate?')
        assert 'Maharashtra' in state_answer
        assert 'Data Analytics' in assistant_answer('Which program has the best placement rate?')
        assert 'Python is the highest recorded gap' in assistant_answer('What are the biggest skill gaps?')
        assert 'follow-ups need attention' in assistant_answer('Who needs follow-up?')
        assert 'average current wage is Rs 24,000' in assistant_answer('What is the average current wage?')
        context = {}
        assistant_answer('How is Pune performing?', context)
        assert 'For Pune, placement is' in assistant_answer('What about placement?', context)
        assert 'I can help with outcomes' in assistant_answer('Tell me a poem about clouds')


def test_arko_retention_no_data_and_employee_privacy():
    """ARKO must calculate retention, decline empty datasets, and protect employee access."""
    with app.app_context():
        trainees, _ = controlled_outcomes()
        trainees[0].email = 'placed.one@employee.skillarc.local'
        trainees[0].password_hash = generate_password_hash('Employee@2026')
        db.session.commit()
        retention = assistant_answer('Which state has the lowest 6 month retention?')
        assert '6-month retention 100%' in retention
        context = {}
        assistant_answer('How is Pune performing?', context)
        assert 'For Pune, six-month retention is 100%' in assistant_answer('And retention?', context)

    client = app.test_client()
    assert client.post('/api/policy-assistant', json={'question': 'How many trainees are there?'}).status_code == 302
    assert client.post('/employee-login', data={'email': 'placed.one@employee.skillarc.local', 'password': 'Employee@2026'}).status_code == 302
    restricted = client.post('/api/policy-assistant', json={'question': "What is another employee's salary?"})
    assert restricted.status_code == 403

    with app.app_context():
        db.drop_all(); db.create_all()
        assert "don't have enough recorded data" in assistant_answer('How many trainees are there?')
