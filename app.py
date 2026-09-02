import os, random
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'skillarc-demo-key'), SQLALCHEMY_DATABASE_URI=os.environ.get('SKILLARC_DATABASE_URI', 'sqlite:///' + os.path.join(app.instance_path, 'skillarc.db')), SQLALCHEMY_TRACK_MODIFICATIONS=False)
os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True); email=db.Column(db.String(120), unique=True); name=db.Column(db.String(80)); role=db.Column(db.String(30)); password_hash=db.Column(db.String(255)); district_id=db.Column(db.Integer, db.ForeignKey('district.id')); first_login_at=db.Column(db.DateTime, nullable=True); avatar=db.Column(db.String(20), default='male')
class District(db.Model):
    id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(80), unique=True); state=db.Column(db.String(100), default='Maharashtra'); trainees=db.relationship('Trainee', backref='district', lazy=True)
class TrainingProgram(db.Model):
    id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(120), unique=True); category=db.Column(db.String(60)); trainees=db.relationship('Trainee', backref='program', lazy=True)
class TrainingProvider(db.Model):
    id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(120)); satisfaction=db.Column(db.Float, default=80); trainees=db.relationship('Trainee', backref='provider', lazy=True)
class Employer(db.Model):
    id=db.Column(db.Integer, primary_key=True); company=db.Column(db.String(120)); industry=db.Column(db.String(80)); district_id=db.Column(db.Integer, db.ForeignKey('district.id')); verification_status=db.Column(db.String(30), default='UNVERIFIED'); requested_skills=db.Column(db.String(250)); district=db.relationship('District')
class Skill(db.Model):
    id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(80), unique=True)
class Trainee(db.Model):
    id=db.Column(db.Integer, primary_key=True); trainee_code=db.Column(db.String(30), unique=True); name=db.Column(db.String(100)); district_id=db.Column(db.Integer, db.ForeignKey('district.id')); program_id=db.Column(db.Integer, db.ForeignKey('training_program.id')); provider_id=db.Column(db.Integer, db.ForeignKey('training_provider.id')); enrolled_date=db.Column(db.Date); completion_date=db.Column(db.Date, nullable=True); certified=db.Column(db.Boolean, default=False); placement_date=db.Column(db.Date, nullable=True); employment_status=db.Column(db.String(30), default='Unemployed'); retention_months=db.Column(db.Integer, default=0); nonplacement_reason=db.Column(db.String(100)); attrition_reason=db.Column(db.String(100)); skills=db.Column(db.String(250)); email=db.Column(db.String(120), unique=True, nullable=True); password_hash=db.Column(db.String(255), nullable=True); first_login_at=db.Column(db.DateTime, nullable=True); avatar=db.Column(db.String(20), default='male'); assessments=db.relationship('Assessment', backref='trainee', lazy=True, cascade='all, delete-orphan'); employments=db.relationship('EmploymentRecord', backref='trainee', lazy=True, cascade='all, delete-orphan'); followups=db.relationship('FollowUp', backref='trainee', lazy=True, cascade='all, delete-orphan'); consents=db.relationship('Consent', backref='trainee', lazy=True, cascade='all, delete-orphan')
class Assessment(db.Model):
    id=db.Column(db.Integer, primary_key=True); trainee_id=db.Column(db.Integer, db.ForeignKey('trainee.id')); skill=db.Column(db.String(80)); score=db.Column(db.Integer)
class EmploymentRecord(db.Model):
    id=db.Column(db.Integer, primary_key=True); trainee_id=db.Column(db.Integer, db.ForeignKey('trainee.id')); employer_id=db.Column(db.Integer, db.ForeignKey('employer.id')); role=db.Column(db.String(100)); start_date=db.Column(db.Date); end_date=db.Column(db.Date, nullable=True); starting_salary=db.Column(db.Integer); current_salary=db.Column(db.Integer); verified=db.Column(db.Boolean, default=False); employer=db.relationship('Employer'); wages=db.relationship('WageRecord', backref='employment', lazy=True, cascade='all, delete-orphan')
class WageRecord(db.Model):
    id=db.Column(db.Integer, primary_key=True); employment_id=db.Column(db.Integer, db.ForeignKey('employment_record.id')); recorded_date=db.Column(db.Date); amount=db.Column(db.Integer)
class FollowUp(db.Model):
    id=db.Column(db.Integer, primary_key=True); trainee_id=db.Column(db.Integer, db.ForeignKey('trainee.id')); followup_type=db.Column(db.String(40)); due_date=db.Column(db.Date); status=db.Column(db.String(30)); channel=db.Column(db.String(30)); response=db.Column(db.String(80)); notes=db.Column(db.String(300))
class Consent(db.Model):
    id=db.Column(db.Integer, primary_key=True); trainee_id=db.Column(db.Integer, db.ForeignKey('trainee.id')); purpose=db.Column(db.String(100)); status=db.Column(db.String(30)); updated_at=db.Column(db.DateTime, default=datetime.utcnow)
class SkillGap(db.Model):
    id=db.Column(db.Integer, primary_key=True); skill_id=db.Column(db.Integer, db.ForeignKey('skill.id')); demand=db.Column(db.Integer); supply=db.Column(db.Integer); recommendation=db.Column(db.String(200)); skill=db.relationship('Skill')
class AuditLog(db.Model):
    id=db.Column(db.Integer, primary_key=True); timestamp=db.Column(db.DateTime, default=datetime.utcnow); user_name=db.Column(db.String(80)); role=db.Column(db.String(30)); action=db.Column(db.String(100)); record=db.Column(db.String(150)); status=db.Column(db.String(30), default='Completed')

TEAM_ACCOUNTS = [
 ('praveen@skillarc.demo', 'Praveen', 'State Administrator'),
 ('nidhi@skillarc.demo', 'Nidhi', 'District Officer'),
 ('tanishq@skillarc.demo', 'Tanishq', 'Training Provider Manager'),
 ('aditya@skillarc.demo', 'Aditya', 'Employer Partner'),
 ('shristi@skillarc.demo', 'Srishti', 'Outcome & Follow-up Officer'),
 ('jayant@skillarc.demo', 'Jayant', 'Data & Intelligence Officer'),
]
ROLE_ENDPOINTS = {
 'State Administrator': {'*'},
 'District Officer': {'dashboard','trainees','trainee_detail','districts','analytics','early_warning','followups','reports','settings','privacy'},
 'Training Provider Manager': {'dashboard','trainees','trainee_detail','programs','providers','analytics','settings'},
 'Employer Partner': {'dashboard','trainees','trainee_detail','employers','employer_detail','skill_gaps','reports','settings'},
 'Outcome & Follow-up Officer': {'dashboard','trainees','trainee_detail','followups','early_warning','reports','settings','privacy'},
 'Data & Intelligence Officer': {'dashboard','districts','analytics','skill_gaps','early_warning','policy_assistant','reports','audit_logs','settings'},
}
FEMALE_NAMES = {'Aditi','Ananya','Isha','Kavya','Meera','Nisha','Priya','Saanvi','Srishti','Nidhi'}
def avatar_gender(name, gender=None):
 """Deterministic local avatar variant for synthetic people; no image service is used."""
 if gender: return 'female' if gender.lower().startswith('f') else 'male'
 return 'female' if (name or '').split(' ')[0] in FEMALE_NAMES else 'male'
def current_user(): return db.session.get(User, session.get('user_id')) if session.get('user_id') else None
def current_employee(): return db.session.get(Trainee, session.get('employee_id')) if session.get('employee_id') else None
@app.context_processor
def inject():
 user=current_user(); allowed=ROLE_ENDPOINTS.get(user.role, set()) if user else set()
 return {'current_user':user, 'current_employee':current_employee(), 'today':date.today(), 'avatar_gender':avatar_gender, 'allowed_endpoints':allowed}
def login_required(f):
 @wraps(f)
 def wrapper(*a, **k):
  user=current_user()
  if current_employee(): abort(403)
  if not user: return redirect(url_for('login', next=request.path))
  allowed=ROLE_ENDPOINTS.get(user.role, set())
  if f.__name__ != 'policy_assistant_api' and '*' not in allowed and f.__name__ not in allowed: abort(403)
  return f(*a, **k)
 return wrapper
def roles_required(*roles):
 def decorator(f):
  @wraps(f)
  def wrapper(*a, **k):
   user=current_user()
   if not user: return redirect(url_for('login', next=request.path))
   if user.role not in roles: abort(403)
   return f(*a, **k)
  return wrapper
 return decorator
def audit(action, record):
 u=current_user(); db.session.add(AuditLog(user_name=u.name if u else 'System', role=u.role if u else 'System', action=action, record=record)); db.session.commit()
def rate(n,d): return round(100*n/d) if d else 0
def status_badge(s): return s
app.jinja_env.filters['money']=lambda n: '₹{:,.0f}'.format(n or 0)

def metrics(items=None):
 ts=items or Trainee.query.all(); total=len(ts); completed=[t for t in ts if t.completion_date]; certified=[t for t in ts if t.certified]; placed=[t for t in ts if t.placement_date]; employed=[t for t in ts if t.employment_status in ('Employed','Self-employed','Apprenticeship')]; emps=[e for t in ts for e in t.employments if not e.end_date];
 return {'total':total,'completed':len(completed),'certified':len(certified),'placed':len(placed),'employed':len(employed),'r3':rate(len([t for t in employed if t.retention_months>=3]),len(employed)),'r6':rate(len([t for t in employed if t.retention_months>=6]),len(employed)),'r12':rate(len([t for t in employed if t.retention_months>=12]),len(employed)),'placement_rate':rate(len(placed),len(certified)),'employment_rate':rate(len(employed),len(certified)),'start_wage':round(sum(e.starting_salary for e in emps)/len(emps)) if emps else 0,'current_wage':round(sum(e.current_salary for e in emps)/len(emps)) if emps else 0,'verified_employers':Employer.query.filter_by(verification_status='VERIFIED').count(),'skill_gap_alerts':SkillGap.query.filter((SkillGap.demand-SkillGap.supply) > 0).count()}
def program_rows():
 rows=[]
 for p in TrainingProgram.query.all():
  m=metrics(p.trainees); rows.append({'name':p.name,**m,'wage_growth':m['current_wage']-m['start_wage']})
 return sorted(rows,key=lambda r:r['placement_rate'],reverse=True)
def district_rows():
 return sorted([{'name':d.name,**metrics(d.trainees)} for d in District.query.all()],key=lambda r:r['employment_rate'])
def state_rows():
 """Aggregate existing city records into state-level outcome metrics."""
 rows=[]
 for state, in db.session.query(District.state).distinct().order_by(District.state):
  trainees=Trainee.query.join(District).filter(District.state==state).all()
  if trainees: rows.append({'name':state,**metrics(trainees)})
 return rows
def provider_rows():
 return sorted([{'name':p.name,**metrics(p.trainees),'impact':impact(p)} for p in TrainingProvider.query.all()],key=lambda r:(r['placement_rate'],r['r6']),reverse=True)
def employer_rows():
 rows=[]
 for employer in Employer.query.all():
  records=EmploymentRecord.query.filter_by(employer_id=employer.id).all()
  rows.append({'name':employer.company,'placements':len(records),'active':len([r for r in records if not r.end_date])})
 return sorted(rows,key=lambda r:r['placements'],reverse=True)
def impact(provider):
 m=metrics(provider.trainees); growth=min(100, max(0,(m['current_wage']-m['start_wage'])/100)); return round(.30*m['placement_rate']+.25*m['r6']+.20*growth+.15*rate(m['completed'],m['total'])+.10*provider.satisfaction)
def warnings():
 rows=[]
 for t in Trainee.query.all():
  if t.certified and t.completion_date and not t.placement_date and (date.today()-t.completion_date).days>90: rows.append((t,'Placement delay','More than 90 days after completion','High','Placement support recommended'))
  if any(a.score<50 for a in t.assessments): rows.append((t,'Assessment','Important assessment below threshold','Medium','Skill development recommended'))
  recent_changes=[e for e in t.employments if e.start_date and e.start_date >= date.today()-timedelta(days=365)]
  if len(recent_changes)>1: rows.append((t,'Job change','Multiple job changes within 12 months','Medium','Retention review recommended'))
  if any(f.status in ('Overdue','Due Today') for f in t.followups): rows.append((t,'Follow-up','Outcome check requires attention','High','Follow-up required'))
 return rows

@app.route('/')
def home(): return render_template('home.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  user=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
  if user and check_password_hash(user.password_hash,request.form.get('password','')):
   session.clear(); session['user_id']=user.id
   if not user.first_login_at: user.first_login_at=datetime.utcnow(); db.session.commit()
   audit('Signed in','Account'); return redirect(request.args.get('next') or url_for('dashboard'))
  flash('Invalid email or password.', 'error')
 return render_template('login.html', demo_accounts=TEAM_ACCOUNTS)
@app.route('/employee-login',methods=['GET','POST'])
def employee_login():
 if request.method=='POST':
  employee=Trainee.query.filter_by(email=request.form.get('email','').strip().lower()).first()
  if employee and employee.password_hash and check_password_hash(employee.password_hash,request.form.get('password','')):
   session.clear(); session['employee_id']=employee.id
   if not employee.first_login_at: employee.first_login_at=datetime.utcnow(); db.session.commit()
   return redirect(url_for('employee_dashboard'))
  flash('Invalid employee email or password.', 'error')
 return render_template('employee_login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))
def employee_required(f):
 @wraps(f)
 def wrapper(*a, **k):
  if not current_employee(): return redirect(url_for('employee_login'))
  return f(*a, **k)
 return wrapper
@app.route('/employee-dashboard')
@employee_required
def employee_dashboard(): return render_template('employee_dashboard.html', t=current_employee())
@app.post('/profile/avatar')
def profile_avatar():
 choice=request.form.get('avatar')
 if choice not in ('male','female'): abort(400)
 user=current_user() or current_employee()
 if not user: abort(403)
 user.avatar=choice; db.session.commit(); flash('Profile picture updated.','success')
 return redirect(request.referrer or url_for('dashboard' if current_user() else 'employee_dashboard'))
@app.route('/dashboard')
@login_required
def dashboard():
 m=metrics(); return render_template('dashboard.html',m=m, districts=district_rows(), programs=program_rows(), gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).limit(5).all(), activities=AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all(), warns=warnings()[:6])

@app.route('/trainees')
@login_required
def trainees():
 q=Trainee.query; search=request.args.get('q','').strip(); district=request.args.get('district',''); state=request.args.get('state',''); program=request.args.get('program',''); provider=request.args.get('provider',''); placement=request.args.get('placement',''); status=request.args.get('status',''); retention=request.args.get('retention','')
 if state: q=q.join(District).filter(District.state==state)
 if search: q=q.filter((Trainee.name.ilike(f'%{search}%'))|(Trainee.trainee_code.ilike(f'%{search}%')))
 if district: q=q.filter_by(district_id=district)
 if program: q=q.filter_by(program_id=program)
 if provider: q=q.filter_by(provider_id=provider)
 if placement == 'placed': q=q.filter(Trainee.placement_date.isnot(None))
 if placement == 'not_placed': q=q.filter(Trainee.placement_date.is_(None))
 if status: q=q.filter_by(employment_status=status)
 if retention == '6m': q=q.filter(Trainee.retention_months >= 6)
 if retention == 'under_6m': q=q.filter(Trainee.retention_months < 6)
 return render_template('trainees.html',trainees=q.order_by(Trainee.name).all(),districts=District.query.order_by(District.state,District.name).all(),states=[x[0] for x in db.session.query(District.state).distinct().order_by(District.state)],programs=TrainingProgram.query.all(),providers=TrainingProvider.query.all())
@app.route('/trainees/<int:id>',methods=['GET','POST'])
@login_required
def trainee_detail(id):
 t=db.get_or_404(Trainee,id)
 if current_user().role=='Trainee' and current_user().name != t.name: abort(403)
 if request.method=='POST':
  allowed={'Employed','Unemployed','Self-employed','Apprenticeship'}; status=request.form.get('employment_status',t.employment_status)
  try: retention=max(0,int(request.form.get('retention_months',t.retention_months) or 0))
  except ValueError: abort(400)
  if status not in allowed or retention>600: abort(400)
  t.employment_status=status; t.retention_months=retention; db.session.commit(); audit('Trainee updated',t.trainee_code); flash('Profile update saved.','success'); return redirect(url_for('trainee_detail',id=id))
 return render_template('trainee_detail.html',t=t)

@app.route('/employers')
@login_required
def employers(): return render_template('employers.html', employers=Employer.query.all())
@app.route('/employers/<int:id>',methods=['GET','POST'])
@login_required
def employer_detail(id):
 e=db.get_or_404(Employer,id)
 if request.method=='POST':
  if current_user().role not in ('State Administrator','District Officer','Employer Partner'): abort(403)
  status=request.form.get('verification_status','')
  if status not in ('UNVERIFIED','SUBMITTED','UNDER REVIEW','VERIFIED'): abort(400)
  e.verification_status=status; db.session.commit(); audit('Employer verification updated',e.company); flash('Verification status saved.','success'); return redirect(url_for('employer_detail',id=id))
 hires=EmploymentRecord.query.filter_by(employer_id=id).all(); return render_template('employer_detail.html',e=e,hires=hires)
@app.route('/followups',methods=['GET','POST'])
@login_required
def followups():
 if request.method=='POST':
  try: f=db.get_or_404(FollowUp,int(request.form['followup_id']))
  except (TypeError, ValueError): abort(400)
  status=request.form.get('status',''); response=request.form.get('response','')
  if status not in ('Completed','Overdue','Due Today','Escalated','Unable to Contact') or response not in ('','Employed','Changed Job','Unemployed','Self-employed','Apprenticeship','Unable to Reach'): abort(400)
  f.status=status; f.response=response; f.notes=request.form.get('notes','')[:300]; db.session.commit(); audit('Follow-up updated',f.trainee.trainee_code); flash('Demo follow-up response saved.','success'); return redirect(url_for('followups'))
 return render_template('followups.html',followups=FollowUp.query.order_by(FollowUp.due_date).all())
@app.route('/privacy',methods=['GET','POST'])
@login_required
def privacy():
 if request.method=='POST':
  try: c=db.get_or_404(Consent,int(request.form['consent_id']))
  except (TypeError, ValueError): abort(400)
  status=request.form.get('status','')
  if status not in ('Consented','Pending','Withdrawn'): abort(400)
  c.status=status; c.updated_at=datetime.utcnow(); db.session.commit(); audit('Consent changed',c.trainee.trainee_code); flash('Consent preference updated.','success'); return redirect(url_for('privacy'))
 return render_template('privacy.html',consents=Consent.query.order_by(Consent.updated_at.desc()).limit(50).all())
@app.route('/skill-gaps')
@login_required
def skill_gaps(): return render_template('skill_gaps.html',gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).all())
@app.route('/programs')
@login_required
def programs(): return render_template('programs.html',rows=program_rows())
@app.route('/providers')
@login_required
def providers(): return render_template('providers.html',providers=[{'p':p,'m':metrics(p.trainees),'impact':impact(p)} for p in TrainingProvider.query.all()])
@app.route('/districts')
@login_required
def districts(): return render_template('districts.html',rows=district_rows())
@app.route('/analytics')
@login_required
def analytics(): return render_template('analytics.html',m=metrics(),programs=program_rows(),districts=district_rows(),gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).limit(6).all())
@app.route('/early-warning')
@login_required
def early_warning(): return render_template('early_warning.html',warnings=warnings())
def assistant_answer_legacy(question):
 q=question.lower(); ds=district_rows(); ps=program_rows(); gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).all()
 if not gaps: return 'No skill-gap records are available yet. Add employer demand and trainee supply records to generate a recommendation.'
 top=gaps[0]
 if not ds or not ps: return 'There is not enough outcome data yet to generate a policy recommendation.'
 if 'lowest retention' in q or 'retention' in q:
  district=min(ds,key=lambda row:row['r6'])
  return f'{district["name"]}, {next((d.state for d in District.query.filter_by(name=district["name"]).all()), "India")}, has the lowest measured six-month retention at {district["r6"]}%. Prioritize follow-up and employer retention support there.'
 if any(x in q for x in ['gap','skill']): return f'{top.skill.name} has the largest supply-demand gap: {top.demand}% employer demand versus {top.supply}% trainee supply. {top.recommendation}'
 if 'state' in q and 'lowest employment' in q: return f'{ds[0]["name"]}, {District.query.filter_by(name=ds[0]["name"]).first().state}, has the lowest measured employment rate at {ds[0]["employment_rate"]}%.'
 if 'city' in q and 'highest placement' in q: return f'{max(ds,key=lambda row:row["placement_rate"])["name"]} has the highest measured placement rate at {max(ds,key=lambda row:row["placement_rate"])["placement_rate"]}%.'
 if 'district' in q or 'attention' in q: return f'{ds[0]["name"]} needs attention, with {ds[0]["employment_rate"]}% employment and {ds[0]["r6"]}% six-month retention.'
 if 'wage' in q: return f'{max(ps,key=lambda x:x["wage_growth"])["name"]} has the strongest measured wage growth at ₹{max(ps,key=lambda x:x["wage_growth"])["wage_growth"]:,}.'
 if 'program' in q or 'best' in q: return f'{ps[0]["name"]} is currently the strongest placement performer at {ps[0]["placement_rate"]}% placement, with {ps[0]["r6"]}% six-month retention.'
 if 'not getting placed' in q: return 'The most common recorded barriers are interview readiness, location mismatch and insufficient practical experience. Prioritize employer-linked practice and local placement support.'
 return f'Prioritize {top.skill.name}: it is the largest measured gap. Pair curriculum capacity with employer-linked placement support in {ds[0]["name"]}.'
def assistant_answer(question, context=None):
 """Local intent router: responses are calculated from the live SQLAlchemy records."""
 q=' '.join(''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in question.lower()).split())
 context=context if context is not None else {}; national=metrics(); states=state_rows(); cities=district_rows(); programs=program_rows(); providers=provider_rows(); gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).all()
 if not Trainee.query.count(): return "I don't have enough recorded data to answer that yet. Try asking about skill gaps once outcome records are available."
 def show(row, label): return f"{label}: {row['name']} — employment {row['employment_rate']}%, placement {row['placement_rate']}%, 6-month retention {row['r6']}%."
 def named(rows):
  return next((r for r in rows if r['name'].lower() in q or r['name'].lower().replace('&','and') in q),None)
 # Resolve short follow-ups using the previous state/city/program row stored in the session.
 if len(q.split())<=5 and any(x in q for x in ('placement','retention','employment')) and context.get('row'):
  row=context['row']; key='placement_rate' if 'placement' in q else ('r6' if 'retention' in q else 'employment_rate')
  return f"For {row['name']}, {'six-month retention' if key=='r6' else key.replace('_rate','')} is {row[key]}%."
 if 'compare' in q or 'which is better' in q:
  choices=[r for r in states+cities+programs if r['name'].lower() in q]
  if len(choices)>=2:
   a,b=choices[:2]; lead=a if a['employment_rate']>=b['employment_rate'] else b
   return f"{a['name']}: employment {a['employment_rate']}%, placement {a['placement_rate']}%, retention {a['r6']}%. {b['name']}: employment {b['employment_rate']}%, placement {b['placement_rate']}%, retention {b['r6']}%. {lead['name']} leads on employment."
  return 'Name two recorded states, cities, or programs and I will compare their employment, placement, and retention.'
 if any(x in q for x in ('follow up','followup','overdue')):
  pending=FollowUp.query.filter(FollowUp.status.in_(['Overdue','Due Today','Escalated'])).all()
  return f"{len(pending)} follow-ups need attention."+(f" Priority trainees: {', '.join(f.trainee.name for f in pending[:4])}." if pending else '')
 if any(x in q for x in ('at risk','warning','early intervention','risk')):
  flagged=warnings()
  return f"Based on current rule-based indicators, {len(flagged)} warnings are active."+(f" {flagged[0][0].name}: {flagged[0][1].lower()} — {flagged[0][4]}." if flagged else '')
 if any(x in q for x in ('skill gap','skill gaps','skills in demand','supply lower','skill should','biggest skill','prioritize')):
  if not gaps: return "I don't have enough recorded skill-gap data to answer that yet."
  top=gaps[0]; return f"{top.skill.name} is the highest recorded gap: demand {top.demand}%, supply {top.supply}%, gap {top.demand-top.supply}%. {top.recommendation}"
 if 'provider' in q or 'training provider' in q or 'needs improvement' in q:
  row=providers[-1] if any(x in q for x in ('worst','improvement')) else providers[0]
  return show(row,'Provider performance')+f" Impact score: {row['impact']}/100."
 if 'employer' in q:
  rows=employer_rows(); top=rows[0] if rows else None
  return f"{top['name']} has the most recorded placements ({top['placements']}) and {top['active']} active employment records." if top else "I don't have enough employer placement data to answer that yet."
 if 'wage' in q or 'salary' in q:
  if 'program' in q or 'highest' in q or 'growth' in q:
   row=max(programs,key=lambda r:r['wage_growth']); return f"{row['name']} has the highest measured wage progression at Rs {row['wage_growth']:,}."
  key='start_wage' if 'starting' in q else 'current_wage'; return f"The average {'starting' if key=='start_wage' else 'current'} wage is Rs {national[key]:,} across active employment records."
 if 'program' in q or named(programs):
  row=named(programs) or (programs[-1] if any(x in q for x in ('worst','lowest')) else programs[0]); return show(row,'Program performance')+f" Wage growth: Rs {row['wage_growth']:,}."
 if 'state' in q or named(states):
  row=named(states)
  if not row:
   key='r6' if 'retention' in q else ('placement_rate' if 'placement' in q else 'employment_rate'); row=min(states,key=lambda r:r[key]) if any(x in q for x in ('lowest','worst','attention','needs')) else max(states,key=lambda r:r[key])
  context['row']=row; return show(row,'State performance')
 if 'city' in q or 'district' in q or named(cities):
  row=named(cities)
  if not row:
   key='r6' if 'retention' in q else ('placement_rate' if 'placement' in q else 'employment_rate'); row=min(cities,key=lambda r:r[key]) if any(x in q for x in ('lowest','worst','attention','needs')) else max(cities,key=lambda r:r[key])
  context['row']=row; return show(row,'City performance')
 if any(x in q for x in ('how many','overview','employment rate','placement rate','completion rate','people employed','trainees')):
  return f"National overview: {national['total']} trainees, {national['employed']} employed, {national['completed']} completed. Employment rate {national['employment_rate']}%, placement rate {national['placement_rate']}%, completion rate {rate(national['completed'],national['total'])}%."
 return 'I can help with outcomes, states, cities, programs, providers, employers, skill gaps, wages, retention and follow-ups. Try: Which state has the lowest employment rate?'
@app.route('/policy-assistant',methods=['GET','POST'])
@login_required
def policy_assistant():
 q=request.form.get('question','') if request.method=='POST' else ''; context=session.get('arko_context',{}); answer=assistant_answer(q,context) if q else None
 if q: session['arko_context']=context
 if q: audit('Policy query generated','Policy Intelligence Assistant')
 return render_template('policy_assistant.html',question=q,answer=answer)
@app.post('/api/policy-assistant')
@login_required
def policy_assistant_api():
 data=request.get_json(silent=True) or request.form
 question=(data.get('question') or '').strip()
 if not question or len(question)>500: return jsonify({'error':'Enter a policy question of up to 500 characters.'}),400
 context=session.get('arko_context',{}); answer=assistant_answer(question,context); session['arko_context']=context
 audit('Policy chat query generated','Policy Intelligence Assistant')
 return jsonify({'answer':answer})
@app.route('/reports')
@login_required
def reports():
 audit('Report generated','State Employment Outcomes')
 return render_template('reports.html',m=metrics(),programs=program_rows(),districts=district_rows(),gaps=SkillGap.query.order_by((SkillGap.demand-SkillGap.supply).desc()).all())
@app.route('/audit-logs')
@login_required
def audit_logs(): return render_template('audit_logs.html',logs=AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all())
@app.route('/settings')
@login_required
def settings(): return render_template('settings.html',db_path=app.config['SQLALCHEMY_DATABASE_URI'])
@app.errorhandler(404)
def not_found(e): return render_template('404.html'),404
@app.errorhandler(403)
def forbidden(e): return render_template('404.html',message='You do not have permission to view this record.'),403
@app.errorhandler(500)
def server_error(e): db.session.rollback(); return render_template('500.html'),500

GEO_CITIES = {
 'Andhra Pradesh':['Visakhapatnam','Vijayawada','Tirupati'],'Arunachal Pradesh':['Itanagar','Naharlagun'],'Assam':['Guwahati','Dibrugarh','Silchar'],'Bihar':['Patna','Gaya','Muzaffarpur'],'Chhattisgarh':['Raipur','Bhilai','Bilaspur'],'Goa':['Panaji','Margao'],'Gujarat':['Ahmedabad','Surat','Vadodara','Rajkot'],'Haryana':['Gurugram','Faridabad','Panipat','Hisar'],'Himachal Pradesh':['Shimla','Dharamshala','Solan'],'Jharkhand':['Ranchi','Jamshedpur','Dhanbad'],'Karnataka':['Bengaluru','Mysuru','Mangaluru','Hubballi'],'Kerala':['Thiruvananthapuram','Kochi','Kozhikode','Thrissur'],'Madhya Pradesh':['Bhopal','Indore','Jabalpur','Gwalior'],'Maharashtra':['Mumbai','Pune','Nashik','Nagpur','Thane','Kolhapur'],'Manipur':['Imphal'],'Meghalaya':['Shillong'],'Mizoram':['Aizawl'],'Nagaland':['Kohima','Dimapur'],'Odisha':['Bhubaneswar','Cuttack','Rourkela'],'Punjab':['Ludhiana','Amritsar','Jalandhar','Patiala'],'Rajasthan':['Jaipur','Jodhpur','Udaipur','Kota','Ajmer'],'Sikkim':['Gangtok'],'Tamil Nadu':['Chennai','Coimbatore','Madurai','Salem','Tiruchirappalli'],'Telangana':['Hyderabad','Warangal','Nizamabad'],'Tripura':['Agartala'],'Uttar Pradesh':['Lucknow','Noida','Greater Noida','Kanpur','Varanasi','Agra','Prayagraj','Gorakhpur'],'Uttarakhand':['Dehradun','Haridwar','Haldwani'],'West Bengal':['Kolkata','Siliguri','Durgapur','Asansol'],'Andaman and Nicobar Islands':['Port Blair'],'Chandigarh':['Chandigarh'],'Dadra and Nagar Haveli and Daman and Diu':['Silvassa','Daman'],'Delhi':['New Delhi'],'Jammu and Kashmir':['Srinagar','Jammu'],'Ladakh':['Leh','Kargil'],'Lakshadweep':['Kavaratti'],'Puducherry':['Puducherry','Karaikal']}
def recommendation_for(skill):
 s=skill.lower()
 if any(x in s for x in ('python','sql','data','power bi','excel')): return 'Expand applied analytics training, portfolio projects and employer-linked practical work.'
 if any(x in s for x in ('cyber','cloud')): return 'Increase cybersecurity and cloud labs, certifications and deployment exposure.'
 if any(x in s for x in ('ev','battery')): return 'Expand EV diagnostics, battery systems and high-voltage safety training.'
 if any(x in s for x in ('digital','advertising')): return 'Increase performance marketing, analytics and campaign-based training.'
 if any(x in s for x in ('graphic','design','web')): return 'Increase portfolio-based learning, studio practice and employer review.'
 if any(x in s for x in ('solar','cnc')): return 'Increase practical workshop capacity and industry-linked certification.'
 if any(x in s for x in ('patient','health')): return 'Strengthen practical healthcare support training and employer placement pathways.'
 return 'Pair targeted practical training with employer-linked assessment and placement support.'
def ensure_geography():
 for state,cities in GEO_CITIES.items():
  for city in cities:
   d=District.query.filter_by(name=city).first()
   if not d: db.session.add(District(name=city,state=state))
   elif not d.state: d.state=state
 db.session.commit()
def seed():
 ensure_geography()
 if Trainee.query.count() >= 100:
  for g in SkillGap.query.all(): g.recommendation=recommendation_for(g.skill.name)
  db.session.commit(); return
 random.seed(26135); districts=[District(name=x) for x in ['Mumbai','Pune','Nagpur','Nashik','Thane','Kolhapur','Chhatrapati Sambhajinagar','Nanded','Satara','Solapur']]; db.session.add_all(districts)
 programs=[TrainingProgram(name=x,category='Industry Skills') for x in ['Python & Data Analytics','Web Development','Electric Vehicle Service','Digital Marketing','Graphic Design','Cybersecurity Basics','Healthcare Assistant','Retail Operations','Solar Technician','Advanced Manufacturing']]; db.session.add_all(programs)
 providers=[TrainingProvider(name=x,satisfaction=random.randint(68,94)) for x in ['Maharashtra Digital Skills Institute','Konkan Career Academy','Vidarbha Technical Trust','Pune FutureWorks','Nashik Skills Centre','Sahyadri Learning Hub','Deccan Vocational Institute','Aarambh Foundation','Metro Employability College','Pragati Skills Network']]; db.session.add_all(providers); db.session.flush()
 skills=['Python','SQL','Excel','Power BI','Data Analysis','JavaScript','Communication','EV Diagnostics','Battery Systems','Digital Advertising','Graphic Design','Cyber Safety','Patient Care','Retail Sales','Solar Installation','CNC Operation','Interview Readiness','English','Customer Service','Project Management','Cloud Basics','Web Design']; db.session.add_all([Skill(name=s) for s in skills]); db.session.flush()
 companies=['Deccan Analytics','Tata EV Services','Konkan Retail','Pune Health Partners','Nashik Solar Works','Mumbai Digital Studio','Vidarbha Manufacturing','Sahyadri Cyber Labs','Maratha Logistics','Apex Web Systems','Pragati Motors','Thane Care Network','Kolhapur Engineering','Solapur Commerce','Aurora Media','Rural Energy Partners']; employers=[]
 for i,c in enumerate(companies): employers.append(Employer(company=c+' Pvt. Ltd.',industry=['Technology','Automotive','Retail','Healthcare','Energy','Manufacturing'][i%6],district_id=districts[i%10].id,verification_status=['VERIFIED','UNDER REVIEW','SUBMITTED'][i%3],requested_skills=', '.join(random.sample(skills,4))))
 db.session.add_all(employers); db.session.flush()
 first=['Aarav','Aditi','Vihaan','Ananya','Kabir','Isha','Arjun','Kavya','Rohan','Meera','Aditya','Saanvi','Yash','Nisha','Rahul','Priya']; last=['Kulkarni','Patil','Deshmukh','Joshi','Shinde','Pawar','Jadhav','More','Kale','Chavan','Bhosale','Sawant']; reasons=['Interview readiness','Location mismatch','Family responsibilities','Insufficient practical experience']; attrs=['Career change','Low wage','Relocation','Workplace fit']
 for i in range(140):
  p=programs[i%10]; d=districts[(i*3)%10]; enrolled=date.today()-timedelta(days=random.randint(190,620)); complete=random.random()>.12; cert=complete and random.random()>.1; placed=cert and random.random() < (.78 if i%10 in [0,3,9] else .48 if i%10 in [2,7] else .63); employed=placed and random.random()>.18; status='Employed' if employed else ('Unemployed' if not placed else 'Unemployed'); t=Trainee(trainee_code=f'KS-MH-2026-{4821+i:06d}',name=f'{first[i%len(first)]} {last[(i*5)%len(last)]}',district_id=d.id,program_id=p.id,provider_id=providers[i%10].id,enrolled_date=enrolled,completion_date=enrolled+timedelta(days=90) if complete else None,certified=cert,placement_date=enrolled+timedelta(days=random.randint(105,160)) if placed else None,employment_status=status,retention_months=random.choice([0,3,6,12,12,6]) if employed else 0,nonplacement_reason=None if placed else random.choice(reasons),attrition_reason=random.choice(attrs) if placed and not employed else None,skills=', '.join(random.sample(skills,5))); db.session.add(t); db.session.flush()
  for s in random.sample(skills,4): db.session.add(Assessment(trainee_id=t.id,skill=s,score=random.randint(42,94)))
  if placed:
   e=EmploymentRecord(trainee_id=t.id,employer_id=employers[i%len(employers)].id,role=['Junior Analyst','Service Technician','Marketing Associate','Healthcare Assistant','Solar Technician','Retail Executive'][i%6],start_date=t.placement_date,end_date=None if employed else t.placement_date+timedelta(days=90),starting_salary=random.randint(15000,26000),current_salary=random.randint(19000,34000) if employed else random.randint(15000,23000),verified=i%3!=0); db.session.add(e); db.session.flush(); db.session.add_all([WageRecord(employment_id=e.id,recorded_date=e.start_date,amount=e.starting_salary),WageRecord(employment_id=e.id,recorded_date=date.today(),amount=e.current_salary)])
  db.session.add(FollowUp(trainee_id=t.id,followup_type=random.choice(['3 Month','6 Month','12 Month']),due_date=date.today()+timedelta(days=random.randint(-25,20)),status=random.choice(['Completed','Completed','Overdue','Due Today','Escalated']),channel=random.choice(['Phone','Email','In-person']),response=status if random.random()>.3 else 'Unable to Reach',notes='Synthetic demonstration follow-up.'))
  for purpose in ['Employment outcome tracking','Employer verification','Wage progression','Research analytics']: db.session.add(Consent(trainee_id=t.id,purpose=purpose,status=random.choices(['Consented','Pending','Withdrawn'],[.75,.18,.07])[0]))
 for idx,s in enumerate(Skill.query.all()):
  demand=random.randint(55,88); supply=random.randint(35,72); db.session.add(SkillGap(skill_id=s.id,demand=demand,supply=supply,recommendation=recommendation_for(s.name)))
 db.session.add(AuditLog(user_name='System',role='System',action='Synthetic demonstration dataset initialized',record='140 trainees')); db.session.commit()
def ensure_demo_users():
 """Keep the six named SIH team accounts consistent even with an existing demo database."""
 legacy={'admin@skillarc.demo','district@skillarc.demo','provider@skillarc.demo','employer@skillarc.demo','trainee@skillarc.demo'}
 for old in User.query.filter(User.email.in_(legacy)).all(): db.session.delete(old)
 district=District.query.order_by(District.id).first()
 for email, name, role in TEAM_ACCOUNTS:
  user=User.query.filter_by(email=email).first()
  if not user:
   user=User(email=email); db.session.add(user)
  user.name=name; user.role=role; user.password_hash=generate_password_hash('Skillarc@2026'); user.district_id=district.id if district else None
 db.session.commit()
def ensure_employee_accounts():
 for t in Trainee.query.filter(Trainee.email.is_(None)).limit(24):
  t.email=f'{t.trainee_code.lower()}@employee.skillarc.local'; t.password_hash=generate_password_hash('Employee@2026'); t.avatar=avatar_gender(t.name)
 db.session.commit()
def migrate_schema():
 """Small SQLite-compatible upgrades for existing installations."""
 with db.engine.connect() as c:
  tables={r[0] for r in c.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")}
  for table, cols in {'user':['first_login_at DATETIME','avatar VARCHAR(20)'], 'district':['state VARCHAR(100)'], 'trainee':['email VARCHAR(120)','password_hash VARCHAR(255)','first_login_at DATETIME','avatar VARCHAR(20)']}.items():
   if table in tables:
    existing={r[1] for r in c.exec_driver_sql(f'PRAGMA table_info("{table}")')}
    for col in cols:
     if col.split()[0] not in existing: c.exec_driver_sql(f'ALTER TABLE "{table}" ADD COLUMN {col}')
  c.commit()
if __name__=='__main__':
 with app.app_context(): db.create_all(); migrate_schema(); seed(); ensure_demo_users(); ensure_employee_accounts()
 app.run(debug=True)
 
