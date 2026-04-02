# Coach-Client Reassignment Detection & Handling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack app that syncs coaching data from a simulated Salesforce source, detects assignment changes, maintains an audit trail, enforces role-based access control, and generates AI transition briefs.

**Architecture:** Django backend with DRF serving a React (Vite) frontend. Two separate SQLite databases — one simulating Salesforce (read-only from app's perspective), one for the application. Django's multi-database support with a custom router keeps them isolated. Gemini API for AI-generated transition briefs.

**Tech Stack:** Python 3.13, Django 5.x, Django REST Framework, React 18 (Vite), SQLite x2, Google Gemini API, TypeScript, CSS Modules

---

## File Structure

```
Coach-Client/├── backend/│   ├── config/                     # Django project config│   │   ├── __init__.py│   │   ├── settings.py             # Dual-DB config, installed apps, DRF settings│   │   ├── urls.py                 # Root URL routing│   │   ├── wsgi.py│   │   └── db_router.py            # Routes salesforce_sim to its own DB│   ├── salesforce_sim/             # Simulated Salesforce source (separate DB)│   │   ├── __init__.py│   │   ├── models.py               # SFCoach, SFAccount, SFContact, SFAssignment│   │   ├── serializers.py│   │   ├── views.py                # Admin CRUD endpoints for source data│   │   ├── urls.py│   │   └── management/│   │       └── commands/│   │           └── seed_salesforce.py  # Populates test data│   ├── coaching/                   # App's local mirror of coaching data│   │   ├── __init__.py│   │   ├── models.py               # Coach, Account, Contact, Assignment│   │   ├── serializers.py│   │   ├── views.py                # Scoped API endpoints│   │   ├── urls.py│   │   └── permissions.py          # IsCoachOrAdmin, ownership checks│   ├── sync/                       # Sync engine + change detection + audit│   │   ├── __init__.py│   │   ├── models.py               # SyncLog, AuditRecord│   │   ├── engine.py               # Pull source → diff → update local → audit│   │   ├── detector.py             # Compares snapshots, returns list of changes│   │   ├── serializers.py│   │   ├── views.py                # Trigger sync, sync history, audit trail│   │   └── urls.py│   ├── briefs/                     # AI transition briefs│   │   ├── __init__.py│   │   ├── models.py               # TransitionBrief│   │   ├── generator.py            # Gemini API call, prompt construction│   │   ├── serializers.py│   │   ├── views.py│   │   └── urls.py│   ├── users/                      # Auth + user roles│   │   ├── __init__.py│   │   ├── models.py               # CustomUser (role: coach/admin, linked Coach)│   │   ├── serializers.py│   │   ├── views.py                # Login, me, register│   │   └── urls.py│   ├── manage.py│   └── requirements.txt├── frontend/│   ├── src/│   │   ├── api/│   │   │   └── client.ts            # Axios instance + CSRF interceptor│   │   ├── context/│   │   │   ├── AuthContext.tsx       # Auth state, login/logout, role│   │   │   └── ThemeContext.tsx      # Dark mode toggle│   │   ├── components/│   │   │   ├── ProtectedRoute.tsx│   │   │   ├── CrmLayout.tsx        # Sidebar + Header + Outlet wrapper│   │   │   ├── CrmLayout.module.css│   │   │   ├── CrmSidebar.tsx       # Collapsible sidebar navigation│   │   │   ├── CrmSidebar.module.css│   │   │   ├── DashboardHeader.tsx  # Page header with user info│   │   │   ├── DashboardHeader.module.css│   │   │   ├── StatCard.tsx         # Reusable stat card component│   │   │   ├── StatCard.module.css│   │   │   └── LoadingSpinner.tsx   # Suspense fallback spinner│   │   ├── pages/│   │   │   ├── LoginPage.tsx│   │   │   ├── LoginPage.module.css│   │   │   ├── CoachDashboard.tsx│   │   │   ├── CoachDashboard.module.css│   │   │   ├── AdminDashboard.tsx│   │   │   ├── AdminDashboard.module.css│   │   │   ├── AuditTrailPage.tsx│   │   │   ├── AuditTrailPage.module.css│   │   │   ├── BriefsPage.tsx│   │   │   ├── BriefsPage.module.css│   │   │   ├── SourceEditorPage.tsx  # Admin: edit simulated Salesforce data│   │   │   └── SourceEditorPage.module.css│   │   ├── styles/│   │   │   ├── variables.css        # --pm-* design tokens (colors, spacing, fonts)│   │   │   ├── global.css           # Reset, base styles, dark mode│   │   │   ├── tables.module.css    # Shared table styles│   │   │   ├── forms.module.css     # Shared form/input styles│   │   │   └── pages.module.css     # Shared page layout styles│   │   ├── App.tsx│   │   └── main.tsx│   ├── index.html│   ├── package.json│   ├── vite.config.ts│   └── tsconfig.json├── Docs/│   └── coach-client-reassignment-PRD.md└── CLAUDE.md
```

---

## Task 1: Django Project Scaffolding + Dual Database Config

**Files:**

-   Create: `backend/config/__init__.py`, `backend/config/settings.py`, `backend/config/urls.py`, `backend/config/wsgi.py`
    
-   Create: `backend/config/db_router.py`
    
-   Create: `backend/manage.py`, `backend/requirements.txt`
    
-    **Step 1: Create requirements.txt**
    

```
django>=5.0,<6.0djangorestframework>=3.15,<4.0django-cors-headers>=4.0,<5.0google-generativeai>=0.8,<1.0
```

-    **Step 2: Create virtual environment and install dependencies**

```bash
cd backendpython -m venv venvsource venv/Scripts/activate   # Windows Git Bashpip install -r requirements.txt
```

-    **Step 3: Scaffold Django project**

```bash
django-admin startproject config .
```

This creates `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`, and `manage.py`.

-    **Step 4: Create all Django apps**

```bash
python manage.py startapp salesforce_simpython manage.py startapp coachingpython manage.py startapp syncpython manage.py startapp briefspython manage.py startapp users
```

-    **Step 5: Write the database router**

Create `backend/config/db_router.py`:

```python
class SalesforceRouter:    """Routes salesforce_sim models to the 'salesforce' database."""    SF_APP = "salesforce_sim"    def db_for_read(self, model, **hints):        if model._meta.app_label == self.SF_APP:            return "salesforce"        return "default"    def db_for_write(self, model, **hints):        if model._meta.app_label == self.SF_APP:            return "salesforce"        return "default"    def allow_relation(self, obj1, obj2, **hints):        # Never allow cross-database relations        a1 = obj1._meta.app_label        a2 = obj2._meta.app_label        if a1 == self.SF_APP or a2 == self.SF_APP:            return a1 == a2        return True    def allow_migrate(self, db, app_label, model_name=None, **hints):        if app_label == self.SF_APP:            return db == "salesforce"        return db == "default"
```

-    **Step 6: Configure settings.py for dual databases, installed apps, DRF, CORS**

Update `backend/config/settings.py` — key sections:

```python
INSTALLED_APPS = [    "django.contrib.admin",    "django.contrib.auth",    "django.contrib.contenttypes",    "django.contrib.sessions",    "django.contrib.messages",    "django.contrib.staticfiles",    # Third party    "rest_framework",    "corsheaders",    # Local apps    "users",    "salesforce_sim",    "coaching",    "sync",    "briefs",]DATABASES = {    "default": {        "ENGINE": "django.db.backends.sqlite3",        "NAME": BASE_DIR / "db.sqlite3",    },    "salesforce": {        "ENGINE": "django.db.backends.sqlite3",        "NAME": BASE_DIR / "db_salesforce.sqlite3",    },}DATABASE_ROUTERS = ["config.db_router.SalesforceRouter"]AUTH_USER_MODEL = "users.CustomUser"REST_FRAMEWORK = {    "DEFAULT_AUTHENTICATION_CLASSES": [        "rest_framework.authentication.SessionAuthentication",    ],    "DEFAULT_PERMISSION_CLASSES": [        "rest_framework.permissions.IsAuthenticated",    ],}MIDDLEWARE = [    "django.middleware.security.SecurityMiddleware",    "django.contrib.sessions.middleware.SessionMiddleware",    "corsheaders.middleware.CorsMiddleware",    "django.middleware.common.CommonMiddleware",    "django.middleware.csrf.CsrfViewMiddleware",    "django.contrib.auth.middleware.AuthenticationMiddleware",    "django.contrib.messages.middleware.MessageMiddleware",    "django.middleware.clickjacking.XFrameOptionsMiddleware",]CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]CORS_ALLOW_CREDENTIALS = True
```

-    **Step 7: Configure root urls.py**

```python
from django.contrib import adminfrom django.urls import path, includeurlpatterns = [    path("admin/", admin.site.urls),    path("api/auth/", include("users.urls")),    path("api/salesforce/", include("salesforce_sim.urls")),    path("api/coaching/", include("coaching.urls")),    path("api/sync/", include("sync.urls")),    path("api/briefs/", include("briefs.urls")),]
```

-    **Step 8: Run migrations to verify dual-DB setup works**

```bash
python manage.py migrate --database=defaultpython manage.py migrate --database=salesforce
```

Expected: Both databases created, no errors.

-    **Step 9: Commit**

```bash
git initgit add -Agit commit -m "feat: scaffold Django project with dual SQLite database config"
```

---

## Task 2: Simulated Salesforce Models + Seed Data

**Files:**

-   Modify: `backend/salesforce_sim/models.py`
    
-   Create: `backend/salesforce_sim/management/commands/seed_salesforce.py`
    
-    **Step 1: Write Salesforce simulation models**
    

`backend/salesforce_sim/models.py`:

```python
import uuidfrom django.db import modelsclass SFCoach(models.Model):    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)    name = models.CharField(max_length=200)    email = models.EmailField(unique=True)    active_clients = models.IntegerField(default=0)    is_active = models.BooleanField(default=True)    class Meta:        app_label = "salesforce_sim"        db_table = "sf_coach"    def __str__(self):        return self.nameclass SFAccount(models.Model):    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)    name = models.CharField(max_length=200)    industry = models.CharField(max_length=100)    website = models.URLField(blank=True)    coaching_start_date = models.DateField()    coach = models.ForeignKey(        SFCoach, on_delete=models.SET_NULL, null=True, related_name="accounts"    )    class Meta:        app_label = "salesforce_sim"        db_table = "sf_account"    def __str__(self):        return self.nameclass SFContact(models.Model):    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)    name = models.CharField(max_length=200)    title = models.CharField(max_length=200)    phone = models.CharField(max_length=30, blank=True)    email = models.EmailField()    account = models.ForeignKey(        SFAccount, on_delete=models.CASCADE, related_name="contacts"    )    coach = models.ForeignKey(        SFCoach, on_delete=models.SET_NULL, null=True, related_name="contacts"    )    class Meta:        app_label = "salesforce_sim"        db_table = "sf_contact"    def __str__(self):        return self.nameclass SFAssignment(models.Model):    STATUS_CHOICES = [        ("active", "Active"),        ("inactive", "Inactive"),    ]    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)    coach = models.ForeignKey(        SFCoach, on_delete=models.CASCADE, related_name="assignments"    )    contact = models.ForeignKey(        SFContact, on_delete=models.CASCADE, related_name="assignments"    )    account = models.ForeignKey(        SFAccount, on_delete=models.CASCADE, related_name="assignments"    )    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")    class Meta:        app_label = "salesforce_sim"        db_table = "sf_assignment"        unique_together = ["coach", "contact"]    def __str__(self):        return f"{self.coach.name} -> {self.contact.name} ({self.status})"
```

-    **Step 2: Write the seed command**

Create `backend/salesforce_sim/management/__init__.py` and `backend/salesforce_sim/management/commands/__init__.py` (empty files).

Create `backend/salesforce_sim/management/commands/seed_salesforce.py`:

```python
from datetime import datefrom django.core.management.base import BaseCommandfrom salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignmentclass Command(BaseCommand):    help = "Seed the simulated Salesforce database with test data"    def handle(self, *args, **options):        # Clear existing data        SFAssignment.objects.using("salesforce").all().delete()        SFContact.objects.using("salesforce").all().delete()        SFAccount.objects.using("salesforce").all().delete()        SFCoach.objects.using("salesforce").all().delete()        # 5 Coaches        alice = SFCoach.objects.using("salesforce").create(            name="Alice Johnson", email="alice@coaching.com",            active_clients=8, is_active=True        )        bob = SFCoach.objects.using("salesforce").create(            name="Bob Smith", email="bob@coaching.com",            active_clients=6, is_active=True        )        carol = SFCoach.objects.using("salesforce").create(            name="Carol Williams", email="carol@coaching.com",            active_clients=4, is_active=True        )        dave = SFCoach.objects.using("salesforce").create(            name="Dave Brown", email="dave@coaching.com",            active_clients=2, is_active=True        )        eve = SFCoach.objects.using("salesforce").create(            name="Eve Davis", email="eve@coaching.com",            active_clients=0, is_active=True        )        # 10 Accounts — distributed: Alice=4, Bob=3, Carol=2, Dave=1        accounts_data = [            ("TechCorp", "Technology", "https://techcorp.com", "2024-01-15", alice),            ("HealthPlus", "Healthcare", "https://healthplus.com", "2024-03-01", alice),            ("FinanceHub", "Finance", "https://financehub.com", "2024-06-15", alice),            ("ManuPro", "Manufacturing", "https://manupro.com", "2024-02-20", alice),            ("CloudNine", "Technology", "https://cloudnine.io", "2024-04-10", bob),            ("DataWorks", "Technology", "https://dataworks.com", "2024-05-01", bob),            ("GreenEnergy", "Energy", "https://greenenergy.com", "2024-07-12", bob),            ("RetailMax", "Retail", "https://retailmax.com", "2024-08-05", carol),            ("BuildRight", "Construction", "https://buildright.com", "2024-09-18", carol),            ("AutoDrive", "Automotive", "https://autodrive.com", "2024-10-01", dave),        ]        accounts = {}        for name, industry, website, start, coach in accounts_data:            acc = SFAccount.objects.using("salesforce").create(                name=name, industry=industry, website=website,                coaching_start_date=date.fromisoformat(start), coach=coach            )            accounts[name] = acc        # 20 Contacts — 2 per account        contacts_data = [            ("John Carter", "CEO", "john@techcorp.com", "555-0101", "TechCorp", alice),            ("Sarah Chen", "VP Engineering", "sarah@techcorp.com", "555-0102", "TechCorp", alice),            ("Mike Ross", "Director HR", "mike@healthplus.com", "555-0201", "HealthPlus", alice),            ("Lisa Park", "CTO", "lisa@healthplus.com", "555-0202", "HealthPlus", alice),            ("Tom Walsh", "CFO", "tom@financehub.com", "555-0301", "FinanceHub", alice),            ("Amy Liu", "COO", "amy@financehub.com", "555-0302", "FinanceHub", alice),            ("Dan Patel", "VP Operations", "dan@manupro.com", "555-0401", "ManuPro", alice),            ("Raj Kumar", "Lead Engineer", "raj@manupro.com", "555-0402", "ManuPro", alice),            ("Nina Gomez", "CEO", "nina@cloudnine.io", "555-0501", "CloudNine", bob),            ("Sam Taylor", "CTO", "sam@cloudnine.io", "555-0502", "CloudNine", bob),            ("Priya Sharma", "VP Engineering", "priya@dataworks.com", "555-0601", "DataWorks", bob),            ("Alex Rivera", "Product Manager", "alex@dataworks.com", "555-0602", "DataWorks", bob),            ("Zoe Adams", "Director of Ops", "zoe@greenenergy.com", "555-0701", "GreenEnergy", bob),            ("Chris Lee", "Team Lead", "chris@greenenergy.com", "555-0702", "GreenEnergy", bob),            ("Emma White", "CEO", "emma@retailmax.com", "555-0801", "RetailMax", carol),            ("Liam Scott", "CFO", "liam@retailmax.com", "555-0802", "RetailMax", carol),            ("Olivia Martinez", "VP Sales", "olivia@buildright.com", "555-0901", "BuildRight", carol),            ("Noah Kim", "Director of Projects", "noah@buildright.com", "555-0902", "BuildRight", carol),            ("Ethan Young", "CEO", "ethan@autodrive.com", "555-1001", "AutoDrive", dave),            ("Mia Jackson", "CTO", "mia@autodrive.com", "555-1002", "AutoDrive", dave),        ]        contacts = {}        for name, title, email, phone, acc_name, coach in contacts_data:            contact = SFContact.objects.using("salesforce").create(                name=name, title=title, email=email, phone=phone,                account=accounts[acc_name], coach=coach            )            contacts[name] = contact        # Create assignments for all active coach-contact pairs        for name, contact in contacts.items():            SFAssignment.objects.using("salesforce").create(                coach=contact.coach,                contact=contact,                account=contact.account,                status="active"            )        self.stdout.write(self.style.SUCCESS(            f"Seeded: {SFCoach.objects.using('salesforce').count()} coaches, "            f"{SFAccount.objects.using('salesforce').count()} accounts, "            f"{SFContact.objects.using('salesforce').count()} contacts, "            f"{SFAssignment.objects.using('salesforce').count()} assignments"        ))
```

-    **Step 3: Run migrations and seed**

```bash
python manage.py makemigrations salesforce_simpython manage.py migrate --database=salesforcepython manage.py seed_salesforce
```

Expected: `Seeded: 5 coaches, 10 accounts, 20 contacts, 20 assignments`

-    **Step 4: Commit**

```bash
git add salesforce_sim/ config/git commit -m "feat: add simulated Salesforce models and seed data"
```

---

## Task 3: Salesforce Sim API (Admin CRUD for Source Data)

**Files:**

-   Modify: `backend/salesforce_sim/serializers.py`, `backend/salesforce_sim/views.py`, `backend/salesforce_sim/urls.py`
    
-    **Step 1: Write serializers**
    

`backend/salesforce_sim/serializers.py`:

```python
from rest_framework import serializersfrom .models import SFCoach, SFAccount, SFContact, SFAssignmentclass SFCoachSerializer(serializers.ModelSerializer):    class Meta:        model = SFCoach        fields = ["id", "sf_id", "name", "email", "active_clients", "is_active"]        read_only_fields = ["sf_id"]class SFContactSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True)    account_name = serializers.CharField(source="account.name", read_only=True)    class Meta:        model = SFContact        fields = [            "id", "sf_id", "name", "title", "phone", "email",            "account", "account_name", "coach", "coach_name",        ]        read_only_fields = ["sf_id"]class SFAccountSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True)    contacts = SFContactSerializer(many=True, read_only=True)    class Meta:        model = SFAccount        fields = [            "id", "sf_id", "name", "industry", "website",            "coaching_start_date", "coach", "coach_name", "contacts",        ]        read_only_fields = ["sf_id"]class SFAssignmentSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True)    contact_name = serializers.CharField(source="contact.name", read_only=True)    account_name = serializers.CharField(source="account.name", read_only=True)    class Meta:        model = SFAssignment        fields = [            "id", "sf_id", "coach", "coach_name",            "contact", "contact_name", "account", "account_name", "status",        ]        read_only_fields = ["sf_id"]
```

-    **Step 2: Write views**

`backend/salesforce_sim/views.py`:

```python
from rest_framework import viewsetsfrom rest_framework.decorators import api_viewfrom rest_framework.response import Responsefrom .models import SFCoach, SFAccount, SFContact, SFAssignmentfrom .serializers import (    SFCoachSerializer, SFAccountSerializer,    SFContactSerializer, SFAssignmentSerializer,)class SFCoachViewSet(viewsets.ModelViewSet):    queryset = SFCoach.objects.using("salesforce").all()    serializer_class = SFCoachSerializerclass SFAccountViewSet(viewsets.ModelViewSet):    queryset = SFAccount.objects.using("salesforce").prefetch_related("contacts").all()    serializer_class = SFAccountSerializerclass SFContactViewSet(viewsets.ModelViewSet):    queryset = SFContact.objects.using("salesforce").select_related("coach", "account").all()    serializer_class = SFContactSerializerclass SFAssignmentViewSet(viewsets.ModelViewSet):    queryset = SFAssignment.objects.using("salesforce").select_related(        "coach", "contact", "account"    ).all()    serializer_class = SFAssignmentSerializer@api_view(["POST"])def notify_change(request):    """Endpoint that only says 'something changed'. No details about what."""    # In a real system this would trigger an async sync.    # For now, just return acknowledgement — the admin triggers sync separately.    return Response({"message": "Change detected. Sync recommended."})
```

-    **Step 3: Write URLs**

`backend/salesforce_sim/urls.py`:

```python
from django.urls import path, includefrom rest_framework.routers import DefaultRouterfrom . import viewsrouter = DefaultRouter()router.register(r"coaches", views.SFCoachViewSet)router.register(r"accounts", views.SFAccountViewSet)router.register(r"contacts", views.SFContactViewSet)router.register(r"assignments", views.SFAssignmentViewSet)urlpatterns = [    path("", include(router.urls)),    path("notify/", views.notify_change, name="sf-notify-change"),]
```

-    **Step 4: Test the API manually**

```bash
python manage.py runserver# In another terminal:curl http://localhost:8000/api/salesforce/coaches/ | python -m json.tool
```

Expected: List of 5 coaches in JSON.

-    **Step 5: Commit**

```bash
git add salesforce_sim/git commit -m "feat: add Salesforce simulation CRUD API"
```

---

## Task 4: User Model + Authentication

**Files:**

-   Modify: `backend/users/models.py`, `backend/users/serializers.py`, `backend/users/views.py`
    
-   Create: `backend/users/urls.py`
    
-    **Step 1: Write CustomUser model**
    

`backend/users/models.py`:

```python
from django.contrib.auth.models import AbstractUserfrom django.db import modelsclass CustomUser(AbstractUser):    ROLE_CHOICES = [        ("coach", "Coach"),        ("admin", "Admin"),    ]    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="coach")    # Links to the coaching.Coach model after sync creates it.    # Null for admins or before first sync.    coach_sf_id = models.UUIDField(null=True, blank=True)    def is_admin(self):        return self.role == "admin"    def is_coach(self):        return self.role == "coach"
```

-    **Step 2: Write serializers**

`backend/users/serializers.py`:

```python
from rest_framework import serializersfrom .models import CustomUserclass UserSerializer(serializers.ModelSerializer):    class Meta:        model = CustomUser        fields = ["id", "username", "email", "role", "coach_sf_id"]        read_only_fields = ["id"]class LoginSerializer(serializers.Serializer):    username = serializers.CharField()    password = serializers.CharField(write_only=True)
```

-    **Step 3: Write views**

`backend/users/views.py`:

```python
from django.contrib.auth import authenticate, login, logoutfrom rest_framework import statusfrom rest_framework.decorators import api_view, permission_classesfrom rest_framework.permissions import AllowAny, IsAuthenticatedfrom rest_framework.response import Responsefrom .serializers import LoginSerializer, UserSerializer@api_view(["POST"])@permission_classes([AllowAny])def login_view(request):    serializer = LoginSerializer(data=request.data)    serializer.is_valid(raise_exception=True)    user = authenticate(        request,        username=serializer.validated_data["username"],        password=serializer.validated_data["password"],    )    if user is None:        return Response(            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED        )    login(request, user)    return Response(UserSerializer(user).data)@api_view(["POST"])def logout_view(request):    logout(request)    return Response({"message": "Logged out"})@api_view(["GET"])@permission_classes([IsAuthenticated])def me_view(request):    return Response(UserSerializer(request.user).data)
```

-    **Step 4: Write URLs**

`backend/users/urls.py`:

```python
from django.urls import pathfrom . import viewsurlpatterns = [    path("login/", views.login_view, name="login"),    path("logout/", views.logout_view, name="logout"),    path("me/", views.me_view, name="me"),]
```

-    **Step 5: Create a management command to create test users**

Create `backend/users/management/commands/create_test_users.py`:

```python
from django.core.management.base import BaseCommandfrom users.models import CustomUserfrom salesforce_sim.models import SFCoachclass Command(BaseCommand):    help = "Create test user accounts for each coach + one admin"    def handle(self, *args, **options):        # Admin        if not CustomUser.objects.filter(username="admin").exists():            CustomUser.objects.create_superuser(                username="admin", password="admin123",                email="admin@coaching.com", role="admin"            )            self.stdout.write(self.style.SUCCESS("Created admin user"))        # One user per coach        for coach in SFCoach.objects.using("salesforce").all():            username = coach.name.split()[0].lower()            if not CustomUser.objects.filter(username=username).exists():                CustomUser.objects.create_user(                    username=username,                    password=f"{username}123",                    email=coach.email,                    role="coach",                    coach_sf_id=coach.sf_id,                )                self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
```

-    **Step 6: Run migrations and create users**

```bash
python manage.py makemigrations userspython manage.py migratepython manage.py create_test_users
```

Expected: `Created admin user`, `Created user: alice`, etc.

-    **Step 7: Commit**

```bash
git add users/git commit -m "feat: add user model with coach/admin roles and auth endpoints"
```

---

## Task 5: Application Local Models (Coaching App)

**Files:**

-   Modify: `backend/coaching/models.py`, `backend/coaching/permissions.py`
    
-    **Step 1: Write the local coaching models**
    

`backend/coaching/models.py`:

```python
import uuidfrom django.db import modelsclass Coach(models.Model):    sf_id = models.UUIDField(unique=True)    name = models.CharField(max_length=200)    email = models.EmailField()    active_clients = models.IntegerField(default=0)    is_active = models.BooleanField(default=True)    def __str__(self):        return self.nameclass Account(models.Model):    sf_id = models.UUIDField(unique=True)    name = models.CharField(max_length=200)    industry = models.CharField(max_length=100)    website = models.URLField(blank=True)    coaching_start_date = models.DateField()    coach = models.ForeignKey(        Coach, on_delete=models.SET_NULL, null=True, related_name="accounts"    )    def __str__(self):        return self.nameclass Contact(models.Model):    sf_id = models.UUIDField(unique=True)    name = models.CharField(max_length=200)    title = models.CharField(max_length=200)    phone = models.CharField(max_length=30, blank=True)    email = models.EmailField()    account = models.ForeignKey(        Account, on_delete=models.CASCADE, related_name="contacts"    )    coach = models.ForeignKey(        Coach, on_delete=models.SET_NULL, null=True, related_name="contacts"    )    def __str__(self):        return self.nameclass Assignment(models.Model):    sf_id = models.UUIDField(unique=True)    coach = models.ForeignKey(        Coach, on_delete=models.CASCADE, related_name="assignments"    )    contact = models.ForeignKey(        Contact, on_delete=models.CASCADE, related_name="assignments"    )    account = models.ForeignKey(        Account, on_delete=models.CASCADE, related_name="assignments"    )    status = models.CharField(max_length=20, default="active")    class Meta:        unique_together = ["coach", "contact"]    def __str__(self):        return f"{self.coach.name} -> {self.contact.name}"
```

-    **Step 2: Write permissions**

`backend/coaching/permissions.py`:

```python
from rest_framework.permissions import BasePermissionfrom coaching.models import Coachclass IsAdminUser(BasePermission):    def has_permission(self, request, view):        return request.user.is_authenticated and request.user.is_admin()class IsCoachOrAdmin(BasePermission):    """Coaches see only their own data. Admins see everything."""    def has_permission(self, request, view):        return request.user.is_authenticateddef get_coach_for_user(user):    """Return the Coach object linked to this user, or None for admins."""    if user.is_admin() or not user.coach_sf_id:        return None    try:        return Coach.objects.get(sf_id=user.coach_sf_id)    except Coach.DoesNotExist:        return None
```

-    **Step 3: Run migrations**

```bash
python manage.py makemigrations coachingpython manage.py migrate
```

-    **Step 4: Commit**

```bash
git add coaching/git commit -m "feat: add local coaching models and access control permissions"
```

---

## Task 6: Sync Engine + Change Detection + Audit Trail

This is the core of the project. The sync engine pulls from the simulated Salesforce, the detector compares old vs new, and audit records are created.

**Files:**

-   Modify: `backend/sync/models.py`, `backend/sync/engine.py`, `backend/sync/detector.py`
    
-   Modify: `backend/sync/serializers.py`, `backend/sync/views.py`, `backend/sync/urls.py`
    
-    **Step 1: Write sync/audit models**
    

`backend/sync/models.py`:

```python
from django.db import modelsclass SyncLog(models.Model):    STATUS_CHOICES = [        ("in_progress", "In Progress"),        ("completed", "Completed"),        ("failed", "Failed"),    ]    started_at = models.DateTimeField(auto_now_add=True)    completed_at = models.DateTimeField(null=True, blank=True)    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")    changes_detected = models.IntegerField(default=0)    error_message = models.TextField(blank=True)    class Meta:        ordering = ["-started_at"]    def __str__(self):        return f"Sync #{self.id} - {self.status} ({self.changes_detected} changes)"class AuditRecord(models.Model):    """Immutable audit record. Never update or delete."""    CHANGE_TYPES = [        ("coach_added", "Coach Added"),        ("coach_removed", "Coach Removed"),        ("coach_updated", "Coach Updated"),        ("account_added", "Account Added"),        ("account_removed", "Account Removed"),        ("account_reassigned", "Account Reassigned"),        ("account_updated", "Account Updated"),        ("contact_added", "Contact Added"),        ("contact_removed", "Contact Removed"),        ("contact_reassigned", "Contact Reassigned"),        ("contact_updated", "Contact Updated"),        ("assignment_added", "Assignment Added"),        ("assignment_removed", "Assignment Removed"),        ("assignment_updated", "Assignment Updated"),    ]    sync = models.ForeignKey(SyncLog, on_delete=models.PROTECT, related_name="audit_records")    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)    entity_type = models.CharField(max_length=30)  # coach, account, contact, assignment    entity_sf_id = models.UUIDField()    entity_name = models.CharField(max_length=200)    before_state = models.JSONField(null=True, blank=True)    after_state = models.JSONField(null=True, blank=True)    coach_name = models.CharField(max_length=200, blank=True)    account_name = models.CharField(max_length=200, blank=True)    detected_at = models.DateTimeField(auto_now_add=True)    class Meta:        ordering = ["-detected_at"]        # Prevent deletion at the DB constraint level        managed = True    def __str__(self):        return f"{self.change_type}: {self.entity_name}"
```

-    **Step 2: Write the change detector**

`backend/sync/detector.py`:

```python
"""Compares source (Salesforce) data with local (app) data.Returns a list of change dicts without modifying any data."""def detect_coach_changes(sf_coaches, local_coaches):    """Compare coaches. Returns list of change dicts."""    changes = []    sf_map = {str(c.sf_id): c for c in sf_coaches}    local_map = {str(c.sf_id): c for c in local_coaches}    # Added    for sf_id, sf_coach in sf_map.items():        if sf_id not in local_map:            changes.append({                "change_type": "coach_added",                "entity_type": "coach",                "entity_sf_id": sf_coach.sf_id,                "entity_name": sf_coach.name,                "before_state": None,                "after_state": {                    "name": sf_coach.name,                    "email": sf_coach.email,                    "is_active": sf_coach.is_active,                },                "coach_name": sf_coach.name,            })    # Removed    for sf_id, local_coach in local_map.items():        if sf_id not in sf_map:            changes.append({                "change_type": "coach_removed",                "entity_type": "coach",                "entity_sf_id": local_coach.sf_id,                "entity_name": local_coach.name,                "before_state": {                    "name": local_coach.name,                    "email": local_coach.email,                    "is_active": local_coach.is_active,                },                "after_state": None,                "coach_name": local_coach.name,            })    # Updated    for sf_id in sf_map:        if sf_id in local_map:            sf_c = sf_map[sf_id]            local_c = local_map[sf_id]            before = {}            after = {}            for field in ["name", "email", "active_clients", "is_active"]:                sf_val = getattr(sf_c, field)                local_val = getattr(local_c, field)                if sf_val != local_val:                    before[field] = local_val                    after[field] = sf_val            if before:                changes.append({                    "change_type": "coach_updated",                    "entity_type": "coach",                    "entity_sf_id": sf_c.sf_id,                    "entity_name": sf_c.name,                    "before_state": before,                    "after_state": after,                    "coach_name": sf_c.name,                })    return changesdef detect_account_changes(sf_accounts, local_accounts, sf_coaches_map, local_coaches_map):    """Compare accounts. Detects add/remove/reassign/update."""    changes = []    sf_map = {str(a.sf_id): a for a in sf_accounts}    local_map = {str(a.sf_id): a for a in local_accounts}    for sf_id, sf_acc in sf_map.items():        if sf_id not in local_map:            coach_name = sf_coaches_map.get(str(sf_acc.coach_id), "Unknown") if sf_acc.coach_id else "Unassigned"            changes.append({                "change_type": "account_added",                "entity_type": "account",                "entity_sf_id": sf_acc.sf_id,                "entity_name": sf_acc.name,                "before_state": None,                "after_state": {                    "name": sf_acc.name,                    "industry": sf_acc.industry,                    "coach": coach_name,                },                "coach_name": coach_name,                "account_name": sf_acc.name,            })        else:            local_acc = local_map[sf_id]            # Check reassignment            sf_coach_sfid = _get_coach_sf_id(sf_acc, sf_coaches_map)            local_coach_sfid = _get_coach_sf_id_local(local_acc, local_coaches_map)            if sf_coach_sfid != local_coach_sfid:                old_coach = local_coaches_map.get(local_coach_sfid, "Unassigned")                new_coach = sf_coaches_map.get(sf_coach_sfid, "Unassigned")                changes.append({                    "change_type": "account_reassigned",                    "entity_type": "account",                    "entity_sf_id": sf_acc.sf_id,                    "entity_name": sf_acc.name,                    "before_state": {"coach": old_coach},                    "after_state": {"coach": new_coach},                    "coach_name": new_coach,                    "account_name": sf_acc.name,                })            # Check other field updates            before = {}            after = {}            for field in ["name", "industry", "website"]:                sf_val = getattr(sf_acc, field)                local_val = getattr(local_acc, field)                if sf_val != local_val:                    before[field] = local_val                    after[field] = sf_val            if before:                changes.append({                    "change_type": "account_updated",                    "entity_type": "account",                    "entity_sf_id": sf_acc.sf_id,                    "entity_name": sf_acc.name,                    "before_state": before,                    "after_state": after,                    "account_name": sf_acc.name,                })    for sf_id, local_acc in local_map.items():        if sf_id not in sf_map:            old_coach = local_coaches_map.get(                _get_coach_sf_id_local(local_acc, local_coaches_map), "Unknown"            )            changes.append({                "change_type": "account_removed",                "entity_type": "account",                "entity_sf_id": local_acc.sf_id,                "entity_name": local_acc.name,                "before_state": {                    "name": local_acc.name,                    "coach": old_coach,                },                "after_state": None,                "coach_name": old_coach,                "account_name": local_acc.name,            })    return changesdef detect_contact_changes(sf_contacts, local_contacts, sf_coaches_map, local_coaches_map):    """Compare contacts. Detects add/remove/reassign/update."""    changes = []    sf_map = {str(c.sf_id): c for c in sf_contacts}    local_map = {str(c.sf_id): c for c in local_contacts}    for sf_id, sf_con in sf_map.items():        if sf_id not in local_map:            coach_name = sf_coaches_map.get(str(sf_con.coach_id), "Unknown") if sf_con.coach_id else "Unassigned"            changes.append({                "change_type": "contact_added",                "entity_type": "contact",                "entity_sf_id": sf_con.sf_id,                "entity_name": sf_con.name,                "before_state": None,                "after_state": {                    "name": sf_con.name,                    "title": sf_con.title,                    "coach": coach_name,                },                "coach_name": coach_name,            })        else:            local_con = local_map[sf_id]            sf_coach_sfid = _get_coach_sf_id(sf_con, sf_coaches_map)            local_coach_sfid = _get_coach_sf_id_local(local_con, local_coaches_map)            if sf_coach_sfid != local_coach_sfid:                old_coach = local_coaches_map.get(local_coach_sfid, "Unassigned")                new_coach = sf_coaches_map.get(sf_coach_sfid, "Unassigned")                changes.append({                    "change_type": "contact_reassigned",                    "entity_type": "contact",                    "entity_sf_id": sf_con.sf_id,                    "entity_name": sf_con.name,                    "before_state": {"coach": old_coach},                    "after_state": {"coach": new_coach},                    "coach_name": new_coach,                })            before = {}            after = {}            for field in ["name", "title", "phone", "email"]:                sf_val = getattr(sf_con, field)                local_val = getattr(local_con, field)                if sf_val != local_val:                    before[field] = local_val                    after[field] = sf_val            if before:                changes.append({                    "change_type": "contact_updated",                    "entity_type": "contact",                    "entity_sf_id": sf_con.sf_id,                    "entity_name": sf_con.name,                    "before_state": before,                    "after_state": after,                })    for sf_id, local_con in local_map.items():        if sf_id not in sf_map:            old_coach = local_coaches_map.get(                _get_coach_sf_id_local(local_con, local_coaches_map), "Unknown"            )            changes.append({                "change_type": "contact_removed",                "entity_type": "contact",                "entity_sf_id": local_con.sf_id,                "entity_name": local_con.name,                "before_state": {                    "name": local_con.name,                    "title": local_con.title,                    "coach": old_coach,                },                "after_state": None,                "coach_name": old_coach,            })    return changesdef detect_assignment_changes(sf_assignments, local_assignments, sf_coaches_map, local_coaches_map):    """Compare assignments."""    changes = []    sf_map = {str(a.sf_id): a for a in sf_assignments}    local_map = {str(a.sf_id): a for a in local_assignments}    for sf_id, sf_asgn in sf_map.items():        if sf_id not in local_map:            coach_name = sf_coaches_map.get(str(sf_asgn.coach_id), "Unknown")            changes.append({                "change_type": "assignment_added",                "entity_type": "assignment",                "entity_sf_id": sf_asgn.sf_id,                "entity_name": f"{coach_name} -> Contact#{sf_asgn.contact_id}",                "before_state": None,                "after_state": {"status": sf_asgn.status, "coach": coach_name},                "coach_name": coach_name,            })        else:            local_asgn = local_map[sf_id]            if sf_asgn.status != local_asgn.status:                changes.append({                    "change_type": "assignment_updated",                    "entity_type": "assignment",                    "entity_sf_id": sf_asgn.sf_id,                    "entity_name": f"Assignment {sf_asgn.sf_id}",                    "before_state": {"status": local_asgn.status},                    "after_state": {"status": sf_asgn.status},                })    for sf_id, local_asgn in local_map.items():        if sf_id not in sf_map:            changes.append({                "change_type": "assignment_removed",                "entity_type": "assignment",                "entity_sf_id": local_asgn.sf_id,                "entity_name": f"Assignment {local_asgn.sf_id}",                "before_state": {"status": local_asgn.status},                "after_state": None,            })    return changes# --- Helpers ---def _get_coach_sf_id(sf_obj, sf_coaches_map):    """Get the sf_id of the coach linked to a source object (via FK id)."""    if sf_obj.coach_id is None:        return None    return str(sf_obj.coach_id)def _get_coach_sf_id_local(local_obj, local_coaches_map):    """Get the sf_id string of the coach linked to a local object."""    if local_obj.coach_id is None:        return None    return str(local_obj.coach_id)
```

**Important note on the helpers:** The SF models use Django PK (`id`) as FK, but we match on `sf_id`. The engine (next step) will build lookup maps that translate between PKs and `sf_id` values correctly.

-    **Step 3: Write the sync engine**

`backend/sync/engine.py`:

```python
"""Sync engine: pulls all data from simulated Salesforce,runs change detection, updates local DB, creates audit records."""import loggingfrom django.utils import timezonefrom salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignmentfrom coaching.models import Coach, Account, Contact, Assignmentfrom .models import SyncLog, AuditRecordfrom . import detectorlogger = logging.getLogger(__name__)def run_sync():    """Execute a full sync. Returns the SyncLog instance."""    sync_log = SyncLog.objects.create(status="in_progress")    try:        # 1. Pull all source data        sf_coaches = list(SFCoach.objects.using("salesforce").all())        sf_accounts = list(SFAccount.objects.using("salesforce").select_related("coach").all())        sf_contacts = list(SFContact.objects.using("salesforce").select_related("coach", "account").all())        sf_assignments = list(SFAssignment.objects.using("salesforce").select_related("coach", "contact", "account").all())        # 2. Pull all local data        local_coaches = list(Coach.objects.all())        local_accounts = list(Account.objects.select_related("coach").all())        local_contacts = list(Contact.objects.select_related("coach", "account").all())        local_assignments = list(Assignment.objects.select_related("coach", "contact", "account").all())        # 3. Build lookup maps: SF PK id -> coach name (for source)        sf_coach_pk_to_name = {str(c.id): c.name for c in sf_coaches}        sf_coach_pk_to_sfid = {str(c.id): str(c.sf_id) for c in sf_coaches}        # Local: coach PK id -> coach name        local_coach_pk_to_name = {str(c.id): c.name for c in local_coaches}        local_coach_pk_to_sfid = {str(c.id): str(c.sf_id) for c in local_coaches}        # 4. Detect changes        all_changes = []        all_changes.extend(detector.detect_coach_changes(sf_coaches, local_coaches))        all_changes.extend(detector.detect_account_changes(            sf_accounts, local_accounts, sf_coach_pk_to_name, local_coach_pk_to_name        ))        all_changes.extend(detector.detect_contact_changes(            sf_contacts, local_contacts, sf_coach_pk_to_name, local_coach_pk_to_name        ))        all_changes.extend(detector.detect_assignment_changes(            sf_assignments, local_assignments, sf_coach_pk_to_name, local_coach_pk_to_name        ))        # 5. Create audit records        for change in all_changes:            AuditRecord.objects.create(sync=sync_log, **change)        # 6. Collect reassignment info BEFORE updating local data        reassignments = _collect_reassignments(all_changes, sf_contacts, sf_accounts, sf_coaches)        # 7. Update local database to match source        _sync_coaches(sf_coaches)        _sync_accounts(sf_accounts, sf_coaches)        _sync_contacts(sf_contacts, sf_coaches, sf_accounts)        _sync_assignments(sf_assignments, sf_coaches, sf_contacts, sf_accounts)        # 8. Finalize        sync_log.status = "completed"        sync_log.changes_detected = len(all_changes)        sync_log.completed_at = timezone.now()        sync_log.save()        # 9. Generate transition briefs (non-blocking)        if reassignments:            _generate_briefs(reassignments, sync_log)        return sync_log    except Exception as e:        logger.exception("Sync failed")        sync_log.status = "failed"        sync_log.error_message = str(e)        sync_log.completed_at = timezone.now()        sync_log.save()        return sync_logdef _sync_coaches(sf_coaches):    sf_ids = set()    for sf_c in sf_coaches:        sf_ids.add(str(sf_c.sf_id))        Coach.objects.update_or_create(            sf_id=sf_c.sf_id,            defaults={                "name": sf_c.name,                "email": sf_c.email,                "active_clients": sf_c.active_clients,                "is_active": sf_c.is_active,            },        )    # Remove coaches no longer in source    Coach.objects.exclude(sf_id__in=[c.sf_id for c in sf_coaches]).delete()def _sync_accounts(sf_accounts, sf_coaches):    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}  # SF PK -> sf_id    for sf_a in sf_accounts:        coach = None        if sf_a.coach_id:            coach_sf_id = sf_coach_map.get(sf_a.coach_id)            if coach_sf_id:                coach = Coach.objects.filter(sf_id=coach_sf_id).first()        Account.objects.update_or_create(            sf_id=sf_a.sf_id,            defaults={                "name": sf_a.name,                "industry": sf_a.industry,                "website": sf_a.website,                "coaching_start_date": sf_a.coaching_start_date,                "coach": coach,            },        )    Account.objects.exclude(sf_id__in=[a.sf_id for a in sf_accounts]).delete()def _sync_contacts(sf_contacts, sf_coaches, sf_accounts):    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}    sf_account_map = {a.id: a.sf_id for a in sf_accounts}    for sf_con in sf_contacts:        coach = None        if sf_con.coach_id:            coach_sf_id = sf_coach_map.get(sf_con.coach_id)            if coach_sf_id:                coach = Coach.objects.filter(sf_id=coach_sf_id).first()        account = None        if sf_con.account_id:            account_sf_id = sf_account_map.get(sf_con.account_id)            if account_sf_id:                account = Account.objects.filter(sf_id=account_sf_id).first()        Contact.objects.update_or_create(            sf_id=sf_con.sf_id,            defaults={                "name": sf_con.name,                "title": sf_con.title,                "phone": sf_con.phone,                "email": sf_con.email,                "account": account,                "coach": coach,            },        )    Contact.objects.exclude(sf_id__in=[c.sf_id for c in sf_contacts]).delete()def _sync_assignments(sf_assignments, sf_coaches, sf_contacts, sf_accounts):    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}    sf_contact_map = {c.id: c.sf_id for c in sf_contacts}    sf_account_map = {a.id: a.sf_id for a in sf_accounts}    for sf_a in sf_assignments:        coach = Coach.objects.filter(sf_id=sf_coach_map.get(sf_a.coach_id)).first()        contact = Contact.objects.filter(sf_id=sf_contact_map.get(sf_a.contact_id)).first()        account = Account.objects.filter(sf_id=sf_account_map.get(sf_a.account_id)).first()        if coach and contact and account:            Assignment.objects.update_or_create(                sf_id=sf_a.sf_id,                defaults={                    "coach": coach,                    "contact": contact,                    "account": account,                    "status": sf_a.status,                },            )    Assignment.objects.exclude(sf_id__in=[a.sf_id for a in sf_assignments]).delete()def _collect_reassignments(changes, sf_contacts, sf_accounts, sf_coaches):    """Identify contact reassignments for brief generation."""    reassignments = []    sf_coach_map = {c.id: c for c in sf_coaches}    sf_account_map = {a.id: a for a in sf_accounts}    for change in changes:        if change["change_type"] == "contact_reassigned":            sf_id = change["entity_sf_id"]            sf_contact = next((c for c in sf_contacts if str(c.sf_id) == str(sf_id)), None)            if sf_contact:                new_coach = sf_coach_map.get(sf_contact.coach_id)                account = sf_account_map.get(sf_contact.account_id)                reassignments.append({                    "contact_name": sf_contact.name,                    "contact_title": sf_contact.title,                    "contact_email": sf_contact.email,                    "contact_sf_id": str(sf_contact.sf_id),                    "account_name": account.name if account else "Unknown",                    "account_industry": account.industry if account else "Unknown",                    "account_start_date": str(account.coaching_start_date) if account else "Unknown",                    "previous_coach": change["before_state"].get("coach", "Unknown"),                    "new_coach": new_coach.name if new_coach else "Unknown",                    "new_coach_sf_id": str(new_coach.sf_id) if new_coach else None,                })    return reassignmentsdef _generate_briefs(reassignments, sync_log):    """Generate transition briefs. Failures are logged, not raised."""    from briefs.generator import generate_transition_brief    from briefs.models import TransitionBrief    from coaching.models import Coach    for r in reassignments:        try:            content = generate_transition_brief(r)            coach = Coach.objects.filter(sf_id=r["new_coach_sf_id"]).first() if r["new_coach_sf_id"] else None            audit_record = AuditRecord.objects.filter(                sync=sync_log,                entity_sf_id=r["contact_sf_id"],                change_type="contact_reassigned",            ).first()            TransitionBrief.objects.create(                sync=sync_log,                audit_record=audit_record,                coach=coach,                contact_name=r["contact_name"],                account_name=r["account_name"],                previous_coach_name=r["previous_coach"],                content=content,            )        except Exception as e:            logger.error(f"Failed to generate brief for {r['contact_name']}: {e}")
```

-    **Step 4: Write sync serializers**

`backend/sync/serializers.py`:

```python
from rest_framework import serializersfrom .models import SyncLog, AuditRecordclass AuditRecordSerializer(serializers.ModelSerializer):    class Meta:        model = AuditRecord        fields = [            "id", "sync_id", "change_type", "entity_type", "entity_sf_id",            "entity_name", "before_state", "after_state",            "coach_name", "account_name", "detected_at",        ]class SyncLogSerializer(serializers.ModelSerializer):    audit_records = AuditRecordSerializer(many=True, read_only=True)    class Meta:        model = SyncLog        fields = [            "id", "started_at", "completed_at", "status",            "changes_detected", "error_message", "audit_records",        ]class SyncLogListSerializer(serializers.ModelSerializer):    """Lighter serializer for list views (no nested audit records)."""    class Meta:        model = SyncLog        fields = [            "id", "started_at", "completed_at", "status",            "changes_detected", "error_message",        ]
```

-    **Step 5: Write sync views**

`backend/sync/views.py`:

```python
from rest_framework import statusfrom rest_framework.decorators import api_viewfrom rest_framework.response import Responsefrom coaching.permissions import IsAdminUserfrom .models import SyncLog, AuditRecordfrom .serializers import SyncLogSerializer, SyncLogListSerializer, AuditRecordSerializerfrom .engine import run_sync@api_view(["POST"])def trigger_sync(request):    """Admin triggers a full sync."""    if not request.user.is_admin():        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)    sync_log = run_sync()    serializer = SyncLogSerializer(sync_log)    return Response(serializer.data, status=status.HTTP_201_CREATED)@api_view(["GET"])def sync_history(request):    """List all sync runs. Admin only."""    if not request.user.is_admin():        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)    syncs = SyncLog.objects.all()    serializer = SyncLogListSerializer(syncs, many=True)    return Response(serializer.data)@api_view(["GET"])def sync_detail(request, sync_id):    """Get a single sync with its audit records."""    if not request.user.is_admin():        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)    try:        sync_log = SyncLog.objects.get(id=sync_id)    except SyncLog.DoesNotExist:        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)    serializer = SyncLogSerializer(sync_log)    return Response(serializer.data)@api_view(["GET"])def audit_trail(request):    """Filterable audit trail. Admin only."""    if not request.user.is_admin():        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)    records = AuditRecord.objects.all()    # Filters    change_type = request.query_params.get("change_type")    if change_type:        records = records.filter(change_type=change_type)    coach_name = request.query_params.get("coach")    if coach_name:        records = records.filter(coach_name__icontains=coach_name)    account_name = request.query_params.get("account")    if account_name:        records = records.filter(account_name__icontains=account_name)    date_from = request.query_params.get("date_from")    if date_from:        records = records.filter(detected_at__date__gte=date_from)    date_to = request.query_params.get("date_to")    if date_to:        records = records.filter(detected_at__date__lte=date_to)    serializer = AuditRecordSerializer(records, many=True)    return Response(serializer.data)
```

-    **Step 6: Write sync URLs**

`backend/sync/urls.py`:

```python
from django.urls import pathfrom . import viewsurlpatterns = [    path("trigger/", views.trigger_sync, name="trigger-sync"),    path("history/", views.sync_history, name="sync-history"),    path("history/<int:sync_id>/", views.sync_detail, name="sync-detail"),    path("audit/", views.audit_trail, name="audit-trail"),]
```

-    **Step 7: Run migrations and test sync**

```bash
python manage.py makemigrations syncpython manage.py migratepython manage.py runserver
```

Test: Login as admin, POST to `/api/sync/trigger/`. First sync should detect all coaches/accounts/contacts/assignments as "added". Second sync should detect 0 changes.

-    **Step 8: Commit**

```bash
git add sync/git commit -m "feat: add sync engine with change detection and audit trail"
```

---

## Task 7: Coaching API with Access Control

**Files:**

-   Modify: `backend/coaching/serializers.py`, `backend/coaching/views.py`
    
-   Create: `backend/coaching/urls.py`
    
-    **Step 1: Write serializers**
    

`backend/coaching/serializers.py`:

```python
from rest_framework import serializersfrom .models import Coach, Account, Contact, Assignmentclass ContactSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True)    class Meta:        model = Contact        fields = [            "id", "sf_id", "name", "title", "phone", "email",            "account_id", "coach_id", "coach_name",        ]class AccountSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True)    contacts = ContactSerializer(many=True, read_only=True)    class Meta:        model = Account        fields = [            "id", "sf_id", "name", "industry", "website",            "coaching_start_date", "coach_id", "coach_name", "contacts",        ]class CoachSerializer(serializers.ModelSerializer):    class Meta:        model = Coach        fields = ["id", "sf_id", "name", "email", "active_clients", "is_active"]class DashboardSerializer(serializers.Serializer):    """Coach dashboard data."""    coach = CoachSerializer()    accounts = AccountSerializer(many=True)    total_accounts = serializers.IntegerField()    total_clients = serializers.IntegerField()
```

-    **Step 2: Write views with access control**

`backend/coaching/views.py`:

```python
from rest_framework import statusfrom rest_framework.decorators import api_viewfrom rest_framework.response import Responsefrom .models import Coach, Account, Contactfrom .serializers import (    AccountSerializer, ContactSerializer, CoachSerializer, DashboardSerializer,)from .permissions import get_coach_for_user@api_view(["GET"])def dashboard(request):    """Coach sees their data. Admin sees all or a specific coach's data."""    user = request.user    if user.is_admin():        coach_id = request.query_params.get("coach_id")        if coach_id:            coach = Coach.objects.filter(id=coach_id).first()            if not coach:                return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)        else:            # Admin overview: all coaches with their accounts            coaches = Coach.objects.filter(is_active=True)            data = []            for c in coaches:                accounts = Account.objects.filter(coach=c).prefetch_related("contacts")                data.append({                    "coach": CoachSerializer(c).data,                    "accounts": AccountSerializer(accounts, many=True).data,                    "total_accounts": accounts.count(),                    "total_clients": Contact.objects.filter(coach=c).count(),                })            return Response(data)    else:        coach = get_coach_for_user(user)        if not coach:            return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)    accounts = Account.objects.filter(coach=coach).prefetch_related("contacts")    total_clients = Contact.objects.filter(coach=coach).count()    result = {        "coach": CoachSerializer(coach).data,        "accounts": AccountSerializer(accounts, many=True).data,        "total_accounts": accounts.count(),        "total_clients": total_clients,    }    return Response(result)@api_view(["GET"])def accounts_list(request):    """List accounts. Scoped to coach's own accounts."""    coach = get_coach_for_user(request.user)    if coach:        accounts = Account.objects.filter(coach=coach).prefetch_related("contacts")    elif request.user.is_admin():        accounts = Account.objects.all().prefetch_related("contacts")    else:        return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)    return Response(AccountSerializer(accounts, many=True).data)@api_view(["GET"])def account_detail(request, account_id):    """Get single account. Enforced ownership."""    try:        account = Account.objects.prefetch_related("contacts").get(id=account_id)    except Account.DoesNotExist:        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)    coach = get_coach_for_user(request.user)    if coach and account.coach_id != coach.id:        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)    return Response(AccountSerializer(account).data)@api_view(["GET"])def contacts_list(request):    """List contacts. Scoped to coach."""    coach = get_coach_for_user(request.user)    if coach:        contacts = Contact.objects.filter(coach=coach).select_related("coach")    elif request.user.is_admin():        contacts = Contact.objects.all().select_related("coach")    else:        return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)    return Response(ContactSerializer(contacts, many=True).data)@api_view(["GET"])def contact_detail(request, contact_id):    """Get single contact. Enforced ownership."""    try:        contact = Contact.objects.select_related("coach", "account").get(id=contact_id)    except Contact.DoesNotExist:        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)    coach = get_coach_for_user(request.user)    if coach and contact.coach_id != coach.id:        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)    return Response(ContactSerializer(contact).data)
```

-    **Step 3: Write URLs**

`backend/coaching/urls.py`:

```python
from django.urls import pathfrom . import viewsurlpatterns = [    path("dashboard/", views.dashboard, name="dashboard"),    path("accounts/", views.accounts_list, name="accounts-list"),    path("accounts/<int:account_id>/", views.account_detail, name="account-detail"),    path("contacts/", views.contacts_list, name="contacts-list"),    path("contacts/<int:contact_id>/", views.contact_detail, name="contact-detail"),]
```

-    **Step 4: Test access control**

```bash
# Login as alice, try to access bob's data — should get 403# Login as admin — should see everything
```

-    **Step 5: Commit**

```bash
git add coaching/git commit -m "feat: add coaching API with role-based access control"
```

---

## Task 8: AI Transition Briefs (Gemini)

**Files:**

-   Modify: `backend/briefs/models.py`, `backend/briefs/generator.py`
    
-   Modify: `backend/briefs/serializers.py`, `backend/briefs/views.py`
    
-   Create: `backend/briefs/urls.py`
    
-    **Step 1: Write TransitionBrief model**
    

`backend/briefs/models.py`:

```python
from django.db import modelsfrom sync.models import SyncLog, AuditRecordfrom coaching.models import Coachclass TransitionBrief(models.Model):    sync = models.ForeignKey(SyncLog, on_delete=models.PROTECT, related_name="briefs")    audit_record = models.ForeignKey(        AuditRecord, on_delete=models.PROTECT, null=True, related_name="briefs"    )    coach = models.ForeignKey(        Coach, on_delete=models.SET_NULL, null=True, related_name="briefs"    )    contact_name = models.CharField(max_length=200)    account_name = models.CharField(max_length=200)    previous_coach_name = models.CharField(max_length=200)    content = models.TextField()    generated_at = models.DateTimeField(auto_now_add=True)    class Meta:        ordering = ["-generated_at"]    def __str__(self):        return f"Brief: {self.contact_name} → {self.coach.name if self.coach else 'Unknown'}"
```

-    **Step 2: Write the Gemini generator**

`backend/briefs/generator.py`:

```python
import osimport loggingimport google.generativeai as genailogger = logging.getLogger(__name__)def generate_transition_brief(reassignment_data):    """    Call Gemini to generate a transition brief from real data.    Raises on failure — caller handles the exception.    """    api_key = os.environ.get("GEMINI_API_KEY")    if not api_key:        raise ValueError("GEMINI_API_KEY environment variable not set")    genai.configure(api_key=api_key)    model = genai.GenerativeModel("gemini-2.0-flash")    prompt = f"""You are an executive coaching assistant. Generate a transition brief for a coachwho is being assigned a new client. Use ONLY the data provided below — do not invent any facts.CLIENT INFORMATION:- Name: {reassignment_data['contact_name']}- Title: {reassignment_data['contact_title']}- Email: {reassignment_data['contact_email']}ACCOUNT INFORMATION:- Company: {reassignment_data['account_name']}- Industry: {reassignment_data['account_industry']}- Coaching relationship started: {reassignment_data['account_start_date']}ASSIGNMENT CHANGE:- Previous Coach: {reassignment_data['previous_coach']}- New Coach (you are writing for): {reassignment_data['new_coach']}Write a brief that includes:1. Client & Account Summary2. Coaching History (based on timeline)3. Key Insights (what the new coach should know)4. Recommended Next Steps (3-5 actionable items)Keep it concise and actionable. Format with clear headers."""    response = model.generate_content(prompt)    return response.text
```

-    **Step 3: Write serializers**

`backend/briefs/serializers.py`:

```python
from rest_framework import serializersfrom .models import TransitionBriefclass TransitionBriefSerializer(serializers.ModelSerializer):    coach_name = serializers.CharField(source="coach.name", read_only=True, default="Unknown")    class Meta:        model = TransitionBrief        fields = [            "id", "sync_id", "coach_id", "coach_name",            "contact_name", "account_name", "previous_coach_name",            "content", "generated_at",        ]
```

-    **Step 4: Write views**

`backend/briefs/views.py`:

```python
from rest_framework.decorators import api_viewfrom rest_framework.response import Responsefrom rest_framework import statusfrom coaching.permissions import get_coach_for_userfrom .models import TransitionBrieffrom .serializers import TransitionBriefSerializer@api_view(["GET"])def briefs_list(request):    """List briefs. Coach sees own, admin sees all."""    coach = get_coach_for_user(request.user)    if coach:        briefs = TransitionBrief.objects.filter(coach=coach)    elif request.user.is_admin():        briefs = TransitionBrief.objects.all()    else:        return Response({"error": "No coach profile"}, status=status.HTTP_404_NOT_FOUND)    return Response(TransitionBriefSerializer(briefs, many=True).data)@api_view(["GET"])def brief_detail(request, brief_id):    """Get single brief. Enforced ownership."""    try:        brief = TransitionBrief.objects.select_related("coach").get(id=brief_id)    except TransitionBrief.DoesNotExist:        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)    coach = get_coach_for_user(request.user)    if coach and (not brief.coach or brief.coach.id != coach.id):        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)    return Response(TransitionBriefSerializer(brief).data)
```

-    **Step 5: Write URLs**

`backend/briefs/urls.py`:

```python
from django.urls import pathfrom . import viewsurlpatterns = [    path("", views.briefs_list, name="briefs-list"),    path("<int:brief_id>/", views.brief_detail, name="brief-detail"),]
```

-    **Step 6: Run migrations**

```bash
python manage.py makemigrations briefspython manage.py migrate
```

-    **Step 7: Commit**

```bash
git add briefs/git commit -m "feat: add AI transition briefs with Gemini integration"
```

---

## Task 9: React Frontend Setup (TypeScript + Vite + CSS Modules)

> **Goal:** Scaffold the Coach-Client frontend SPA using the same patterns proven in PentEdge-CRM -- TypeScript, Vite, CSS Modules with `--pm-*` design tokens, AuthContext with coach/admin roles, ThemeContext for dark mode, axios API client with CSRF handling, and a ProtectedRoute guard.

---

### Prerequisites

-   Node.js >= 18 installed
-   Backend API running on `http://localhost:8000/api` (Tasks 1-8 complete)

---

-    **Step 1: Scaffold the Vite + React + TypeScript project**

```bash
cd frontendnpm create vite@latest . -- --template react-tsnpm install
```

-    **Step 2: Install dependencies**

```bash
npm install axios react-router-dom rechartsnpm install -D @types/react @types/react-dom typescript
```

**File: `frontend/package.json`**

```json
{  "name": "coach-client",  "private": true,  "version": "1.0.0",  "type": "module",  "scripts": {    "dev": "vite",    "build": "tsc -b && vite build",    "preview": "vite preview",    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",    "typecheck": "tsc --noEmit"  },  "dependencies": {    "axios": "^1.13.5",    "react": "^18.3.1",    "react-dom": "^18.3.1",    "react-router-dom": "^6.28.0",    "recharts": "^2.12.7"  },  "devDependencies": {    "@types/react": "^18.3.12",    "@types/react-dom": "^18.3.1",    "@vitejs/plugin-react": "^4.3.4",    "typescript": "~5.6.2",    "vite": "^5.4.11"  }}
```

---

-    **Step 3: Configure Vite with `@/` path alias**

**File: `frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite'import react from '@vitejs/plugin-react'import path from 'path'export default defineConfig({  plugins: [react()],  resolve: {    alias: {      '@': path.resolve(__dirname, './src'),    },  },  server: {    proxy: {      '/api': {        target: 'http://localhost:8000',        changeOrigin: true,      },    },  },  build: {    rollupOptions: {      output: {        manualChunks: {          'vendor-react': ['react', 'react-dom', 'react-router-dom'],          'vendor-charts': ['recharts'],          'vendor-axios': ['axios'],        },      },    },  },})
```

---

-    **Step 4: Configure TypeScript (strict mode, `@/` paths)**

**File: `frontend/tsconfig.json`**

```json
{  "files": [],  "references": [    { "path": "./tsconfig.app.json" }  ]}
```

**File: `frontend/tsconfig.app.json`**

```json
{  "compilerOptions": {    "target": "ES2020",    "useDefineForClassFields": true,    "lib": ["ES2020", "DOM", "DOM.Iterable"],    "module": "ESNext",    "skipLibCheck": true,    "moduleResolution": "bundler",    "allowImportingTsExtensions": true,    "isolatedModules": true,    "moduleDetection": "force",    "noEmit": true,    "jsx": "react-jsx",    "strict": true,    "noUnusedLocals": true,    "noUnusedParameters": true,    "noFallthroughCasesInSwitch": true,    "baseUrl": ".",    "paths": {      "@/*": ["src/*"]    }  },  "include": ["src"]}
```

---

-    **Step 5: Create CSS variables (light + dark mode design tokens)**

All colors throughout the app use `var(--pm-*)` variables. No hardcoded hex values in CSS Modules.

**File: `frontend/src/styles/variables.css`**

```css
:root {  /* Page backgrounds */  --pm-gradient-start: #FBFCFE;  --pm-gradient-mid: #E6EAF4;  --pm-gradient-end: #D7DEEE;  --pm-content-bg: #F3F4F6;  --pm-card-bg: #FFFFFF;  --pm-card-bg-hover: #F9FAFB;  /* Text colors */  --pm-text-primary: #1F2937;  --pm-text-secondary: #4B5563;  --pm-text-muted: #9CA3AF;  --pm-text-grey: #6B7280;  --pm-text-on-accent: #FFFFFF;  /* Accent colors -- Coach-Client uses teal/blue primary */  --pm-accent-primary: #0D9488;  --pm-accent-primary-hover: #0F766E;  --pm-accent-primary-bg: rgba(13, 148, 136, 0.08);  --pm-accent-green: #10B981;  --pm-accent-green-bg: rgba(16, 185, 129, 0.1);  --pm-accent-red: #EF4444;  --pm-accent-red-bg: rgba(239, 68, 68, 0.08);  --pm-accent-orange: #F59E0B;  --pm-accent-orange-bg: rgba(245, 158, 11, 0.1);  --pm-accent-purple: #8B5CF6;  --pm-accent-purple-bg: rgba(139, 92, 246, 0.08);  --pm-accent-blue: #3B82F6;  --pm-accent-blue-bg: rgba(59, 130, 246, 0.1);  /* Sidebar */  --pm-sidebar-bg: #FFFFFF;  --pm-sidebar-border: #E2E8F0;  --pm-sidebar-item-color: #4B5563;  --pm-sidebar-item-hover-bg: #F1F5F9;  --pm-sidebar-item-hover-color: #1F2937;  --pm-sidebar-item-active-bg: rgba(13, 148, 136, 0.08);  --pm-sidebar-item-active-color: #0D9488;  --pm-sidebar-item-active-shadow: 0 1px 6px rgba(13, 148, 136, 0.10);  --pm-sidebar-item-active-border: #0D9488;  --pm-sidebar-icon-filter: none;  --pm-sidebar-icon-opacity: 0.7;  --pm-sidebar-icon-active-opacity: 1;  /* Chart */  --pm-bar-light: #E5E7EB;  --pm-bar-active: #0D9488;  --pm-tooltip-bg: #F9FAFB;  /* Trend badges */  --pm-trend-green-bg: rgba(16, 185, 129, 0.1);  --pm-trend-red-bg: rgba(239, 68, 68, 0.1);  /* Borders */  --pm-border: #DCE0E5;  --pm-border-light: #E5E7EB;  --pm-border-heavy: #D1D5DB;  /* Inputs / Forms */  --pm-input-bg: #FFFFFF;  --pm-input-border: #D1D5DB;  --pm-input-text: #1F2937;  --pm-input-placeholder: #9CA3AF;  --pm-input-focus-border: #0D9488;  --pm-input-focus-ring: rgba(13, 148, 136, 0.15);  /* Tables */  --pm-table-header-bg: #F9FAFB;  --pm-table-header-color: #4B5563;  --pm-table-row-hover: #F3F4F6;  --pm-table-row-selected: #EFF6FF;  --pm-table-border: #E5E7EB;  /* Modals */  --pm-modal-bg: #FFFFFF;  --pm-modal-overlay: rgba(0, 0, 0, 0.5);  --pm-modal-border: #E5E7EB;  /* Buttons */  --pm-btn-secondary-bg: #F3F4F6;  --pm-btn-secondary-color: #374151;  --pm-btn-secondary-border: #D1D5DB;  --pm-btn-secondary-hover-bg: #E5E7EB;  --pm-btn-danger-bg: #FEF2F2;  --pm-btn-danger-color: #EF4444;  --pm-btn-danger-hover-bg: #FEE2E2;  /* Badges / Tags */  --pm-badge-bg: #F3F4F6;  --pm-badge-color: #374151;  --pm-badge-border: #E5E7EB;  /* Dropdown / Popover */  --pm-dropdown-bg: #FFFFFF;  --pm-dropdown-border: #E5E7EB;  --pm-dropdown-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.05);  --pm-dropdown-item-hover: #F3F4F6;  /* Tooltip */  --pm-tooltip-color: #FFFFFF;  --pm-tooltip-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);  /* Avatar */  --pm-avatar-gradient: linear-gradient(135deg, #0D9488, #3B82F6);  --pm-avatar-border: #E5E7EB;  /* Scrollbar */  --pm-scrollbar-thumb: rgba(0, 0, 0, 0.08);  /* Typography */  --font-primary: 'Inter', system-ui, sans-serif;  --font-secondary: 'Inter', system-ui, sans-serif;  /* Font sizes */  --text-xs: 0.75rem;  --text-sm: 0.875rem;  --text-md: 0.9375rem;  --text-base: 1rem;  --text-lg: 1.125rem;  --text-xl: 1.25rem;  --text-2xl: 1.5rem;  /* Radius */  --radius-card: 16px;  --radius-content: 12px;  --radius-full: 100px;  --radius-sm: 6px;  --radius-md: 8px;  --radius-lg: 12px;  --radius-xl: 16px;  /* Shadows */  --pm-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);  --pm-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);  --pm-shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.12);}/* ═══════════════════════════════════════════════   DARK MODE   ═══════════════════════════════════════════════ */.dark {  /* Page backgrounds - deep navy */  --pm-gradient-start: #0B1525;  --pm-gradient-mid: #0F1B2E;  --pm-gradient-end: #132238;  --pm-content-bg: #0F1B2E;  --pm-card-bg: #152035;  --pm-card-bg-hover: #1A2A44;  /* Text colors */  --pm-text-primary: #FFFFFF;  --pm-text-secondary: #94A3B8;  --pm-text-muted: #64748B;  --pm-text-grey: #64748B;  --pm-text-on-accent: #FFFFFF;  /* Accent colors -- teal lighter for dark bg */  --pm-accent-primary: #2DD4BF;  --pm-accent-primary-hover: #5EEAD4;  --pm-accent-primary-bg: rgba(45, 212, 191, 0.12);  --pm-accent-green: #34D399;  --pm-accent-green-bg: rgba(52, 211, 153, 0.15);  --pm-accent-red: #F87171;  --pm-accent-red-bg: rgba(248, 113, 113, 0.12);  --pm-accent-orange: #FBBF24;  --pm-accent-orange-bg: rgba(251, 191, 36, 0.12);  --pm-accent-purple: #A78BFA;  --pm-accent-purple-bg: rgba(167, 139, 250, 0.12);  --pm-accent-blue: #60A5FA;  --pm-accent-blue-bg: rgba(96, 165, 250, 0.12);  /* Sidebar */  --pm-sidebar-bg: #0D1B30;  --pm-sidebar-border: rgba(255, 255, 255, 0.06);  --pm-sidebar-item-color: #94A3B8;  --pm-sidebar-item-hover-bg: rgba(45, 212, 191, 0.10);  --pm-sidebar-item-hover-color: #E2E8F0;  --pm-sidebar-item-active-bg: rgba(45, 212, 191, 0.15);  --pm-sidebar-item-active-color: #FFFFFF;  --pm-sidebar-item-active-shadow: 0 0 16px rgba(45, 212, 191, 0.22);  --pm-sidebar-item-active-border: #2DD4BF;  --pm-sidebar-icon-filter: brightness(0) invert(1);  --pm-sidebar-icon-opacity: 0.5;  --pm-sidebar-icon-active-opacity: 1;  /* Chart */  --pm-bar-light: #1E3050;  --pm-bar-active: #2DD4BF;  --pm-tooltip-bg: #152035;  /* Trend badges */  --pm-trend-green-bg: rgba(52, 211, 153, 0.15);  --pm-trend-red-bg: rgba(248, 113, 113, 0.12);  /* Borders */  --pm-border: #1E3050;  --pm-border-light: #1A2A44;  --pm-border-heavy: #2A3F5F;  /* Inputs / Forms */  --pm-input-bg: #152035;  --pm-input-border: #1E3050;  --pm-input-text: #F1F5F9;  --pm-input-placeholder: #64748B;  --pm-input-focus-border: #2DD4BF;  --pm-input-focus-ring: rgba(45, 212, 191, 0.2);  /* Tables */  --pm-table-header-bg: #1A2A44;  --pm-table-header-color: #94A3B8;  --pm-table-row-hover: #1A2A44;  --pm-table-row-selected: rgba(45, 212, 191, 0.08);  --pm-table-border: #1E3050;  /* Modals */  --pm-modal-bg: #152035;  --pm-modal-overlay: rgba(0, 0, 0, 0.7);  --pm-modal-border: #1E3050;  /* Buttons */  --pm-btn-secondary-bg: #1E293B;  --pm-btn-secondary-color: #CBD5E1;  --pm-btn-secondary-border: #334155;  --pm-btn-secondary-hover-bg: #334155;  --pm-btn-danger-bg: rgba(248, 113, 113, 0.1);  --pm-btn-danger-color: #F87171;  --pm-btn-danger-hover-bg: rgba(248, 113, 113, 0.2);  /* Badges / Tags */  --pm-badge-bg: #1E293B;  --pm-badge-color: #CBD5E1;  --pm-badge-border: #334155;  /* Dropdown / Popover */  --pm-dropdown-bg: #1E293B;  --pm-dropdown-border: #334155;  --pm-dropdown-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05);  --pm-dropdown-item-hover: #334155;  /* Tooltip */  --pm-tooltip-color: #FFFFFF;  --pm-tooltip-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);  /* Avatar */  --pm-avatar-gradient: linear-gradient(135deg, #2DD4BF, #60A5FA);  --pm-avatar-border: #1E293B;  /* Scrollbar */  --pm-scrollbar-thumb: rgba(255, 255, 255, 0.06);  /* Shadows */  --pm-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2);  --pm-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);  --pm-shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.4);}
```

---

-    **Step 6: Create global stylesheet**

**File: `frontend/src/styles/global.css`**

```css
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");@import "./variables.css";*,*::before,*::after {  box-sizing: border-box;  margin: 0;  padding: 0;}html,body,#root {  height: 100%;  width: 100%;  overflow: hidden;}body {  font-family: var(--font-primary);  -webkit-font-smoothing: antialiased;  -moz-osx-font-smoothing: grayscale;  background: linear-gradient(    to bottom right,    var(--pm-gradient-start),    var(--pm-gradient-mid),    var(--pm-gradient-end)  );  color: var(--pm-text-primary);}img {  display: block;  max-width: 100%;}button {  cursor: pointer;  border: none;  background: none;  font-family: inherit;}a {  text-decoration: none;  color: inherit;}/* Hide scrollbar utility */.scrollbar-hide {  -ms-overflow-style: none;  scrollbar-width: none;}.scrollbar-hide::-webkit-scrollbar {  display: none;}/* ═══════════════════════════════════   DARK MODE OVERRIDES   ═══════════════════════════════════ */.dark body,body.dark {  background: linear-gradient(    to bottom right,    #0B1525,    #0F1B2E,    #0B1525  );  color: #F1F5F9;}/* Scrollbar (dark) */.dark ::-webkit-scrollbar {  width: 6px;  height: 6px;}.dark ::-webkit-scrollbar-track {  background: #0F1B2E;}.dark ::-webkit-scrollbar-thumb {  background: #1E3050;  border-radius: 4px;}.dark ::-webkit-scrollbar-thumb:hover {  background: #2A4066;}.dark {  scrollbar-color: #1E3050 #0F1B2E;}/* Selection (dark) */.dark ::selection {  background: rgba(45, 212, 191, 0.3);  color: #F1F5F9;}.dark ::-moz-selection {  background: rgba(45, 212, 191, 0.3);  color: #F1F5F9;}
```

Import in `frontend/src/main.tsx`:

```tsx
import './styles/global.css'
```

---

-    **Step 7: Define shared TypeScript types**

**File: `frontend/src/types.ts`**

```ts
export type UserRole = 'coach' | 'admin'export type AuthUser = {  id: number  email: string  name: string  role: UserRole  avatar_url?: string}export type Coach = {  id: number  name: string  email: string  active_client_count: number  is_active: boolean}export type Account = {  id: number  company_name: string  assigned_coach_id: number  assigned_coach_name: string}export type Client = {  id: number  name: string  email: string  account_id: number  account_name: string  assigned_coach_id: number  assigned_coach_name: string}export type AuditRecord = {  id: number  sync_run_id: number  change_type: 'reassignment' | 'new_assignment' | 'removed'  client_id: number  client_name: string  previous_coach_id: number | null  previous_coach_name: string | null  new_coach_id: number | null  new_coach_name: string | null  detected_at: string  transition_brief?: string}export type SyncRun = {  id: number  triggered_by: string  started_at: string  completed_at: string | null  status: 'running' | 'completed' | 'failed'  changes_detected: number}
```

---

-    **Step 8: Set up the axios API client with CSRF handling**

**File: `frontend/src/api.ts`**

```ts
import axios from 'axios'import type {  AuthUser,  Coach,  Client,  Account,  AuditRecord,  SyncRun,} from './types'const http = axios.create({  baseURL: import.meta.env.VITE_API_URL || '/api',  headers: { 'Content-Type': 'application/json' },  withCredentials: true, // send session cookie for CSRF})// ── CSRF: read Django's csrftoken cookie and attach it as X-CSRFToken ──function getCsrfToken(): string | null {  const match = document.cookie.match(/csrftoken=([^;]+)/)  return match ? match[1] : null}http.interceptors.request.use(config => {  // Attach CSRF token for state-changing methods  if (['post', 'put', 'patch', 'delete'].includes(config.method ?? '')) {    const csrf = getCsrfToken()    if (csrf) {      config.headers['X-CSRFToken'] = csrf    }  }  // Attach auth token  const token = localStorage.getItem('cc_auth_token')  if (token) {    config.headers['Authorization'] = `Token ${token}`  }  return config})// ── Handle 401/403 responses globally ──http.interceptors.response.use(  response => response,  error => {    if (error.response?.status === 401) {      localStorage.removeItem('cc_auth_token')      localStorage.removeItem('cc_user_data')      window.location.href = '/login'    } else if (error.response?.status === 403) {      window.dispatchEvent(new CustomEvent('cc:permission-denied'))    }    return Promise.reject(error)  })// ── Generic CRUD helper ──function crud<T>(resource: string) {  return {    list: (params?: Record<string, string>) =>      http.get<{ results: T[]; count: number }>(`/${resource}/`, { params }).then(r => r.data),    get: (id: number | string) =>      http.get<T>(`/${resource}/${id}/`).then(r => r.data),    create: (data: Partial<T>) =>      http.post<T>(`/${resource}/`, data).then(r => r.data),    update: (id: number | string, data: Partial<T>) =>      http.patch<T>(`/${resource}/${id}/`, data).then(r => r.data),    delete: (id: number | string) =>      http.delete(`/${resource}/${id}/`),  }}// ── Auth API ──export const authApi = {  login: (credentials: { email: string; password: string }) =>    http.post<{ token: string; user: AuthUser }>('/auth/login/', credentials).then(r => r.data),  logout: () =>    http.post('/auth/logout/'),  me: () =>    http.get<AuthUser>('/auth/me/').then(r => r.data),}// ── Resource APIs ──export const coachesApi = crud<Coach>('coaches')export const accountsApi = crud<Account>('accounts')export const clientsApi = crud<Client>('clients')export const auditApi = {  ...crud<AuditRecord>('audit'),  listBySyncRun: (syncRunId: number) =>    http.get<{ results: AuditRecord[]; count: number }>(`/audit/`, {      params: { sync_run: syncRunId },    }).then(r => r.data),}export const syncApi = {  list: () =>    http.get<{ results: SyncRun[]; count: number }>('/sync-runs/').then(r => r.data),  trigger: () =>    http.post<SyncRun>('/sync-runs/trigger/').then(r => r.data),  get: (id: number) =>    http.get<SyncRun>(`/sync-runs/${id}/`).then(r => r.data),}export default http
```

---

-    **Step 9: Create AuthContext (coach/admin roles)**

**File: `frontend/src/context/AuthContext.tsx`**

```tsx
import {  createContext,  useContext,  useState,  useEffect,  useCallback,  type ReactNode,} from 'react'import { authApi } from '../api'import type { AuthUser, UserRole } from '../types'type AuthContextType = {  user: AuthUser | null  loading: boolean  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>  logout: () => void  isAdmin: boolean  isCoach: boolean  hasRole: (role: UserRole) => boolean}const AuthContext = createContext<AuthContextType | null>(null)export function AuthProvider({ children }: { children: ReactNode }) {  const [user, setUser] = useState<AuthUser | null>(null)  const [loading, setLoading] = useState(true)  // On mount: restore session from localStorage + validate with API  useEffect(() => {    const token = localStorage.getItem('cc_auth_token')    const cachedUser = localStorage.getItem('cc_user_data')    if (token) {      // Set cached user immediately for instant UI render      if (cachedUser) {        try {          setUser(JSON.parse(cachedUser))        } catch {          /* ignore corrupt cache */        }        setLoading(false)      }      // Validate token with API in background      authApi        .me()        .then(u => {          setUser(u)          localStorage.setItem('cc_user_data', JSON.stringify(u))        })        .catch(() => {          localStorage.removeItem('cc_auth_token')          localStorage.removeItem('cc_user_data')          setUser(null)        })        .finally(() => setLoading(false))    } else {      setLoading(false)    }  }, [])  const login = async (email: string, password: string) => {    try {      const { token, user: u } = await authApi.login({ email, password })      localStorage.setItem('cc_auth_token', token)      localStorage.setItem('cc_user_data', JSON.stringify(u))      setUser(u)      return { success: true }    } catch (err: unknown) {      const msg =        (err as { response?: { data?: { error?: string } } })?.response?.data          ?.error || 'Login failed'      return { success: false, error: msg }    }  }  const logout = () => {    authApi.logout().catch(() => {})    localStorage.removeItem('cc_auth_token')    localStorage.removeItem('cc_user_data')    setUser(null)  }  const isAdmin = user?.role === 'admin'  const isCoach = user?.role === 'coach'  const hasRole = useCallback(    (role: UserRole): boolean => user?.role === role,    [user]  )  return (    <AuthContext.Provider      value={{ user, loading, login, logout, isAdmin, isCoach, hasRole }}    >      {children}    </AuthContext.Provider>  )}export function useAuth() {  const ctx = useContext(AuthContext)  if (!ctx) throw new Error('useAuth must be used within AuthProvider')  return ctx}
```

---

-    **Step 10: Create ThemeContext for dark mode**

**File: `frontend/src/context/ThemeContext.tsx`**

```tsx
import {  createContext,  useContext,  useState,  useEffect,  type ReactNode,} from 'react'type Theme = 'light' | 'dark'type ThemeContextType = {  theme: Theme  toggleTheme: () => void  isDark: boolean}const ThemeContext = createContext<ThemeContextType | null>(null)export function ThemeProvider({ children }: { children: ReactNode }) {  const [theme, setTheme] = useState<Theme>(() => {    const saved = localStorage.getItem('cc_theme')    return saved === 'dark' ? 'dark' : 'light'  })  useEffect(() => {    const root = document.documentElement    if (theme === 'dark') {      root.classList.add('dark')    } else {      root.classList.remove('dark')    }    localStorage.setItem('cc_theme', theme)  }, [theme])  const toggleTheme = () => setTheme(t => (t === 'light' ? 'dark' : 'light'))  const isDark = theme === 'dark'  return (    <ThemeContext.Provider value={{ theme, toggleTheme, isDark }}>      {children}    </ThemeContext.Provider>  )}export function useTheme() {  const ctx = useContext(ThemeContext)  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')  return ctx}
```

---

-    **Step 11: Create ProtectedRoute component**

**File: `frontend/src/components/ProtectedRoute.tsx`**

```tsx
import { Navigate, Outlet } from 'react-router-dom'import { useAuth } from '../context/AuthContext'import type { UserRole } from '../types'type Props = {  /** If set, only users with this role can access the route */  requiredRole?: UserRole}export default function ProtectedRoute({ requiredRole }: Props) {  const { user, loading } = useAuth()  if (loading) {    return (      <div        style={{          display: 'flex',          alignItems: 'center',          justifyContent: 'center',          height: '100vh',          color: 'var(--pm-text-muted)',        }}      >        Loading...      </div>    )  }  // Not logged in -> redirect to login  if (!user) {    return <Navigate to="/login" replace />  }  // Logged in but wrong role -> redirect to dashboard (or a 403 page)  if (requiredRole && user.role !== requiredRole) {    return <Navigate to="/dashboard" replace />  }  return <Outlet />}
```

---

-    **Step 12: Wire up `main.tsx` and `App.tsx` with providers and routing**

**File: `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'import { createRoot } from 'react-dom/client'import { BrowserRouter } from 'react-router-dom'import { AuthProvider } from './context/AuthContext'import { ThemeProvider } from './context/ThemeContext'import App from './App'import './styles/global.css'createRoot(document.getElementById('root')!).render(  <StrictMode>    <BrowserRouter>      <ThemeProvider>        <AuthProvider>          <App />        </AuthProvider>      </ThemeProvider>    </BrowserRouter>  </StrictMode>)
```

**File: `frontend/src/App.tsx`**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'import ProtectedRoute from './components/ProtectedRoute'// Lazy-load pages as they are built in later tasks// import LoginPage from './pages/LoginPage'// import DashboardPage from './pages/DashboardPage'// import AuditPage from './pages/AuditPage'// import SyncPage from './pages/SyncPage'function PlaceholderPage({ title }: { title: string }) {  return (    <div style={{ padding: '2rem', color: 'var(--pm-text-primary)' }}>      <h1>{title}</h1>      <p style={{ color: 'var(--pm-text-muted)' }}>Coming soon...</p>    </div>  )}export default function App() {  return (    <Routes>      {/* Public */}      <Route path="/login" element={<PlaceholderPage title="Login" />} />      {/* Protected: any authenticated user */}      <Route element={<ProtectedRoute />}>        <Route path="/dashboard" element={<PlaceholderPage title="Dashboard" />} />        <Route path="/audit" element={<PlaceholderPage title="Audit Trail" />} />      </Route>      {/* Protected: admin only */}      <Route element={<ProtectedRoute requiredRole="admin" />}>        <Route path="/sync" element={<PlaceholderPage title="Sync Management" />} />        <Route path="/coaches" element={<PlaceholderPage title="Coaches" />} />      </Route>      {/* Fallback */}      <Route path="*" element={<Navigate to="/dashboard" replace />} />    </Routes>  )}
```

---

-    **Step 13: Create the `.env` file for local development**

**File: `frontend/.env`**

```
VITE_API_URL=/api
```

**File: `frontend/.env.example`**

```
VITE_API_URL=/api
```

Add `frontend/.env` to `.gitignore`.

---

-    **Step 14: Verify the setup compiles cleanly**

```bash
cd frontendnpx tsc --noEmit        # Must exit 0 with no errorsnpm run dev              # Must start on localhost:5173 with no console errors
```

Open `http://localhost:5173` -- you should see the placeholder "Dashboard" page. Toggle between light/dark themes via the browser console:

```js
document.documentElement.classList.toggle('dark')
```

The gradient background should switch between the light blue-gray and deep navy palettes.

---

### File tree after completion

```
frontend/├── .env├── .env.example├── index.html├── package.json├── tsconfig.json├── tsconfig.app.json├── vite.config.ts└── src/    ├── main.tsx    ├── App.tsx    ├── api.ts    ├── types.ts    ├── components/    │   └── ProtectedRoute.tsx    ├── context/    │   ├── AuthContext.tsx    │   └── ThemeContext.tsx    └── styles/        ├── variables.css        └── global.css
```

---

### Key differences from PentEdge-CRM

Aspect

PentEdge-CRM

Coach-Client

Auth method

Google OAuth (`X-User-Email` header)

Token auth (`Authorization: Token xxx`) + CSRF

User roles

Admin + per-module RBAC

`coach` (scoped to own data) + `admin` (full access)

Primary accent

Gold `#9E8544`

Teal `#0D9488`

Dark accent

Gold `#C4A767`

Teal `#2DD4BF`

localStorage prefix

`crm_`

`cc_`

Permission model

`canRead/canCreate/canEdit/canDelete` per module

`isAdmin` / `isCoach` / `hasRole()` -- simpler, role-based

CSRF handling

None (email header auth)

Django `csrftoken` cookie read + `X-CSRFToken` header

Font

Satoshi

Inter

---

## Task 10: Login Page

> **Pattern reference:** `Docs/PentEdge-CRM/frontend/src/pages/LoginPage.tsx` and `LoginPage.module.css`Adapted from PentEdge CRM's centered login page pattern -- card-based, branded, animated -- but using username/password form fields instead of Google OAuth, with `--pm-*` CSS variables.

### Files to create

File

Purpose

`frontend/src/pages/LoginPage.tsx`

Login page component (TypeScript)

`frontend/src/pages/LoginPage.module.css`

CSS Module with `--pm-*` tokens

---

### 10.1 -- CSS Module

-    Create `frontend/src/pages/LoginPage.module.css`

```css
/* ── Login Page ── */.loginPage {  position: relative;  width: 100vw;  height: 100vh;  overflow: hidden;  background: linear-gradient(    135deg,    var(--pm-gradient-start) 0%,    var(--pm-gradient-mid) 50%,    var(--pm-gradient-end) 100%  );  display: flex;  align-items: center;  justify-content: center;  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;}/* ── Background blob (decorative) ── */.blob {  position: absolute;  width: 600px;  height: 600px;  top: 50%;  left: 50%;  transform: translate(-50%, -50%);  border-radius: 50%;  background: radial-gradient(    ellipse at center,    rgba(158, 133, 68, 0.12) 0%,    rgba(158, 133, 68, 0.06) 40%,    transparent 70%  );  filter: blur(40px);  animation: blobPulse 8s ease-in-out infinite;  pointer-events: none;  z-index: 0;}@keyframes blobPulse {  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }  50%      { transform: translate(-50%, -50%) scale(1.08); opacity: 0.85; }}/* ── Login Card ── */.card {  position: relative;  z-index: 1;  width: 100%;  max-width: 420px;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border-light);  border-radius: 16px;  box-shadow:    0 4px 24px rgba(0, 0, 0, 0.06),    0 1px 4px rgba(0, 0, 0, 0.04);  padding: 40px 36px 32px;  display: flex;  flex-direction: column;  align-items: center;  animation: cardIn 0.6s ease-out both;}@keyframes cardIn {  from {    opacity: 0;    transform: translateY(24px) scale(0.97);  }  to {    opacity: 1;    transform: translateY(0) scale(1);  }}/* ── Brand area ── */.brandIcon {  width: 52px;  height: 52px;  border-radius: 14px;  background: var(--pm-accent-primary);  display: flex;  align-items: center;  justify-content: center;  margin-bottom: 20px;  box-shadow: 0 2px 8px rgba(158, 133, 68, 0.25);}.brandIcon svg {  width: 28px;  height: 28px;  color: var(--pm-text-on-accent);}.title {  font-size: 26px;  font-weight: 700;  color: var(--pm-text-primary);  letter-spacing: -0.4px;  margin: 0 0 4px;}.titleAccent {  color: var(--pm-accent-primary);}.subtitle {  font-size: 14px;  color: var(--pm-text-muted);  margin: 0 0 28px;}/* ── Form ── */.form {  width: 100%;  display: flex;  flex-direction: column;  gap: 18px;}.fieldGroup {  display: flex;  flex-direction: column;  gap: 6px;}.label {  font-size: 13px;  font-weight: 600;  color: var(--pm-text-primary);  letter-spacing: 0.01em;}.input {  width: 100%;  padding: 11px 14px;  font-size: 14px;  color: var(--pm-input-text);  background: var(--pm-input-bg);  border: 1px solid var(--pm-input-border);  border-radius: 10px;  outline: none;  transition: border-color 0.2s, box-shadow 0.2s;  box-sizing: border-box;}.input::placeholder {  color: var(--pm-input-placeholder);}.input:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}/* ── Submit button ── */.submitBtn {  width: 100%;  padding: 12px;  margin-top: 4px;  font-size: 15px;  font-weight: 600;  color: var(--pm-text-on-accent);  background: var(--pm-accent-primary);  border: none;  border-radius: 10px;  cursor: pointer;  transition: background 0.2s, box-shadow 0.2s;}.submitBtn:hover:not(:disabled) {  background: var(--pm-accent-primary-hover);  box-shadow: 0 4px 12px rgba(158, 133, 68, 0.2);}.submitBtn:disabled {  opacity: 0.6;  cursor: not-allowed;}/* ── Error message ── */.error {  width: 100%;  padding: 10px 14px;  font-size: 13px;  color: var(--pm-accent-red);  background: var(--pm-accent-red-bg);  border: 1px solid var(--pm-accent-red);  border-radius: 8px;  text-align: center;}/* ── Credentials hint ── */.hint {  width: 100%;  margin-top: 8px;  padding: 12px 14px;  background: var(--pm-accent-primary-bg);  border: 1px dashed var(--pm-accent-gold);  border-radius: 10px;}.hintTitle {  font-size: 12px;  font-weight: 600;  color: var(--pm-accent-primary);  margin: 0 0 6px;  text-transform: uppercase;  letter-spacing: 0.04em;}.hintRow {  display: flex;  align-items: center;  gap: 8px;  font-size: 13px;  color: var(--pm-text-grey);  line-height: 1.6;}.hintRow code {  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;  font-size: 12px;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border-light);  border-radius: 4px;  padding: 1px 6px;  color: var(--pm-text-primary);}/* ── Footer ── */.footer {  margin-top: 24px;  font-size: 12px;  color: var(--pm-text-muted);}
```

---

### 10.2 -- LoginPage Component

-    Create `frontend/src/pages/LoginPage.tsx`

```tsx
import { useState, type FormEvent } from 'react'import { useNavigate } from 'react-router-dom'import { useAuth } from '../context/AuthContext'import styles from './LoginPage.module.css'export default function LoginPage() {  const navigate = useNavigate()  const { login } = useAuth()  const [username, setUsername] = useState('')  const [password, setPassword] = useState('')  const [error, setError] = useState('')  const [loading, setLoading] = useState(false)  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {    e.preventDefault()    setError('')    setLoading(true)    try {      const result = await login(username.trim(), password)      if (!result.success) {        setError(result.error || 'Invalid username or password.')        setLoading(false)        return      }      // Redirect based on role      if (result.user?.role === 'admin') {        navigate('/admin', { replace: true })      } else {        navigate('/', { replace: true })      }    } catch {      setError('Something went wrong. Please try again.')      setLoading(false)    }  }  return (    <div className={styles.loginPage}>      {/* Decorative background blob */}      <div className={styles.blob} />      <div className={styles.card}>        {/* Brand icon */}        <div className={styles.brandIcon}>          <svg            viewBox="0 0 24 24"            fill="none"            stroke="currentColor"            strokeWidth="2"            strokeLinecap="round"            strokeLinejoin="round"          >            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />            <circle cx="9" cy="7" r="4" />            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />            <path d="M16 3.13a4 4 0 0 1 0 7.75" />          </svg>        </div>        <h1 className={styles.title}>          Coach <span className={styles.titleAccent}>Portal</span>        </h1>        <p className={styles.subtitle}>Sign in to manage your coaching assignments</p>        <form className={styles.form} onSubmit={handleSubmit}>          {error && <div className={styles.error}>{error}</div>}          <div className={styles.fieldGroup}>            <label htmlFor="username" className={styles.label}>              Username            </label>            <input              id="username"              className={styles.input}              type="text"              placeholder="Enter your username"              value={username}              onChange={(e) => setUsername(e.target.value)}              autoComplete="username"              autoFocus              required            />          </div>          <div className={styles.fieldGroup}>            <label htmlFor="password" className={styles.label}>              Password            </label>            <input              id="password"              className={styles.input}              type="password"              placeholder="Enter your password"              value={password}              onChange={(e) => setPassword(e.target.value)}              autoComplete="current-password"              required            />          </div>          <button            type="submit"            className={styles.submitBtn}            disabled={loading || !username.trim() || !password}          >            {loading ? 'Signing in...' : 'Sign In'}          </button>        </form>        {/* Test credentials hint */}        <div className={styles.hint}>          <p className={styles.hintTitle}>Test Credentials</p>          <div className={styles.hintRow}>            Coach: <code>alice</code> / <code>alice123</code>          </div>          <div className={styles.hintRow}>            Admin: <code>admin</code> / <code>admin123</code>          </div>        </div>        <div className={styles.footer}>          &copy; 2026 Coach-Client Reassignment System        </div>      </div>    </div>  )}
```

---

### 10.3 -- Integration checklist

-    Verify `AuthContext` exposes a `login(username, password)` function that returns `{ success: boolean; error?: string; user?: { role: string } }`
-    Add route in the router: `<Route path="/login" element={<LoginPage />} />`
-    Ensure unauthenticated users redirect to `/login` (via `ProtectedRoute` or equivalent)
-    After login, coach role navigates to `/` (coach dashboard), admin role navigates to `/admin`
-    Confirm `variables.css` (or equivalent) is imported globally so `--pm-*` tokens resolve correctly
-    Test: entering `alice` / `alice123` logs in as coach and redirects to `/`
-    Test: entering `admin` / `admin123` logs in as admin and redirects to `/admin`
-    Test: entering wrong credentials shows the error banner inside the card
-    Test: the page renders centered on mobile viewports (the `max-width: 420px` card scales down gracefully)

---

## Task 11: Layout, Sidebar & Header (CrmLayout Pattern)

**Files:**

-   Create: `frontend/src/context/ThemeContext.tsx`
-   Create: `frontend/src/components/CrmLayout.tsx`
-   Create: `frontend/src/components/CrmLayout.module.css`
-   Create: `frontend/src/components/Sidebar.tsx`
-   Create: `frontend/src/components/Sidebar.module.css`
-   Create: `frontend/src/components/DashboardHeader.tsx`
-   Create: `frontend/src/components/DashboardHeader.module.css`
-   Create: `frontend/src/styles/variables.css`

> **Pattern:** Mirrors PentEdge-CRM's `CrmLayout + CrmSidebar + DashboardHeader` architecture. Fixed viewport wrapper, flex layout with 12px gap/padding, collapsible sidebar (250px to 60px), content area with rounded border and `var(--pm-*)` CSS variables for light/dark mode.

---

-    **Step 1: Create CSS variables file**

`frontend/src/styles/variables.css`:

```css
/* ══════════════════════════════════════════════════   Coach-Client Design Tokens (--pm-* namespace)   Light + Dark mode via .dark class on <html>   ══════════════════════════════════════════════════ */:root {  /* ── Typography ── */  --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;  /* ── Radius ── */  --radius-sm: 6px;  --radius-md: 8px;  --radius-lg: 12px;  --radius-xl: 16px;  --radius-full: 9999px;  /* ── Font sizes ── */  --text-xs: 11px;  --text-sm: 13px;  --text-md: 14px;  --text-lg: 18px;  /* ── Light mode (default) ── */  --pm-content-bg: #ffffff;  --pm-card-bg: #ffffff;  --pm-card-bg-hover: #f9fafb;  --pm-border: #e5e7eb;  --pm-border-light: #f3f4f6;  --pm-text-primary: #111827;  --pm-text-secondary: #6b7280;  --pm-text-muted: #9ca3af;  --pm-text-on-accent: #ffffff;  --pm-accent-primary: #3b82f6;  --pm-accent-gold: #d4a843;  --pm-accent-red: #ef4444;  --pm-input-text: #111827;  --pm-input-placeholder: #9ca3af;  /* ── Sidebar light ── */  --pm-sidebar-bg: #ffffff;  --pm-sidebar-border: #e5e7eb;  --pm-sidebar-item-color: #6b7280;  --pm-sidebar-item-hover-bg: #f3f4f6;  --pm-sidebar-item-hover-color: #111827;  --pm-sidebar-item-active-bg: #eff6ff;  --pm-sidebar-item-active-color: #1d4ed8;  --pm-sidebar-item-active-border: #3b82f6;  --pm-sidebar-item-active-shadow: 0 1px 3px rgba(59, 130, 246, 0.1);  --pm-sidebar-icon-opacity: 0.6;  --pm-sidebar-icon-active-opacity: 1;  --pm-sidebar-icon-filter: none;  --pm-sidebar-item-active-icon-filter: none;  /* ── Shadows ── */  --pm-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);  --pm-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);  /* ── Dropdowns / menus ── */  --pm-dropdown-bg: #ffffff;  --pm-dropdown-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);  --pm-dropdown-border: #e5e7eb;  --pm-dropdown-item-hover: #f3f4f6;  /* ── Avatar ── */  --pm-avatar-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);  --pm-avatar-border: #e5e7eb;  /* ── Profile menu ── */  --pm-profile-menu-bg: #ffffff;  --pm-profile-menu-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);  --pm-profile-divider: #f3f4f6;  /* ── Misc ── */  --pm-online-dot-border: #ffffff;  --pm-scrollbar-thumb: #d1d5db;  --pm-btn-danger-bg: #fef2f2;}/* ── Dark mode ── */.dark {  --pm-content-bg: #111827;  --pm-card-bg: #1f2937;  --pm-card-bg-hover: #374151;  --pm-border: #374151;  --pm-border-light: #1f2937;  --pm-text-primary: #f9fafb;  --pm-text-secondary: #9ca3af;  --pm-text-muted: #6b7280;  --pm-input-text: #f9fafb;  --pm-input-placeholder: #6b7280;  --pm-sidebar-bg: #0d1b30;  --pm-sidebar-border: rgba(255, 255, 255, 0.06);  --pm-sidebar-item-color: #9ca3af;  --pm-sidebar-item-hover-bg: rgba(255, 255, 255, 0.06);  --pm-sidebar-item-hover-color: #f9fafb;  --pm-sidebar-item-active-bg: rgba(59, 130, 246, 0.15);  --pm-sidebar-item-active-color: #60a5fa;  --pm-sidebar-item-active-border: #3b82f6;  --pm-sidebar-item-active-shadow: 0 1px 3px rgba(59, 130, 246, 0.2);  --pm-sidebar-icon-opacity: 0.5;  --pm-sidebar-icon-active-opacity: 1;  --pm-sidebar-icon-filter: brightness(0.7);  --pm-sidebar-item-active-icon-filter: brightness(1.2);  --pm-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);  --pm-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);  --pm-dropdown-bg: #1f2937;  --pm-dropdown-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);  --pm-dropdown-border: #374151;  --pm-dropdown-item-hover: #374151;  --pm-avatar-border: #374151;  --pm-profile-menu-bg: #1f2937;  --pm-profile-menu-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);  --pm-profile-divider: #374151;  --pm-online-dot-border: #1f2937;  --pm-scrollbar-thumb: #4b5563;  --pm-btn-danger-bg: rgba(239, 68, 68, 0.1);}body {  margin: 0;  font-family: var(--font-primary);  background: var(--pm-content-bg);  color: var(--pm-text-primary);  -webkit-font-smoothing: antialiased;  -moz-osx-font-smoothing: grayscale;}
```

---

-    **Step 2: Create ThemeContext**

`frontend/src/context/ThemeContext.tsx`:

```tsx
import { createContext, useContext, useState, useEffect, type ReactNode } from "react";interface ThemeContextValue {  isDark: boolean;  toggleTheme: () => void;}const ThemeContext = createContext<ThemeContextValue>({  isDark: false,  toggleTheme: () => {},});export function ThemeProvider({ children }: { children: ReactNode }) {  const [isDark, setIsDark] = useState<boolean>(() => {    const stored = localStorage.getItem("coach_theme");    if (stored) return stored === "dark";    return window.matchMedia("(prefers-color-scheme: dark)").matches;  });  useEffect(() => {    const root = document.documentElement;    if (isDark) {      root.classList.add("dark");    } else {      root.classList.remove("dark");    }    localStorage.setItem("coach_theme", isDark ? "dark" : "light");  }, [isDark]);  const toggleTheme = () => setIsDark((prev) => !prev);  return (    <ThemeContext.Provider value={{ isDark, toggleTheme }}>      {children}    </ThemeContext.Provider>  );}export const useTheme = () => useContext(ThemeContext);
```

---

-    **Step 3: Create CrmLayout wrapper**

`frontend/src/components/CrmLayout.tsx`:

```tsx
import { useState, useEffect } from "react";import { Outlet, useLocation, useNavigate } from "react-router-dom";import { useAuth } from "../context/AuthContext";import Sidebar from "./Sidebar";import DashboardHeader from "./DashboardHeader";import styles from "./CrmLayout.module.css";const routeToNavId: Record<string, string> = {  "/": "dashboard",  "/dashboard": "dashboard",  "/audit": "audit",  "/briefs": "briefs",  "/source": "source",};function resolveNavId(pathname: string): string {  if (routeToNavId[pathname]) return routeToNavId[pathname];  if (pathname.startsWith("/briefs/")) return "briefs";  if (pathname.startsWith("/audit/")) return "audit";  return "dashboard";}const routeToPageInfo: Record<string, { title: string; subtitle: string }> = {  dashboard: {    title: "Dashboard",    subtitle: "Overview of your coaching assignments and activity.",  },  audit: {    title: "Audit Trail",    subtitle: "Track all reassignment changes across the system.",  },  briefs: {    title: "Transition Briefs",    subtitle: "AI-generated handoff documents for reassignments.",  },  source: {    title: "Source Editor",    subtitle: "Manage simulated Salesforce source data.",  },};export default function CrmLayout() {  const location = useLocation();  const navigate = useNavigate();  const { user } = useAuth();  const [mobileOpen, setMobileOpen] = useState(false);  const activeItem = resolveNavId(location.pathname);  const pageInfo = routeToPageInfo[activeItem];  const handleNavChange = (id: string) => {    const routes: Record<string, string> = {      dashboard: user?.role === "admin" ? "/admin" : "/",      audit: "/audit",      briefs: "/briefs",      source: "/source",    };    navigate(routes[id] || "/");  };  useEffect(() => {    window.scrollTo(0, 0);  }, [location.pathname]);  return (    <div className={styles.pageWrapper}>      <button        className={styles.hamburger}        onClick={() => setMobileOpen((v) => !v)}        type="button"        aria-label={mobileOpen ? "Close menu" : "Open menu"}      >        <svg          viewBox="0 0 24 24"          fill="none"          stroke="currentColor"          strokeWidth="2"          strokeLinecap="round"          strokeLinejoin="round"        >          <line x1="3" y1="6" x2="21" y2="6" />          <line x1="3" y1="12" x2="21" y2="12" />          <line x1="3" y1="18" x2="21" y2="18" />        </svg>      </button>      <div className={styles.layout}>        <Sidebar          activeItem={activeItem}          onActiveChange={handleNavChange}          mobileOpen={mobileOpen}          onMobileClose={() => setMobileOpen(false)}        />        <main className={styles.content}>          <DashboardHeader            title={pageInfo?.title}            subtitle={pageInfo?.subtitle}          />          <Outlet />        </main>      </div>    </div>  );}
```

`frontend/src/components/CrmLayout.module.css`:

```css
/* ══════════════════════════════════════════════════   CrmLayout — Viewport wrapper + flex shell   Matches PentEdge-CRM layout pattern exactly   ══════════════════════════════════════════════════ */.pageWrapper {  position: fixed;  inset: 0;  overflow: hidden;}.layout {  display: flex;  align-items: stretch;  gap: 12px;  height: 100%;  padding: 12px;  overflow: hidden;}.content {  display: flex;  flex-direction: column;  gap: 6px;  flex: 1;  min-width: 0;  padding: 14px 20px;  height: 100%;  overflow: hidden;  background: var(--pm-content-bg);  border-radius: var(--radius-xl);  border: 1px solid var(--pm-border);}/* ── Hamburger button (mobile only) ── */.hamburger {  display: none;  position: fixed;  top: 12px;  left: 12px;  z-index: 1001;  width: 40px;  height: 40px;  border-radius: 10px;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border);  align-items: center;  justify-content: center;  cursor: pointer;  box-shadow: var(--pm-shadow-sm);}.hamburger svg {  width: 20px;  height: 20px;  color: var(--pm-text-primary);}@media (max-width: 768px) {  .hamburger {    display: flex;  }  .layout {    padding: 8px;    gap: 0;  }  .content {    padding: 10px 12px;    padding-top: 52px;    border-radius: var(--radius-lg);    width: 100%;  }}
```

---

-    **Step 4: Create Sidebar component**

`frontend/src/components/Sidebar.tsx`:

```tsx
import { useState, useRef, useEffect } from "react";import { useNavigate } from "react-router-dom";import { useAuth } from "../context/AuthContext";import { useTheme } from "../context/ThemeContext";import styles from "./Sidebar.module.css";/* ── SVG Icon components ── */function DoubleChevron({ direction }: { direction: "left" | "right" }) {  return (    <svg      width="14"      height="14"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="2.5"      strokeLinecap="round"      strokeLinejoin="round"    >      {direction === "right" ? (        <>          <polyline points="7 18 13 12 7 6" />          <polyline points="13 18 19 12 13 6" />        </>      ) : (        <>          <polyline points="17 18 11 12 17 6" />          <polyline points="11 18 5 12 11 6" />        </>      )}    </svg>  );}function SunIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <circle cx="12" cy="12" r="5" />      <line x1="12" y1="1" x2="12" y2="3" />      <line x1="12" y1="21" x2="12" y2="23" />      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />      <line x1="1" y1="12" x2="3" y2="12" />      <line x1="21" y1="12" x2="23" y2="12" />      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />    </svg>  );}function MoonIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />    </svg>  );}function DashboardIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <rect x="3" y="3" width="7" height="9" rx="1" />      <rect x="14" y="3" width="7" height="5" rx="1" />      <rect x="14" y="12" width="7" height="9" rx="1" />      <rect x="3" y="16" width="7" height="5" rx="1" />    </svg>  );}function AuditIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />      <polyline points="14 2 14 8 20 8" />      <line x1="16" y1="13" x2="8" y2="13" />      <line x1="16" y1="17" x2="8" y2="17" />      <polyline points="10 9 9 9 8 9" />    </svg>  );}function BriefsIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />    </svg>  );}function SourceIcon() {  return (    <svg      width="18"      height="18"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <polyline points="16 18 22 12 16 6" />      <polyline points="8 6 2 12 8 18" />    </svg>  );}function ProfileIcon() {  return (    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">      <path        d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"        stroke="currentColor"        strokeWidth="1.5"        strokeLinecap="round"        strokeLinejoin="round"      />      <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" />    </svg>  );}function LogoutIcon() {  return (    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">      <path        d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"        stroke="currentColor"        strokeWidth="1.5"        strokeLinecap="round"        strokeLinejoin="round"      />      <path        d="M16 17l5-5-5-5M21 12H9"        stroke="currentColor"        strokeWidth="1.5"        strokeLinecap="round"        strokeLinejoin="round"      />    </svg>  );}/* ── Nav slot builder ── */interface NavSlot {  id: string;  icon: React.ReactNode;  label: string;  adminOnly?: boolean;}const NAV_SLOTS: NavSlot[] = [  { id: "dashboard", icon: <DashboardIcon />, label: "Dashboard" },  { id: "audit", icon: <AuditIcon />, label: "Audit Trail", adminOnly: true },  { id: "briefs", icon: <BriefsIcon />, label: "Briefs" },  { id: "source", icon: <SourceIcon />, label: "Source Editor", adminOnly: true },];/* ── Component ── */interface SidebarProps {  activeItem: string;  onActiveChange: (id: string) => void;  mobileOpen?: boolean;  onMobileClose?: () => void;}export default function Sidebar({  activeItem,  onActiveChange,  mobileOpen,  onMobileClose,}: SidebarProps) {  const navigate = useNavigate();  const { user, logout } = useAuth();  const { isDark, toggleTheme } = useTheme();  const [collapsed, setCollapsed] = useState<boolean>(    () => localStorage.getItem("coach_sidebar_collapsed") === "true"  );  const [showProfileMenu, setShowProfileMenu] = useState(false);  const profileMenuRef = useRef<HTMLDivElement>(null);  const isAdmin = user?.role === "admin";  const visibleSlots = NAV_SLOTS.filter(    (slot) => !slot.adminOnly || isAdmin  );  const toggleCollapse = () =>    setCollapsed((v) => {      localStorage.setItem("coach_sidebar_collapsed", String(!v));      return !v;    });  useEffect(() => {    const handler = (e: MouseEvent) => {      if (        profileMenuRef.current &&        !profileMenuRef.current.contains(e.target as Node)      ) {        setShowProfileMenu(false);      }    };    document.addEventListener("mousedown", handler);    return () => document.removeEventListener("mousedown", handler);  }, []);  const handleLogout = async () => {    setShowProfileMenu(false);    onMobileClose?.();    await logout();    navigate("/login");  };  return (    <>      {mobileOpen && <div className={styles.overlay} onClick={onMobileClose} />}      <aside        className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ""} ${mobileOpen ? styles.sidebarMobileOpen : ""}`}      >        {/* ── Logo row with collapse toggle ── */}        <div className={styles.logoRow}>          <span className={styles.logoText}>            {collapsed ? "CP" : "Coach Portal"}          </span>          <button            className={styles.collapseBtn}            onClick={toggleCollapse}            type="button"            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}          >            <DoubleChevron direction={collapsed ? "right" : "left"} />          </button>        </div>        {/* ── Navigation ── */}        <nav className={styles.nav}>          {visibleSlots.map((slot) => (            <button              key={slot.id}              className={`${styles.navItem} ${activeItem === slot.id ? styles.navItemActive : ""}`}              onClick={() => {                onActiveChange(slot.id);                onMobileClose?.();              }}              type="button"              aria-label={slot.label}              title={slot.label}              data-tooltip={collapsed ? slot.label : undefined}            >              <span className={styles.navIcon}>{slot.icon}</span>              {!collapsed && <span className={styles.navLabel}>{slot.label}</span>}            </button>          ))}        </nav>        {/* ── Bottom: theme toggle + user ── */}        <div className={styles.bottom} ref={profileMenuRef}>          <button            className={styles.themeBtn}            onClick={toggleTheme}            type="button"            title={isDark ? "Light Mode" : "Dark Mode"}            data-tooltip={collapsed ? (isDark ? "Light Mode" : "Dark Mode") : undefined}          >            <span className={styles.themeBtnIcon}>              {isDark ? <SunIcon /> : <MoonIcon />}            </span>            {!collapsed && <span>{isDark ? "Light Mode" : "Dark Mode"}</span>}          </button>          <button            className={styles.userBtn}            onClick={() => setShowProfileMenu((v) => !v)}            type="button"          >            <span className={styles.avatar}>              {(user?.username || "U").slice(0, 2).toUpperCase()}            </span>            {!collapsed && (              <span className={styles.userName}>{user?.username || "User"}</span>            )}            {!collapsed && (              <svg                width="12"                height="12"                viewBox="0 0 24 24"                fill="none"                stroke="currentColor"                strokeWidth="2"                strokeLinecap="round"                strokeLinejoin="round"                className={styles.userChevron}              >                <polyline points="6 15 12 9 18 15" />              </svg>            )}            <span className={styles.onlineDot} />          </button>          {showProfileMenu && (            <div className={styles.profileMenu}>              <div className={styles.profileHeader}>                <span className={styles.profileName}>                  {user?.username || "User"}                </span>                <span className={styles.profileRole}>{user?.role || "coach"}</span>              </div>              <div className={styles.profileDivider} />              <button                className={styles.profileItem}                type="button"                onClick={() => {                  setShowProfileMenu(false);                  onMobileClose?.();                }}              >                <ProfileIcon />                <span>My Profile</span>              </button>              <button                className={`${styles.profileItem} ${styles.profileItemDanger}`}                type="button"                onClick={handleLogout}              >                <LogoutIcon />                <span>Logout</span>              </button>            </div>          )}        </div>      </aside>    </>  );}
```

`frontend/src/components/Sidebar.module.css`:

```css
/* ══════════════════════════════════════════════════   Sidebar — Coach-Client (PentEdge pattern)   250px expanded → 60px collapsed   ══════════════════════════════════════════════════ */.sidebar {  display: flex;  flex-direction: column;  width: 250px;  height: 100%;  background: var(--pm-sidebar-bg);  border-right: 1px solid var(--pm-sidebar-border);  box-sizing: border-box;  flex-shrink: 0;  overflow: visible;  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);  position: relative;  z-index: 50;}.sidebarCollapsed {  width: 60px;  overflow: visible;}/* Dark mode gradient background */:global(.dark) .sidebar {  background: linear-gradient(180deg, #0d1b30 0%, #081424 100%);  border-right-color: rgba(255, 255, 255, 0.06);}:global(.dark) .navItemActive {  background: linear-gradient(    135deg,    rgba(0, 201, 167, 0.25),    rgba(59, 130, 246, 0.14)  );}:global(.dark) .sidebarCollapsed .navItemActive {  border-bottom-color: #00c9a7;}/* ── Logo row ── */.logoRow {  display: flex;  align-items: center;  justify-content: space-between;  padding: 14px 14px 10px;  flex-shrink: 0;}.logoText {  font-family: var(--font-primary);  font-weight: 700;  font-size: 16px;  color: var(--pm-text-primary);  white-space: nowrap;  overflow: hidden;  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);}.sidebarCollapsed .logoRow {  justify-content: center;  padding: 14px 0 10px;  flex-direction: column;  align-items: center;  gap: 6px;}.sidebarCollapsed .logoText {  font-size: 14px;  font-weight: 800;}/* ── Collapse / Expand button ── */.collapseBtn {  width: 28px;  height: 28px;  border-radius: 6px;  display: flex;  align-items: center;  justify-content: center;  background: var(--pm-sidebar-item-hover-bg);  border: 1px solid var(--pm-sidebar-border);  color: var(--pm-sidebar-item-color);  cursor: pointer;  transition: all 0.2s ease;  flex-shrink: 0;}.sidebarCollapsed .collapseBtn {  width: 36px;  height: 36px;  border-radius: 8px;  margin-bottom: 6px;}.collapseBtn:hover {  background: var(--pm-sidebar-item-hover-bg);  color: var(--pm-sidebar-item-hover-color);  border-color: var(--pm-sidebar-item-hover-color);}/* ── Navigation ── */.nav {  flex: 1;  overflow-y: auto;  overflow-x: hidden;  padding: 8px 10px;  display: flex;  flex-direction: column;  gap: 6px;  scrollbar-width: thin;  scrollbar-color: var(--pm-scrollbar-thumb) transparent;}.nav::-webkit-scrollbar {  width: 4px;}.nav::-webkit-scrollbar-track {  background: transparent;}.nav::-webkit-scrollbar-thumb {  background: var(--pm-scrollbar-thumb);  border-radius: 4px;}.sidebarCollapsed .nav {  padding: 8px 8px;  align-items: center;  gap: 6px;}/* ── Nav item ── */.navItem {  display: flex;  align-items: center;  gap: 12px;  width: 100%;  padding: 9px 12px;  border-radius: 10px;  border: none;  border-left: 3.5px solid transparent;  background: transparent;  color: var(--pm-sidebar-item-color);  cursor: pointer;  font-family: var(--font-primary);  font-size: 14px;  font-weight: 500;  line-height: 1.4;  white-space: nowrap;  text-align: left;  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);  position: relative;}.navItem:hover {  background: var(--pm-sidebar-item-hover-bg);  color: var(--pm-sidebar-item-hover-color);}.navItem:active {  transform: scale(0.97);}/* ── Active state ── */.navItemActive {  background: var(--pm-sidebar-item-active-bg);  color: var(--pm-sidebar-item-active-color);  font-weight: 600;  border-left-color: var(--pm-sidebar-item-active-border);  box-shadow: var(--pm-sidebar-item-active-shadow);}.navItemActive:hover {  background: var(--pm-sidebar-item-active-bg);  color: var(--pm-sidebar-item-active-color);}/* ── Collapsed nav items ── */.sidebarCollapsed .navItem {  width: 44px;  height: 44px;  padding: 0;  justify-content: center;  border-radius: 12px;  border-left: none;  gap: 0;}.sidebarCollapsed .navItem:hover {  transform: scale(1.06);}.sidebarCollapsed .navItemActive {  border-left: none;  border-bottom: 2.5px solid var(--pm-sidebar-item-active-border);}/* ── Tooltip (collapsed mode) ── */.navItem::after {  content: attr(data-tooltip);  position: absolute;  left: calc(100% + 10px);  top: 50%;  transform: translateY(-50%);  background: var(--pm-dropdown-bg);  color: var(--pm-text-primary);  font-family: var(--font-primary);  font-weight: 500;  font-size: 12px;  padding: 6px 12px;  border-radius: 8px;  white-space: nowrap;  opacity: 0;  pointer-events: none;  transition: opacity 0.15s ease;  z-index: 100;  box-shadow: var(--pm-dropdown-shadow);}.navItem:hover::after {  opacity: 1;}.navItem:not([data-tooltip])::after {  display: none;}/* ── Nav icon ── */.navIcon {  display: flex;  align-items: center;  justify-content: center;  width: 18px;  height: 18px;  flex-shrink: 0;  opacity: var(--pm-sidebar-icon-opacity);  transition: opacity 0.15s ease;}.navItem:hover .navIcon {  opacity: 0.85;}.navItemActive .navIcon {  opacity: var(--pm-sidebar-icon-active-opacity);}.sidebarCollapsed .navIcon {  width: 20px;  height: 20px;}.navLabel {  flex: 1;}/* ── Bottom section ── */.bottom {  flex-shrink: 0;  padding: 8px 10px 12px;  border-top: 1px solid var(--pm-sidebar-border);  display: flex;  flex-direction: column;  gap: 2px;  position: relative;}.sidebarCollapsed .bottom {  padding: 8px 8px 12px;  align-items: center;}/* ── Theme toggle button ── */.themeBtn {  display: flex;  align-items: center;  gap: 12px;  width: 100%;  padding: 9px 12px;  border-radius: 10px;  border: none;  background: transparent;  color: var(--pm-sidebar-item-color);  cursor: pointer;  font-family: var(--font-primary);  font-size: 13px;  font-weight: 500;  white-space: nowrap;  text-align: left;  transition: all 0.2s ease;  position: relative;}.themeBtn:hover {  background: var(--pm-sidebar-item-hover-bg);  color: var(--pm-sidebar-item-hover-color);}.sidebarCollapsed .themeBtn {  width: 44px;  height: 44px;  padding: 0;  justify-content: center;  border-radius: 12px;}.themeBtn::after {  content: attr(data-tooltip);  position: absolute;  left: calc(100% + 10px);  top: 50%;  transform: translateY(-50%);  background: var(--pm-dropdown-bg);  color: var(--pm-text-primary);  font-family: var(--font-primary);  font-weight: 500;  font-size: 12px;  padding: 6px 12px;  border-radius: 8px;  white-space: nowrap;  opacity: 0;  pointer-events: none;  transition: opacity 0.15s ease;  z-index: 100;  box-shadow: var(--pm-dropdown-shadow);}.themeBtn:hover::after {  opacity: 1;}.themeBtn:not([data-tooltip])::after {  display: none;}.themeBtnIcon {  display: flex;  align-items: center;  justify-content: center;  flex-shrink: 0;}/* ── User button ── */.userBtn {  display: flex;  align-items: center;  gap: 10px;  width: 100%;  padding: 8px 12px;  border-radius: 10px;  border: none;  background: transparent;  cursor: pointer;  text-align: left;  transition: all 0.2s ease;  position: relative;}.userBtn:hover {  background: var(--pm-sidebar-item-hover-bg);}.sidebarCollapsed .userBtn {  width: 44px;  height: 44px;  padding: 0;  justify-content: center;  border-radius: 12px;}.avatar {  width: 32px;  height: 32px;  border-radius: 50%;  object-fit: cover;  flex-shrink: 0;  display: flex;  align-items: center;  justify-content: center;  background: var(--pm-avatar-gradient);  color: #ffffff;  font-size: 12px;  font-weight: 600;  font-family: var(--font-primary);  border: 2px solid var(--pm-avatar-border);}.sidebarCollapsed .avatar {  width: 34px;  height: 34px;}.userName {  font-family: var(--font-primary);  font-size: 13px;  font-weight: 600;  color: var(--pm-text-primary);  line-height: 1.3;  overflow: hidden;  text-overflow: ellipsis;  white-space: nowrap;  flex: 1;  min-width: 0;}.userChevron {  margin-left: auto;  flex-shrink: 0;  opacity: 0.5;  color: var(--pm-sidebar-item-color);}.onlineDot {  position: absolute;  bottom: 10px;  left: 36px;  width: 9px;  height: 9px;  border-radius: 50%;  background: #10b981;  border: 2px solid var(--pm-online-dot-border);}.sidebarCollapsed .onlineDot {  left: 30px;  bottom: 8px;}/* ── Profile popup menu ── */.profileMenu {  position: fixed;  left: 258px;  bottom: 16px;  background: var(--pm-profile-menu-bg);  border-radius: 12px;  padding: 6px;  box-shadow: var(--pm-profile-menu-shadow);  border: 1px solid var(--pm-dropdown-border);  z-index: 9999;  min-width: 180px;  display: flex;  flex-direction: column;  gap: 2px;}.sidebarCollapsed .profileMenu {  left: 68px;}.profileHeader {  padding: 10px 14px 6px;  display: flex;  flex-direction: column;  gap: 2px;}.profileName {  font-family: var(--font-primary);  font-size: 14px;  font-weight: 600;  color: var(--pm-text-primary);}.profileRole {  font-family: var(--font-primary);  font-size: 11px;  font-weight: 500;  color: var(--pm-text-secondary);  text-transform: capitalize;}.profileDivider {  height: 1px;  background: var(--pm-profile-divider);  margin: 4px 10px;}.profileItem {  display: flex;  align-items: center;  gap: 10px;  padding: 10px 14px;  border-radius: 8px;  font-family: var(--font-primary);  font-size: 13px;  font-weight: 500;  color: var(--pm-text-primary);  background: transparent;  border: none;  cursor: pointer;  white-space: nowrap;  text-align: left;  width: 100%;  transition: all 0.1s ease;}.profileItem:hover {  background: var(--pm-dropdown-item-hover);}.profileItemDanger:hover {  background: var(--pm-btn-danger-bg);  color: var(--pm-accent-red);}/* ── Mobile overlay ── */.overlay {  display: none;  position: fixed;  inset: 0;  background: rgba(0, 0, 0, 0.4);  z-index: 999;}@media (max-width: 768px) {  .overlay {    display: block;  }  .sidebar {    position: fixed;    left: 0;    top: 0;    bottom: 0;    width: 220px;    z-index: 1000;    transform: translateX(-100%);    transition: transform 0.3s ease, visibility 0.3s ease;    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);    visibility: hidden;  }  .sidebarCollapsed {    width: 220px;  }  .sidebarMobileOpen {    transform: translateX(0);    visibility: visible;  }  .collapseBtn {    display: none;  }  .navItem::after {    display: none;  }  .themeBtn::after {    display: none;  }  .profileMenu {    position: fixed;    left: 228px;    bottom: 20px;  }}
```

---

-    **Step 5: Create DashboardHeader component**

`frontend/src/components/DashboardHeader.tsx`:

```tsx
import { useNavigate } from "react-router-dom";import { useAuth } from "../context/AuthContext";import styles from "./DashboardHeader.module.css";interface DashboardHeaderProps {  title?: string;  subtitle?: string;}function LogoutIcon() {  return (    <svg      width="16"      height="16"      viewBox="0 0 24 24"      fill="none"      stroke="currentColor"      strokeWidth="1.5"      strokeLinecap="round"      strokeLinejoin="round"    >      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />      <path d="M16 17l5-5-5-5M21 12H9" />    </svg>  );}export default function DashboardHeader({  title,  subtitle,}: DashboardHeaderProps) {  const { user, logout } = useAuth();  const navigate = useNavigate();  const handleLogout = async () => {    await logout();    navigate("/login");  };  return (    <header className={styles.header}>      <div className={styles.titleBlock}>        <h1 className={styles.title}>          {title || (            <>              Coach              <span style={{ color: "var(--pm-accent-gold)", fontWeight: 800 }}>                Portal              </span>            </>          )}        </h1>        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}      </div>      <div className={styles.actions}>        <div className={styles.userInfo}>          <span className={styles.userName}>{user?.username || "User"}</span>          <span className={styles.userRole}>{user?.role || "coach"}</span>        </div>        <button          className={styles.logoutBtn}          onClick={handleLogout}          type="button"          title="Logout"        >          <LogoutIcon />          <span>Logout</span>        </button>      </div>    </header>  );}
```

`frontend/src/components/DashboardHeader.module.css`:

```css
/* ══════════════════════════════════════════════════   DashboardHeader — Coach-Client (PentEdge pattern)   ══════════════════════════════════════════════════ */.header {  display: flex;  align-items: center;  justify-content: space-between;  gap: 24px;  width: 100%;}.titleBlock {  display: flex;  flex-direction: column;  gap: 2px;  min-width: 0;}.title {  font-family: var(--font-primary);  font-weight: 700;  font-size: 18px;  color: var(--pm-text-primary);  margin: 0;  letter-spacing: -0.01em;  line-height: 1.2;}.subtitle {  font-family: var(--font-primary);  font-weight: 400;  font-size: 13px;  color: var(--pm-text-secondary);  margin: 0;  line-height: 1.2;}.actions {  display: flex;  align-items: center;  gap: 16px;  flex-shrink: 0;  margin-left: auto;}.userInfo {  display: flex;  flex-direction: column;  align-items: flex-end;  gap: 1px;}.userName {  font-family: var(--font-primary);  font-size: 13px;  font-weight: 600;  color: var(--pm-text-primary);  line-height: 1.2;}.userRole {  font-family: var(--font-primary);  font-size: 11px;  font-weight: 500;  color: var(--pm-text-secondary);  text-transform: capitalize;}.logoutBtn {  display: flex;  align-items: center;  gap: 6px;  padding: 8px 14px;  border-radius: var(--radius-md);  border: 1px solid var(--pm-border);  background: var(--pm-card-bg);  color: var(--pm-text-secondary);  font-family: var(--font-primary);  font-size: 13px;  font-weight: 500;  cursor: pointer;  transition: all 0.2s ease;  white-space: nowrap;}.logoutBtn:hover {  background: var(--pm-btn-danger-bg);  color: var(--pm-accent-red);  border-color: var(--pm-accent-red);}@media (max-width: 768px) {  .header {    flex-wrap: wrap;    gap: 10px;  }  .titleBlock {    flex: 1 1 100%;    order: 2;  }  .actions {    order: 1;    margin-left: auto;    gap: 10px;  }}@media (max-width: 480px) {  .title {    font-size: 16px;  }  .subtitle {    font-size: 12px;  }  .logoutBtn span {    display: none;  }}
```

---

-    **Step 6: Import variables.css in index.css**

Prepend to `frontend/src/index.css`:

```css
@import "./styles/variables.css";@import "tailwindcss";
```

---

-    **Step 7: Update App.tsx to use CrmLayout with Outlet routing**

Replace the `<Navbar />` + flat `<Routes>` approach in `App.jsx` (now `App.tsx`) with nested routing through `CrmLayout`:

`frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";import { AuthProvider, useAuth } from "./context/AuthContext";import { ThemeProvider } from "./context/ThemeContext";import ProtectedRoute from "./components/ProtectedRoute";import CrmLayout from "./components/CrmLayout";import LoginPage from "./pages/LoginPage";import CoachDashboard from "./pages/CoachDashboard";import AdminDashboard from "./pages/AdminDashboard";import AuditTrailPage from "./pages/AuditTrailPage";import BriefsPage from "./pages/BriefsPage";import SourceEditorPage from "./pages/SourceEditorPage";function AppRoutes() {  const { user, loading } = useAuth();  if (loading) return <div style={{ padding: 32, textAlign: "center" }}>Loading...</div>;  return (    <Routes>      <Route path="/login" element={<LoginPage />} />      <Route        element={          <ProtectedRoute>            <CrmLayout />          </ProtectedRoute>        }      >        <Route          index          element={            user?.role === "admin" ? <AdminDashboard /> : <CoachDashboard />          }        />        <Route path="dashboard" element={<CoachDashboard />} />        <Route          path="admin"          element={            <ProtectedRoute adminOnly>              <AdminDashboard />            </ProtectedRoute>          }        />        <Route          path="audit"          element={            <ProtectedRoute adminOnly>              <AuditTrailPage />            </ProtectedRoute>          }        />        <Route path="briefs" element={<BriefsPage />} />        <Route          path="source"          element={            <ProtectedRoute adminOnly>              <SourceEditorPage />            </ProtectedRoute>          }        />      </Route>      <Route path="*" element={<Navigate to="/" />} />    </Routes>  );}export default function App() {  return (    <BrowserRouter>      <AuthProvider>        <ThemeProvider>          <AppRoutes />        </ThemeProvider>      </AuthProvider>    </BrowserRouter>  );}
```

---

-    **Step 8: Verify TypeScript compiles**

```bash
cd frontendnpx tsc --noEmit
```

Fix any unused imports or type errors before proceeding.

---

-    **Step 9: Commit**

```bash
git add frontend/src/styles/variables.css         frontend/src/context/ThemeContext.tsx         frontend/src/components/CrmLayout.tsx         frontend/src/components/CrmLayout.module.css         frontend/src/components/Sidebar.tsx         frontend/src/components/Sidebar.module.css         frontend/src/components/DashboardHeader.tsx         frontend/src/components/DashboardHeader.module.css         frontend/src/App.tsx         frontend/src/index.cssgit commit -m "feat: add layout shell with collapsible sidebar, header, and dark mode (PentEdge pattern)"
```

---

## Task 12: Coach Dashboard Page

**Files:**

-   Create: `frontend/src/pages/CoachDashboard.tsx`
    
-   Create: `frontend/src/pages/CoachDashboard.module.css`
    
-   Create: `frontend/src/components/StatCard.tsx`
    
-   Create: `frontend/src/components/StatCard.module.css`
    
-    **Step 1: Create `frontend/src/components/StatCard.module.css`**
    

```css
/* ═══════════════════════════════════   StatCard — PentEdge-style KPI card   ═══════════════════════════════════ */.card {  background: var(--pm-card-bg);  border-radius: var(--radius-card, 14px);  padding: 20px;  display: flex;  flex-direction: column;  gap: 12px;  height: auto;  flex: 1;  box-sizing: border-box;  border: 1px solid var(--pm-border-light);  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);}.card:hover {  transform: translateY(-2px);  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);  border-color: var(--pm-border);}.topRow {  display: flex;  align-items: center;  justify-content: space-between;  width: 100%;}.iconTitle {  display: flex;  align-items: center;  gap: 16px;}.iconCircle {  width: 40px;  height: 40px;  border-radius: 10px;  display: flex;  align-items: center;  justify-content: center;  flex-shrink: 0;}.iconCircle svg {  width: 22px;  height: 22px;}.title {  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 15px;  color: var(--pm-text-primary);  margin: 0;}.valueRow {  display: flex;  align-items: flex-end;  gap: 8px;}.value {  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 700;  font-size: 28px;  color: var(--pm-text-primary);  margin: 0;  line-height: 1;  letter-spacing: -0.02em;}.subtitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 12px;  color: var(--pm-text-muted);  margin: 0;  padding-bottom: 4px;}
```

-    **Step 2: Create `frontend/src/components/StatCard.tsx`**

```tsx
import styles from './StatCard.module.css';/* ── Inline SVG icons ── */function AccountsIcon() {  return (    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>    </svg>  );}function ClientsIcon() {  return (    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>    </svg>  );}const iconMap: Record<string, React.FC> = {  accounts: AccountsIcon,  clients: ClientsIcon,};export interface StatCardData {  icon: string;  title: string;  value: number | string;  subtitle?: string;  color: string;  bg: string;}export default function StatCard({ data }: { data: StatCardData }) {  const Icon = iconMap[data.icon] || AccountsIcon;  return (    <div className={styles.card}>      <div className={styles.topRow}>        <div className={styles.iconTitle}>          <div            className={styles.iconCircle}            style={{ background: data.bg, color: data.color }}          >            <Icon />          </div>          <p className={styles.title}>{data.title}</p>        </div>      </div>      <div className={styles.valueRow}>        <p className={styles.value} style={{ color: data.color }}>          {data.value}        </p>        {data.subtitle && <p className={styles.subtitle}>{data.subtitle}</p>}      </div>    </div>  );}
```

-    **Step 3: Create `frontend/src/pages/CoachDashboard.module.css`**

```css
/* ═══════════════════════════════════════════════════════   Coach Dashboard – PentEdge-style layout   CSS-variable driven (--pm-*) with animated cards & charts   ═══════════════════════════════════════════════════════ */@keyframes fadeInUp {  from { opacity: 0; transform: translateY(16px); }  to   { opacity: 1; transform: translateY(0); }}@keyframes shimmer {  0%   { background-position: -200% 0; }  100% { background-position: 200% 0; }}@keyframes spinOuter {  to { transform: rotate(360deg); }}/* ── Dashboard Container ── */.dashboard {  display: flex;  flex-direction: column;  gap: 24px;  padding: 0 0 48px;  overflow-y: auto;  flex: 1;  min-height: 0;}.dashboard::-webkit-scrollbar { width: 5px; }.dashboard::-webkit-scrollbar-track { background: transparent; }.dashboard::-webkit-scrollbar-thumb { background: var(--pm-border); border-radius: 10px; }.dashboard::-webkit-scrollbar-thumb:hover { background: var(--pm-text-muted); }/* ── Loading ── */.loadingContainer {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  min-height: 400px;  gap: 16px;  flex: 1;}.spinnerOuter {  width: 48px;  height: 48px;  border-radius: 50%;  border: 3px solid var(--pm-border-light);  border-top-color: var(--pm-accent-primary);  animation: spinOuter 0.8s linear infinite;}.loadingText {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 14px;  font-weight: 500;  color: var(--pm-text-muted);}.shimmerBlock {  display: inline-block;  width: 60px;  height: 1em;  border-radius: 4px;  background: linear-gradient(90deg, var(--pm-border-light) 25%, var(--pm-content-bg) 50%, var(--pm-border-light) 75%);  background-size: 200% 100%;  animation: shimmer 1.5s ease-in-out infinite;  vertical-align: middle;}/* ═══════════════════════════════════   Welcome Header   ═══════════════════════════════════ */.welcomeRow {  display: flex;  align-items: center;  justify-content: space-between;  gap: 16px;  animation: fadeInUp 0.4s ease-out;}.welcomeBlock {  display: flex;  flex-direction: column;  gap: 2px;}.welcomeTitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 22px;  font-weight: 700;  color: var(--pm-text-primary);  margin: 0;  line-height: 1.3;}.welcomeSubtitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  font-weight: 500;  color: var(--pm-text-muted);  margin: 0;  line-height: 1.3;}/* ═══════════════════════════════════   Stat Cards Grid (2 cards)   ═══════════════════════════════════ */.statsGrid {  display: grid;  grid-template-columns: repeat(2, 1fr);  gap: 16px;  animation: fadeInUp 0.5s ease-out 0.1s both;}/* ═══════════════════════════════════   Charts Row (bar chart)   ═══════════════════════════════════ */.chartsRow {  display: grid;  grid-template-columns: 1fr;  gap: 16px;  animation: fadeInUp 0.5s ease-out 0.12s both;}.card {  background: var(--pm-card-bg);  border-radius: 14px;  border: 1px solid var(--pm-border-light);  padding: 24px;  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);}.card:hover {  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);}.cardHeader {  display: flex;  align-items: flex-start;  justify-content: space-between;  margin-bottom: 20px;}.cardTitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 16px;  font-weight: 700;  color: var(--pm-text-primary);}.cardSubtitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 12px;  color: var(--pm-text-muted);  margin-top: 2px;}.chartWrapper {  width: 100%;  height: 300px;}.chartPlaceholder {  width: 100%;  height: 100%;  display: flex;  align-items: center;  justify-content: center;}/* ═══════════════════════════════════   Tooltip (Recharts)   ═══════════════════════════════════ */.tooltip {  background: var(--pm-card-bg);  border: 1px solid var(--pm-border-light);  border-radius: 10px;  padding: 12px 16px;  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  color: var(--pm-text-muted);  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);}.tooltipLabel {  font-weight: 700;  color: var(--pm-text-primary);  margin-bottom: 6px;}.tooltipRow {  display: flex;  align-items: center;  gap: 8px;  margin-top: 4px;}.tooltipDot {  width: 8px;  height: 8px;  border-radius: 3px;  flex-shrink: 0;}/* ═══════════════════════════════════   Coach Section (Admin overview)   ═══════════════════════════════════ */.coachSection {  background: var(--pm-card-bg);  border-radius: 14px;  border: 1px solid var(--pm-border-light);  padding: 24px;  animation: fadeInUp 0.5s ease-out;  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);}.coachSection:hover {  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);}.coachHeader {  display: flex;  align-items: center;  justify-content: space-between;  margin-bottom: 16px;  padding-bottom: 12px;  border-bottom: 1px solid var(--pm-border-light);}.coachName {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 18px;  font-weight: 700;  color: var(--pm-text-primary);  margin: 0;}.coachEmail {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 12px;  color: var(--pm-text-muted);  margin: 2px 0 0;}.coachMeta {  display: flex;  gap: 16px;  align-items: center;}.coachMetaItem {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  font-weight: 600;  color: var(--pm-text-muted);  display: flex;  align-items: center;  gap: 4px;}.coachMetaValue {  color: var(--pm-text-primary);  font-weight: 700;}/* ═══════════════════════════════════   Account Cards Grid   ═══════════════════════════════════ */.accountsGrid {  display: grid;  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));  gap: 16px;}.accountCard {  background: var(--pm-card-bg);  border-radius: 12px;  border: 1px solid var(--pm-border-light);  padding: 18px;  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);}.accountCard:hover {  transform: translateY(-2px);  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);  border-color: var(--pm-border);}.accountCardHeader {  display: flex;  align-items: center;  justify-content: space-between;  margin-bottom: 12px;}.accountName {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 15px;  font-weight: 700;  color: var(--pm-text-primary);  margin: 0;}.industryBadge {  display: inline-flex;  align-items: center;  padding: 3px 10px;  border-radius: 20px;  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 11px;  font-weight: 600;  letter-spacing: 0.3px;  background: var(--pm-accent-primary-bg);  color: var(--pm-accent-primary);  white-space: nowrap;}.accountMeta {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 12px;  color: var(--pm-text-muted);  margin-bottom: 12px;}.contactsList {  display: flex;  flex-direction: column;  gap: 8px;}.contactItem {  display: flex;  flex-direction: column;  gap: 2px;  padding: 10px 12px;  background: var(--pm-content-bg);  border-radius: 8px;  border: 1px solid var(--pm-border-light);}.contactName {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  font-weight: 600;  color: var(--pm-text-primary);}.contactTitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 12px;  color: var(--pm-text-muted);}.contactEmail {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 11px;  color: var(--pm-text-grey);}/* ═══════════════════════════════════   Empty state   ═══════════════════════════════════ */.emptyState {  text-align: center;  padding: 48px 24px;  color: var(--pm-text-muted);  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 15px;  font-weight: 500;}/* ═══════════════════════════════════   Responsive   ═══════════════════════════════════ */@media (max-width: 1200px) {  .statsGrid { grid-template-columns: 1fr 1fr; }  .accountsGrid { grid-template-columns: 1fr; }}@media (max-width: 768px) {  .statsGrid { grid-template-columns: 1fr; }  .welcomeRow { flex-direction: column; align-items: flex-start; }  .coachHeader { flex-direction: column; align-items: flex-start; gap: 8px; }  .coachMeta { flex-wrap: wrap; }  .accountsGrid { grid-template-columns: 1fr; }}@media (max-width: 480px) {  .dashboard { gap: 16px; }  .coachSection { padding: 16px; }  .accountCard { padding: 14px; }  .chartWrapper { height: 220px; }}
```

-    **Step 4: Create `frontend/src/pages/CoachDashboard.tsx`**

```tsx
import { useState, useEffect } from 'react';import {  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,  ResponsiveContainer,} from 'recharts';import api from '../api/client';import { useAuth } from '../context/AuthContext';import StatCard from '../components/StatCard';import type { StatCardData } from '../components/StatCard';import styles from './CoachDashboard.module.css';/* ── Types matching backend DashboardSerializer ── */interface Contact {  id: number;  sf_id: string;  name: string;  title: string;  phone: string;  email: string;  account_id: number;  coach_id: number;  coach_name: string;}interface Account {  id: number;  sf_id: string;  name: string;  industry: string;  website: string;  coaching_start_date: string;  coach_id: number;  coach_name: string;  contacts: Contact[];}interface Coach {  id: number;  sf_id: string;  name: string;  email: string;  active_clients: number;  is_active: boolean;}interface DashboardEntry {  coach: Coach;  accounts: Account[];  total_accounts: number;  total_clients: number;}/* ── Custom chart tooltip ── */function ChartTooltip({ active, payload, label }: any) {  if (!active || !payload?.length) return null;  return (    <div className={styles.tooltip}>      <div className={styles.tooltipLabel}>{label}</div>      {payload.map((p: any, i: number) => (        <div key={i} className={styles.tooltipRow}>          <span            className={styles.tooltipDot}            style={{ background: p.color || p.fill }}          />          <span>            {p.name}: {p.value}          </span>        </div>      ))}    </div>  );}/* ── Build bar-chart data: clients per account ── */function buildChartData(accounts: Account[]) {  return accounts.map((a) => ({    name: a.name.length > 18 ? a.name.slice(0, 16) + '...' : a.name,    Clients: a.contacts.length,  }));}/* ── Bar gradient colors ── */const BAR_COLORS = {  gridStroke: 'var(--pm-border-light)',  axisTick: 'var(--pm-text-muted)',  gradientStart: '#3B82F6',  gradientEnd: '#2563EB',  cursorFill: 'rgba(59, 130, 246, 0.04)',};export default function CoachDashboard() {  const { user } = useAuth();  const [data, setData] = useState<DashboardEntry[] | null>(null);  const [loading, setLoading] = useState(true);  useEffect(() => {    api      .get('/coaching/dashboard/')      .then((res) => {        // Admin gets an array; coach gets a single object        const payload = Array.isArray(res.data) ? res.data : [res.data];        setData(payload);      })      .catch(console.error)      .finally(() => setLoading(false));  }, []);  const isAdmin = user?.role === 'admin';  const userName = user?.name?.split(' ')[0] || 'there';  /* ── Loading state ── */  if (loading) {    return (      <div className={styles.loadingContainer}>        <div className={styles.spinnerOuter} />        <span className={styles.loadingText}>Loading dashboard...</span>      </div>    );  }  /* ── Empty / error state ── */  if (!data || data.length === 0) {    return (      <div className={styles.emptyState}>        No data available. Run a sync first.      </div>    );  }  /* ── Aggregate totals (for admin: across all coaches; for coach: their own) ── */  const grandTotalAccounts = data.reduce((s, d) => s + d.total_accounts, 0);  const grandTotalClients = data.reduce((s, d) => s + d.total_clients, 0);  /* ── Aggregate chart data across all visible coaches ── */  const allAccounts = data.flatMap((d) => d.accounts);  const chartData = buildChartData(allAccounts);  const statCards: StatCardData[] = [    {      icon: 'accounts',      title: 'Total Accounts',      value: grandTotalAccounts,      subtitle: isAdmin ? `across ${data.length} coaches` : undefined,      color: '#3B82F6',      bg: 'rgba(59, 130, 246, 0.1)',    },    {      icon: 'clients',      title: 'Total Clients',      value: grandTotalClients,      subtitle: isAdmin ? 'all active contacts' : undefined,      color: '#10B981',      bg: 'rgba(16, 185, 129, 0.1)',    },  ];  return (    <div className={styles.dashboard}>      {/* ── Welcome Header ── */}      <div className={styles.welcomeRow}>        <div className={styles.welcomeBlock}>          <h1 className={styles.welcomeTitle}>            {isAdmin ? 'All Coaches Overview' : `Welcome back, ${userName}`}          </h1>          <p className={styles.welcomeSubtitle}>            {isAdmin              ? `${data.length} active coach${data.length !== 1 ? 'es' : ''} with ${grandTotalAccounts} accounts`              : `${grandTotalAccounts} accounts, ${grandTotalClients} clients`}          </p>        </div>      </div>      {/* ── Stat Cards ── */}      <div className={styles.statsGrid}>        {statCards.map((s, i) => (          <StatCard key={i} data={s} />        ))}      </div>      {/* ── Clients per Account Bar Chart ── */}      {chartData.length > 0 && (        <div className={styles.chartsRow}>          <div className={styles.card}>            <div className={styles.cardHeader}>              <div>                <div className={styles.cardTitle}>Clients per Account</div>                <div className={styles.cardSubtitle}>                  {allAccounts.length} account{allAccounts.length !== 1 ? 's' : ''} &middot;{' '}                  {grandTotalClients} total clients                </div>              </div>            </div>            <div className={styles.chartWrapper}>              <ResponsiveContainer width="100%" height="100%">                <BarChart                  data={chartData}                  margin={{ top: 10, right: 20, left: 0, bottom: 0 }}                >                  <defs>                    <linearGradient id="barCoach" x1="0" y1="0" x2="0" y2="1">                      <stop offset="0%" stopColor={BAR_COLORS.gradientStart} stopOpacity={1} />                      <stop offset="100%" stopColor={BAR_COLORS.gradientEnd} stopOpacity={0.8} />                    </linearGradient>                  </defs>                  <CartesianGrid                    strokeDasharray="3 3"                    stroke={BAR_COLORS.gridStroke}                    vertical={false}                  />                  <XAxis                    dataKey="name"                    tick={{ fill: BAR_COLORS.axisTick, fontSize: 12 }}                    axisLine={false}                    tickLine={false}                  />                  <YAxis                    tick={{ fill: BAR_COLORS.axisTick, fontSize: 12 }}                    axisLine={false}                    tickLine={false}                    allowDecimals={false}                  />                  <Tooltip                    content={<ChartTooltip />}                    cursor={{ fill: BAR_COLORS.cursorFill }}                  />                  <Bar                    dataKey="Clients"                    name="Clients"                    fill="url(#barCoach)"                    radius={[4, 4, 0, 0]}                    barSize={32}                  />                </BarChart>              </ResponsiveContainer>            </div>          </div>        </div>      )}      {/* ── Coach Sections with Account Cards ── */}      {data.map((entry) => (        <div key={entry.coach.id} className={styles.coachSection}>          {/* Coach header (shown always for admin, simplified for coach) */}          <div className={styles.coachHeader}>            <div>              <h2 className={styles.coachName}>{entry.coach.name}</h2>              {isAdmin && (                <p className={styles.coachEmail}>{entry.coach.email}</p>              )}            </div>            <div className={styles.coachMeta}>              <span className={styles.coachMetaItem}>                Accounts: <span className={styles.coachMetaValue}>{entry.total_accounts}</span>              </span>              <span className={styles.coachMetaItem}>                Clients: <span className={styles.coachMetaValue}>{entry.total_clients}</span>              </span>            </div>          </div>          {/* Account Cards */}          {entry.accounts.length === 0 ? (            <div className={styles.emptyState}>No accounts assigned</div>          ) : (            <div className={styles.accountsGrid}>              {entry.accounts.map((account) => (                <div key={account.id} className={styles.accountCard}>                  <div className={styles.accountCardHeader}>                    <h3 className={styles.accountName}>{account.name}</h3>                    <span className={styles.industryBadge}>{account.industry}</span>                  </div>                  {account.website && (                    <div className={styles.accountMeta}>{account.website}</div>                  )}                  {account.contacts.length === 0 ? (                    <div className={styles.accountMeta}>No contacts</div>                  ) : (                    <div className={styles.contactsList}>                      {account.contacts.map((contact) => (                        <div key={contact.id} className={styles.contactItem}>                          <span className={styles.contactName}>{contact.name}</span>                          <span className={styles.contactTitle}>{contact.title}</span>                          <span className={styles.contactEmail}>{contact.email}</span>                        </div>                      ))}                    </div>                  )}                </div>              ))}            </div>          )}        </div>      ))}    </div>  );}
```

-    **Step 5: Install Recharts dependency (if not already installed)**

```bash
cd frontendnpm install recharts
```

-    **Step 6: Verify TypeScript compiles**

```bash
cd frontendnpx tsc --noEmit
```

Fix any type errors before proceeding.

-    **Step 7: Commit**

```bash
git add frontend/src/components/StatCard.tsx frontend/src/components/StatCard.module.css frontend/src/pages/CoachDashboard.tsx frontend/src/pages/CoachDashboard.module.cssgit commit -m "feat: add coach dashboard with StatCards, account cards, and Recharts bar chart"
```

---

That is the complete updated Task 12. Key design decisions:

1.  **StatCard** (`/frontend/src/components/StatCard.tsx` + `.module.css`) follows the PentEdge pattern: icon circle with configurable color/bg, title, large value, optional subtitle. Uses `--pm-*` CSS variables throughout.
    
2.  **CoachDashboard** (`/frontend/src/pages/CoachDashboard.tsx` + `.module.css`) mirrors PentEdge's `DashboardContent` layout:
    
    -   Welcome header row at top
    -   `statsGrid` (2-column grid) for the two StatCards (Total Accounts, Total Clients)
    -   `chartsRow` with a Recharts `BarChart` showing clients-per-account
    -   Coach sections with account cards containing industry badges and contact lists
    -   Admin sees all coaches' data in separate sections; coach sees only their own
3.  All colors reference `var(--pm-*)` variables. Card styling (border-radius 14px, hover lift, border-light borders) matches PentEdge's `.card`, `.bdMetricCard`, and `.funnelSection` patterns. Responsive breakpoints at 1200px, 768px, and 480px mirror PentEdge's media queries.
    

---

## Task 13: Admin Dashboard Page

**Files:**

-   Create: `frontend/src/pages/AdminDashboard.tsx`
-   Create: `frontend/src/pages/AdminDashboard.module.css`
-   Create: `frontend/src/components/StatCard.tsx`
-   Create: `frontend/src/components/StatCard.module.css`

### Prerequisites

-   Task 9 (React Frontend Setup) must be complete — `variables.css` with all `--pm-*` tokens loaded globally
-   Task 6 (Sync Engine) must be complete — API endpoints `GET /api/sync/history/` and `POST /api/sync/trigger/` available
-   `frontend/src/api/client.ts` must export a configured Axios instance

---

-    **Step 1: Create the StatCard component**

`frontend/src/components/StatCard.tsx`:

```tsx
import styles from './StatCard.module.css';interface StatCardProps {  title: string;  value: string | number;  icon: React.ReactNode;}function StatCard({ title, value, icon }: StatCardProps) {  return (    <div className={styles.card}>      <div className={styles.topRow}>        <div className={styles.iconTitle}>          <div className={styles.iconCircle}>{icon}</div>          <p className={styles.title}>{title}</p>        </div>      </div>      <div className={styles.valueRow}>        <p className={styles.value}>{value}</p>      </div>    </div>  );}export default StatCard;
```

-    **Step 2: Create the StatCard CSS module**

`frontend/src/components/StatCard.module.css`:

```css
/* * StatCard styles — mirrors PentEdge-CRM StatCard pattern * Uses --pm-* design tokens from variables.css */.card {  background: var(--pm-card-bg);  border-radius: var(--radius-card, 12px);  padding: 20px;  display: flex;  flex-direction: column;  gap: 12px;  height: auto;  flex: 1;  box-sizing: border-box;  border: 1px solid var(--pm-border);}.topRow {  display: flex;  align-items: center;  justify-content: space-between;  width: 100%;}.iconTitle {  display: flex;  align-items: center;  gap: 16px;}.iconCircle {  width: 36px;  height: 36px;  border-radius: 50%;  background: var(--pm-bar-light);  display: flex;  align-items: center;  justify-content: center;  flex-shrink: 0;}.title {  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 15px;  color: var(--pm-text-primary);  margin: 0;}.valueRow {  display: flex;  align-items: flex-end;  gap: 8px;}.value {  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 27px;  color: var(--pm-text-primary);  margin: 0;  line-height: 1;}
```

-    **Step 3: Create the AdminDashboard CSS module**

`frontend/src/pages/AdminDashboard.module.css`:

```css
/* * Admin Dashboard page styles * Follows PentEdge-CRM page layout (pages.module.css) + table (tables.module.css) patterns * All colors via --pm-* design tokens *//* ── Page Wrapper ── */.wrapper {  display: flex;  flex-direction: column;  gap: 0;  flex: 1;  min-height: 0;  height: 100%;  padding: 24px;}.pageTitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 22px;  font-weight: 600;  color: var(--pm-text-primary);  margin: 0 0 20px 0;}/* ── Stat Cards Row ── */.statsRow {  display: flex;  gap: 16px;  margin-bottom: 20px;  flex-shrink: 0;}/* ── Toolbar (Sync Controls) ── */.toolbar {  display: flex;  align-items: center;  justify-content: space-between;  gap: 16px;  flex-shrink: 0;  margin-bottom: 0;}.toolbarLeft {  display: flex;  align-items: center;  gap: 12px;}.toolbarRight {  display: flex;  align-items: center;  gap: 10px;}.sectionTitle {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 16px;  font-weight: 600;  color: var(--pm-text-primary);  margin: 0;}/* ── Primary Button (matches PentEdge .createBtn) ── */.syncBtn {  padding: 9px 20px;  border-radius: var(--radius-lg, 10px);  background: var(--pm-accent-primary);  color: var(--pm-text-on-accent);  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 14px;  cursor: pointer;  white-space: nowrap;  border: none;  transition: background 0.15s ease;}.syncBtn:hover:not(:disabled) {  background: var(--pm-accent-primary-hover);}.syncBtn:disabled {  opacity: 0.5;  cursor: not-allowed;}/* ── Status Message ── */.statusMessage {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  font-weight: 500;  padding: 6px 14px;  border-radius: var(--radius-md, 8px);}.statusSuccess {  background: var(--pm-accent-green-bg);  color: var(--pm-accent-green);}.statusError {  background: var(--pm-accent-red-bg);  color: var(--pm-accent-red);}/* ── Table Wrapper (matches PentEdge .tableWrap) ── */.tableWrap {  flex: 1;  min-height: 0;  overflow: auto;  background: var(--pm-card-bg);  border-radius: var(--radius-xl, 12px);  border: 1px solid var(--pm-border);  margin-top: 6px;}.table {  min-width: 100%;  border-collapse: collapse;  table-layout: auto;}/* ── Header Cells (matches PentEdge .th) ── */.th {  position: sticky;  top: 0;  z-index: 10;  background: var(--pm-table-header-bg);  padding: 10px 12px;  text-align: left;  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 14px;  color: var(--pm-table-header-color);  white-space: nowrap;  user-select: none;  border-bottom: 1px solid var(--pm-table-border);  min-width: 120px;}/* ── Rows (matches PentEdge .tr) ── */.tr {  border-bottom: 1px solid var(--pm-table-border);  transition: background 0.15s ease;}.tr:last-child {  border-bottom: none;}.tr:hover {  background: var(--pm-table-row-hover);}/* ── Data Cells (matches PentEdge .td) ── */.td {  padding: 8px 12px;  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 13px;  color: var(--pm-text-primary);  white-space: nowrap;  min-width: 120px;  max-width: 200px;  overflow: hidden;  text-overflow: ellipsis;}/* ── Status Badges (matches PentEdge .badge pattern) ── */.badge {  display: inline-block;  padding: 4px 12px;  border-radius: var(--radius-full, 999px);  font-family: var(--font-primary, 'Inter', sans-serif);  font-weight: 500;  font-size: 12px;  text-transform: capitalize;}.badgeCompleted {  background: var(--pm-accent-green-bg);  color: var(--pm-accent-green);}.badgeFailed {  background: var(--pm-accent-red-bg);  color: var(--pm-accent-red);}.badgeInProgress {  background: var(--pm-accent-orange-bg);  color: var(--pm-accent-orange);}/* ── Empty State (matches PentEdge .empty) ── */.empty {  text-align: center;  padding: 60px 14px;  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 14px;  color: var(--pm-text-muted);}/* ── Loading Spinner (matches PentEdge pattern) ── */@keyframes spinOuter {  to {    transform: rotate(360deg);  }}.loadingContainer {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  min-height: 400px;  gap: 16px;  flex: 1;}.spinnerOuter {  width: 48px;  height: 48px;  border-radius: 50%;  border: 3px solid var(--pm-border-light);  border-top-color: var(--pm-accent-primary);  animation: spinOuter 0.8s linear infinite;}.loadingText {  font-family: var(--font-primary, 'Inter', sans-serif);  font-size: 14px;  font-weight: 500;  color: var(--pm-text-muted);}/* ── Responsive ── */@media (max-width: 768px) {  .wrapper {    padding: 16px;  }  .statsRow {    flex-direction: column;  }  .toolbar {    flex-direction: column;    align-items: stretch;    gap: 8px;  }  .toolbarRight {    flex-wrap: wrap;    gap: 6px;  }  .syncBtn {    width: 100%;    text-align: center;  }}
```

-    **Step 4: Write the AdminDashboard page component**

`frontend/src/pages/AdminDashboard.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react';import api from '../api/client';import StatCard from '../components/StatCard';import styles from './AdminDashboard.module.css';/* ── Types ── */interface SyncLogEntry {  id: number;  started_at: string;  completed_at: string | null;  status: 'in_progress' | 'completed' | 'failed';  changes_detected: number;  error_message: string;}/* ── Inline SVG Icons for StatCards ── */function SyncIcon() {  return (    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">      <path d="M23 4v6h-6" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M1 20v-6h6" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>    </svg>  );}function StatusIcon() {  return (    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M22 4L12 14.01l-3-3" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>    </svg>  );}function ChangesIcon() {  return (    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="var(--pm-accent-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>    </svg>  );}/* ── Helpers ── */function getBadgeClass(status: SyncLogEntry['status']): string {  switch (status) {    case 'completed':      return styles.badgeCompleted;    case 'failed':      return styles.badgeFailed;    case 'in_progress':      return styles.badgeInProgress;    default:      return '';  }}function formatDateTime(iso: string): string {  return new Date(iso).toLocaleString();}function formatDuration(start: string, end: string | null): string {  if (!end) return '--';  const ms = new Date(end).getTime() - new Date(start).getTime();  if (ms < 1000) return `${ms}ms`;  return `${(ms / 1000).toFixed(1)}s`;}/* ── Component ── */export default function AdminDashboard() {  const [syncHistory, setSyncHistory] = useState<SyncLogEntry[]>([]);  const [loading, setLoading] = useState(true);  const [syncing, setSyncing] = useState(false);  const [message, setMessage] = useState('');  const [messageType, setMessageType] = useState<'success' | 'error'>('success');  const fetchHistory = useCallback(async () => {    try {      const res = await api.get('/sync/history/');      setSyncHistory(res.data);    } catch {      setSyncHistory([]);    } finally {      setLoading(false);    }  }, []);  useEffect(() => {    fetchHistory();  }, [fetchHistory]);  const triggerSync = async () => {    setSyncing(true);    setMessage('');    try {      const res = await api.post('/sync/trigger/');      setMessage(`Sync completed: ${res.data.changes_detected} changes detected`);      setMessageType('success');      fetchHistory();    } catch (err: unknown) {      const axiosErr = err as { response?: { data?: { error?: string } }; message?: string };      setMessage('Sync failed: ' + (axiosErr.response?.data?.error || axiosErr.message || 'Unknown error'));      setMessageType('error');    } finally {      setSyncing(false);    }  };  /* ── Derived stats ── */  const totalSyncs = syncHistory.length;  const lastSync = syncHistory.length > 0 ? syncHistory[0] : null;  const lastSyncStatus = lastSync    ? lastSync.status.replace('_', ' ').replace(/bw/g, (c) => c.toUpperCase())    : 'N/A';  const totalChanges = syncHistory.reduce((sum, s) => sum + s.changes_detected, 0);  /* ── Render ── */  if (loading) {    return (      <div className={styles.wrapper}>        <div className={styles.loadingContainer}>          <div className={styles.spinnerOuter} />          <span className={styles.loadingText}>Loading dashboard...</span>        </div>      </div>    );  }  return (    <div className={styles.wrapper}>      <h1 className={styles.pageTitle}>Admin Dashboard</h1>      {/* ── Stat Cards ── */}      <div className={styles.statsRow}>        <StatCard          title="Total Syncs"          value={totalSyncs}          icon={<SyncIcon />}        />        <StatCard          title="Last Sync Status"          value={lastSyncStatus}          icon={<StatusIcon />}        />        <StatCard          title="Total Changes Detected"          value={totalChanges}          icon={<ChangesIcon />}        />      </div>      {/* ── Toolbar: Sync Controls ── */}      <div className={styles.toolbar}>        <div className={styles.toolbarLeft}>          <h2 className={styles.sectionTitle}>Sync History</h2>        </div>        <div className={styles.toolbarRight}>          {message && (            <span              className={`${styles.statusMessage} ${                messageType === 'success' ? styles.statusSuccess : styles.statusError              }`}            >              {message}            </span>          )}          <button            className={styles.syncBtn}            onClick={triggerSync}            disabled={syncing}          >            {syncing ? 'Syncing...' : 'Trigger Sync'}          </button>        </div>      </div>      {/* ── Sync History Table ── */}      <div className={styles.tableWrap}>        {syncHistory.length === 0 ? (          <div className={styles.empty}>            No sync history yet. Trigger your first sync above.          </div>        ) : (          <table className={styles.table}>            <thead>              <tr>                <th className={styles.th}>ID</th>                <th className={styles.th}>Started</th>                <th className={styles.th}>Duration</th>                <th className={styles.th}>Status</th>                <th className={styles.th}>Changes</th>                <th className={styles.th}>Error</th>              </tr>            </thead>            <tbody>              {syncHistory.map((sync) => (                <tr key={sync.id} className={styles.tr}>                  <td className={styles.td}>#{sync.id}</td>                  <td className={styles.td}>{formatDateTime(sync.started_at)}</td>                  <td className={styles.td}>                    {formatDuration(sync.started_at, sync.completed_at)}                  </td>                  <td className={styles.td}>                    <span className={`${styles.badge} ${getBadgeClass(sync.status)}`}>                      {sync.status.replace('_', ' ')}                    </span>                  </td>                  <td className={styles.td}>{sync.changes_detected}</td>                  <td className={styles.td} title={sync.error_message}>                    {sync.error_message || '--'}                  </td>                </tr>              ))}            </tbody>          </table>        )}      </div>    </div>  );}
```

-    **Step 5: Verify TypeScript compiles clean**

```bash
cd frontendnpx tsc --noEmit
```

Expected: No errors. Every variable is used, no implicit `any` types, all imports resolve.

-    **Step 6: Commit**

```bash
git add frontend/src/components/StatCard.tsx frontend/src/components/StatCard.module.css frontend/src/pages/AdminDashboard.tsx frontend/src/pages/AdminDashboard.module.cssgit commit -m "feat: add admin dashboard with stat cards, sync controls, and history table"
```

---

### Design Decisions

Decision

Rationale

TypeScript `.tsx` instead of `.jsx`

Matches project plan's tech stack (React 18 + TypeScript). Typed `SyncLogEntry` interface ensures API contract safety.

CSS Modules instead of Tailwind utility classes

Matches PentEdge-CRM pattern. All styles in dedicated `.module.css` files, all colors via `var(--pm-*)` tokens.

Sticky table headers (`position: sticky; top: 0`)

Direct port from PentEdge `tables.module.css` `.th` pattern.

Hover rows with `var(--pm-table-row-hover)`

Matches PentEdge `.tr:hover` pattern exactly.

Status badges: green/red/orange

`completed` uses `--pm-accent-green` + `--pm-accent-green-bg`, `failed` uses `--pm-accent-red` + `--pm-accent-red-bg`, `in_progress` uses `--pm-accent-orange` + `--pm-accent-orange-bg` — all from PentEdge `variables.css`.

Toolbar layout (left title, right actions)

Mirrors PentEdge `.toolbar` / `.toolbarLeft` / `.toolbarRight` flexbox pattern from `pages.module.css`.

Primary button (`.syncBtn`)

Styled identically to PentEdge `.createBtn` — `--pm-accent-primary` bg, `--pm-text-on-accent` text, `--pm-accent-primary-hover` on hover.

StatCard component

Extracted as reusable component matching PentEdge `StatCard.tsx` + `StatCard.module.css` structure — icon circle, title, large value display.

`useCallback` for `fetchHistory`

Stable reference prevents unnecessary re-renders; used as `useEffect` dependency.

Duration column

Computed from `started_at` / `completed_at` — adds operational insight not in the original task.

---

## Task 14: Audit Trail Page

### Goal

Build an admin-facing Audit Trail page that displays all detected assignment changes with filtering, using PentEdge-CRM design patterns (CSS Modules, `--pm-*` variables, sticky-header table, form inputs).

### Files to Create

-   `frontend/src/pages/AuditTrailPage.tsx`
-   `frontend/src/pages/AuditTrailPage.module.css`

---

### Checklist

-    **AuditTrailPage.tsx** — TypeScript + React page component
-    **AuditTrailPage.module.css** — CSS Module with `--pm-*` variables only (no hardcoded hex)
-    Filter bar: change type dropdown, coach name input, account input, date-from picker, date-to picker, clear button
-    Filter inputs styled with PentEdge form patterns (`--pm-input-*` variables, focus ring)
-    Results table with PentEdge table styling (sticky header, row hover, border-collapse)
-    Columns: Time, Type (colored badge), Entity, Before, After, Coach, Sync #
-    Change-type badges: reassigned = orange, added = green, removed = red, updated = purple, deactivated = gray
-    Empty state message when no records match filters
-    Responsive: filter bar wraps on narrow screens

---

### Complete Code

#### `frontend/src/pages/AuditTrailPage.module.css`

```css
/* * Audit Trail page styles * Uses --pm-* variables from variables.css — no hardcoded colors *//* ── Page wrapper ── */.wrapper {  display: flex;  flex-direction: column;  flex: 1;  min-height: 0;  height: 100%;  gap: 0;}/* ── Page heading ── */.heading {  font-family: var(--font-primary);  font-weight: 600;  font-size: 20px;  color: var(--pm-text-primary);  margin: 0 0 16px;  letter-spacing: -0.01em;}/* ── Filter bar ── */.filterBar {  display: flex;  align-items: flex-end;  gap: 12px;  flex-shrink: 0;  flex-wrap: wrap;  margin-bottom: 12px;}.filterGroup {  display: flex;  flex-direction: column;  gap: 4px;}.filterLabel {  font-family: var(--font-primary);  font-weight: 500;  font-size: 11px;  color: var(--pm-text-muted);  text-transform: uppercase;  letter-spacing: 0.4px;}.filterSelect {  padding: 8px 12px;  border-radius: var(--radius-md);  border: 1px solid var(--pm-input-border);  background: var(--pm-input-bg);  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-input-text);  cursor: pointer;  outline: none;  min-width: 160px;  transition: border-color 0.2s ease, box-shadow 0.2s ease;  -webkit-appearance: none;  appearance: none;  background-image: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M6 9l6 6 6-6' stroke='%239CA3AF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");  background-repeat: no-repeat;  background-position: right 10px center;  padding-right: 28px;}.filterSelect:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}.filterInput {  padding: 8px 12px;  border-radius: var(--radius-md);  border: 1px solid var(--pm-input-border);  background: var(--pm-input-bg);  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-input-text);  outline: none;  min-width: 140px;  box-sizing: border-box;  transition: border-color 0.2s ease, box-shadow 0.2s ease;}.filterInput::placeholder {  color: var(--pm-input-placeholder);}.filterInput:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}.filterDateInput {  padding: 8px 12px;  border-radius: var(--radius-md);  border: 1px solid var(--pm-input-border);  background: var(--pm-input-bg);  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-input-text);  outline: none;  min-width: 140px;  box-sizing: border-box;  transition: border-color 0.2s ease, box-shadow 0.2s ease;}.filterDateInput:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}.clearBtn {  padding: 8px 16px;  border-radius: var(--radius-md);  border: 1px solid var(--pm-border);  background: var(--pm-card-bg);  font-family: var(--font-primary);  font-size: 13px;  font-weight: 500;  color: var(--pm-accent-red);  cursor: pointer;  white-space: nowrap;  transition: all 0.15s ease;}.clearBtn:hover {  background: var(--pm-accent-red-bg);  border-color: var(--pm-accent-red);}/* ── Table wrapper ── */.tableWrap {  flex: 1;  min-height: 0;  overflow: auto;  background: var(--pm-card-bg);  border-radius: var(--radius-xl);  border: 1px solid var(--pm-border);}.table {  min-width: 100%;  border-collapse: collapse;  table-layout: auto;}/* ── Header cells ── */.th {  position: sticky;  top: 0;  z-index: 10;  background: var(--pm-table-header-bg);  padding: 10px 12px;  text-align: left;  font-family: var(--font-primary);  font-weight: 500;  font-size: 14px;  color: var(--pm-table-header-color);  white-space: nowrap;  user-select: none;  border-bottom: 1px solid var(--pm-table-border);  min-width: 100px;}/* ── Rows ── */.tr {  border-bottom: 1px solid var(--pm-table-border);  transition: background 0.15s ease;}.tr:last-child {  border-bottom: none;}.tr:hover {  background: var(--pm-table-row-hover);}/* ── Data cells ── */.td {  padding: 8px 12px;  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-primary);  white-space: nowrap;  max-width: 220px;  overflow: hidden;  text-overflow: ellipsis;}.tdWrap {  padding: 8px 12px;  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-primary);  white-space: normal;  max-width: 220px;  word-break: break-word;}/* ── Badges ── */.badge {  display: inline-block;  padding: 3px 10px;  border-radius: var(--radius-full, 999px);  font-family: var(--font-primary);  font-weight: 600;  font-size: 11px;  text-transform: uppercase;  letter-spacing: 0.3px;  white-space: nowrap;}.badgeReassigned {  background: var(--pm-accent-orange-bg);  color: var(--pm-accent-orange);}.badgeAdded {  background: var(--pm-accent-green-bg);  color: var(--pm-accent-green);}.badgeRemoved {  background: var(--pm-accent-red-bg);  color: var(--pm-accent-red);}.badgeUpdated {  background: var(--pm-accent-purple-bg);  color: var(--pm-accent-purple);}.badgeDeactivated {  background: rgba(107, 114, 128, 0.1);  color: var(--pm-text-grey);}/* ── Sync number pill ── */.syncPill {  display: inline-flex;  align-items: center;  justify-content: center;  min-width: 28px;  padding: 2px 8px;  border-radius: var(--radius-full, 999px);  background: var(--pm-accent-primary-bg);  color: var(--pm-accent-primary);  font-family: var(--font-primary);  font-size: 12px;  font-weight: 600;}/* ── Empty state ── */.empty {  text-align: center;  padding: 60px 14px;  font-family: var(--font-primary);  font-size: 14px;  color: var(--pm-text-muted);}.emptyIcon {  font-size: 32px;  margin-bottom: 8px;  opacity: 0.5;}/* ── Loading ── */@keyframes spin {  to { transform: rotate(360deg); }}.loadingContainer {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  min-height: 300px;  gap: 16px;  flex: 1;}.spinner {  width: 40px;  height: 40px;  border-radius: 50%;  border: 3px solid var(--pm-border-light);  border-top-color: var(--pm-accent-primary);  animation: spin 0.8s linear infinite;}.loadingText {  font-family: var(--font-primary);  font-size: 14px;  font-weight: 500;  color: var(--pm-text-muted);}/* ── Result count ── */.resultCount {  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-muted);  margin-bottom: 4px;  flex-shrink: 0;}.resultCountBold {  font-weight: 600;  color: var(--pm-text-primary);}/* ── Responsive ── */@media (max-width: 768px) {  .filterBar {    flex-direction: column;    align-items: stretch;    gap: 8px;  }  .filterGroup {    width: 100%;  }  .filterSelect,  .filterInput,  .filterDateInput {    width: 100%;    min-width: unset;  }  .clearBtn {    width: 100%;    text-align: center;  }}
```

#### `frontend/src/pages/AuditTrailPage.tsx`

```tsx
import { useState, useMemo, useEffect, useCallback } from 'react'import styles from './AuditTrailPage.module.css'/* ────────────────────────────────────────────   Types   ──────────────────────────────────────────── */type ChangeType =  | 'reassigned'  | 'added'  | 'removed'  | 'updated'  | 'deactivated'interface AuditRecord {  id: number  timestamp: string            // ISO string  changeType: ChangeType  entityType: string           // e.g. "Contact", "Account", "Coach"  entityName: string  beforeValue: string | null  afterValue: string | null  coachName: string  accountName: string  syncRunId: number}/* ────────────────────────────────────────────   Badge helper   ──────────────────────────────────────────── */const BADGE_CLASS: Record<ChangeType, string> = {  reassigned: styles.badgeReassigned,  added: styles.badgeAdded,  removed: styles.badgeRemoved,  updated: styles.badgeUpdated,  deactivated: styles.badgeDeactivated,}const CHANGE_TYPE_OPTIONS: ChangeType[] = [  'reassigned',  'added',  'removed',  'updated',  'deactivated',]/* ────────────────────────────────────────────   Helpers   ──────────────────────────────────────────── */function formatTimestamp(iso: string): string {  const d = new Date(iso)  return d.toLocaleString(undefined, {    year: 'numeric',    month: 'short',    day: 'numeric',    hour: '2-digit',    minute: '2-digit',    second: '2-digit',  })}function toDateInputValue(d: Date): string {  const yyyy = d.getFullYear()  const mm = String(d.getMonth() + 1).padStart(2, '0')  const dd = String(d.getDate()).padStart(2, '0')  return `${yyyy}-${mm}-${dd}`}/* ────────────────────────────────────────────   Component   ──────────────────────────────────────────── */export default function AuditTrailPage() {  /* ── Data state ── */  const [records, setRecords] = useState<AuditRecord[]>([])  const [loading, setLoading] = useState(true)  /* ── Filter state ── */  const [changeTypeFilter, setChangeTypeFilter] = useState<string>('')  const [coachFilter, setCoachFilter] = useState('')  const [accountFilter, setAccountFilter] = useState('')  const [dateFrom, setDateFrom] = useState('')  const [dateTo, setDateTo] = useState('')  /* ── Fetch audit records from API ── */  const fetchRecords = useCallback(async () => {    setLoading(true)    try {      // TODO: replace with your actual API call, e.g.:      // const res = await auditApi.list()      // setRecords(res.results)      const res = await fetch('/api/audit-trail/')      if (!res.ok) throw new Error('Failed to fetch audit trail')      const data = await res.json()      setRecords(data.results ?? data)    } catch (err) {      console.error('Error loading audit trail:', err)      setRecords([])    } finally {      setLoading(false)    }  }, [])  useEffect(() => {    fetchRecords()  }, [fetchRecords])  /* ── Filtered records ── */  const filtered = useMemo(() => {    let result = records    if (changeTypeFilter) {      result = result.filter(r => r.changeType === changeTypeFilter)    }    if (coachFilter.trim()) {      const q = coachFilter.trim().toLowerCase()      result = result.filter(r => r.coachName.toLowerCase().includes(q))    }    if (accountFilter.trim()) {      const q = accountFilter.trim().toLowerCase()      result = result.filter(r => r.accountName.toLowerCase().includes(q))    }    if (dateFrom) {      const from = new Date(dateFrom)      from.setHours(0, 0, 0, 0)      result = result.filter(r => new Date(r.timestamp) >= from)    }    if (dateTo) {      const to = new Date(dateTo)      to.setHours(23, 59, 59, 999)      result = result.filter(r => new Date(r.timestamp) <= to)    }    return result  }, [records, changeTypeFilter, coachFilter, accountFilter, dateFrom, dateTo])  /* ── Clear all filters ── */  const clearFilters = () => {    setChangeTypeFilter('')    setCoachFilter('')    setAccountFilter('')    setDateFrom('')    setDateTo('')  }  const hasActiveFilters =    changeTypeFilter !== '' ||    coachFilter !== '' ||    accountFilter !== '' ||    dateFrom !== '' ||    dateTo !== ''  /* ── Render ── */  if (loading) {    return (      <div className={styles.wrapper}>        <h1 className={styles.heading}>Audit Trail</h1>        <div className={styles.loadingContainer}>          <div className={styles.spinner} />          <span className={styles.loadingText}>Loading audit records...</span>        </div>      </div>    )  }  return (    <div className={styles.wrapper}>      <h1 className={styles.heading}>Audit Trail</h1>      {/* ── Filter Bar ── */}      <div className={styles.filterBar}>        {/* Change Type */}        <div className={styles.filterGroup}>          <label className={styles.filterLabel}>Change Type</label>          <select            className={styles.filterSelect}            value={changeTypeFilter}            onChange={e => setChangeTypeFilter(e.target.value)}          >            <option value="">All Types</option>            {CHANGE_TYPE_OPTIONS.map(t => (              <option key={t} value={t}>                {t.charAt(0).toUpperCase() + t.slice(1)}              </option>            ))}          </select>        </div>        {/* Coach Name */}        <div className={styles.filterGroup}>          <label className={styles.filterLabel}>Coach</label>          <input            type="text"            className={styles.filterInput}            placeholder="Filter by coach..."            value={coachFilter}            onChange={e => setCoachFilter(e.target.value)}          />        </div>        {/* Account */}        <div className={styles.filterGroup}>          <label className={styles.filterLabel}>Account</label>          <input            type="text"            className={styles.filterInput}            placeholder="Filter by account..."            value={accountFilter}            onChange={e => setAccountFilter(e.target.value)}          />        </div>        {/* Date From */}        <div className={styles.filterGroup}>          <label className={styles.filterLabel}>From</label>          <input            type="date"            className={styles.filterDateInput}            value={dateFrom}            onChange={e => setDateFrom(e.target.value)}          />        </div>        {/* Date To */}        <div className={styles.filterGroup}>          <label className={styles.filterLabel}>To</label>          <input            type="date"            className={styles.filterDateInput}            value={dateTo}            onChange={e => setDateTo(e.target.value)}            min={dateFrom || undefined}          />        </div>        {/* Clear */}        {hasActiveFilters && (          <button            type="button"            className={styles.clearBtn}            onClick={clearFilters}          >            Clear Filters          </button>        )}      </div>      {/* ── Result count ── */}      <div className={styles.resultCount}>        Showing{' '}        <span className={styles.resultCountBold}>{filtered.length}</span>        {' '}of{' '}        <span className={styles.resultCountBold}>{records.length}</span>        {' '}records      </div>      {/* ── Table ── */}      {filtered.length === 0 ? (        <div className={styles.empty}>          <div className={styles.emptyIcon}>&#128269;</div>          {records.length === 0            ? 'No audit records yet. Run a sync to detect changes.'            : 'No records match the current filters.'}        </div>      ) : (        <div className={styles.tableWrap}>          <table className={styles.table}>            <thead>              <tr>                <th className={styles.th}>Time</th>                <th className={styles.th}>Type</th>                <th className={styles.th}>Entity</th>                <th className={styles.th}>Before</th>                <th className={styles.th}>After</th>                <th className={styles.th}>Coach</th>                <th className={styles.th}>Sync #</th>              </tr>            </thead>            <tbody>              {filtered.map(record => (                <tr key={record.id} className={styles.tr}>                  <td className={styles.td}>                    {formatTimestamp(record.timestamp)}                  </td>                  <td className={styles.td}>                    <span                      className={`${styles.badge} ${BADGE_CLASS[record.changeType] || ''}`}                    >                      {record.changeType}                    </span>                  </td>                  <td className={styles.td} title={`${record.entityType}: ${record.entityName}`}>                    <strong>{record.entityType}</strong>                    {' — '}                    {record.entityName}                  </td>                  <td className={styles.tdWrap}>                    {record.beforeValue ?? '—'}                  </td>                  <td className={styles.tdWrap}>                    {record.afterValue ?? '—'}                  </td>                  <td className={styles.td}>{record.coachName}</td>                  <td className={styles.td}>                    <span className={styles.syncPill}>                      #{record.syncRunId}                    </span>                  </td>                </tr>              ))}            </tbody>          </table>        </div>      )}    </div>  )}
```

---

### Design Notes

Concern

Decision

**Variables**

Every color references a `--pm-*` CSS variable from `variables.css` -- no hardcoded hex except the deactivated badge `rgba()` fallback that mirrors the PentEdge badge pattern

**Badge colors**

`reassigned` = orange (`--pm-accent-orange`), `added` = green (`--pm-accent-green`), `removed` = red (`--pm-accent-red`), `updated` = purple (`--pm-accent-purple`), `deactivated` = grey (`--pm-text-grey`)

**Sticky header**

`.th` uses `position: sticky; top: 0; z-index: 10` matching `tables.module.css`

**Input focus**

All inputs use `--pm-input-focus-border` + `--pm-input-focus-ring` for the gold ring on focus, matching `forms.module.css`

**Select chevron**

Embedded SVG background-image matching `pages.module.css .filterSelect` pattern

**Empty state**

Two variants: no records at all vs. no records matching filters

**API shape**

Expects `GET /api/audit-trail/` returning `{ results: AuditRecord[] }` -- adjust the `fetchRecords` call to match your actual backend

**Before/After cells**

Use `white-space: normal` + `word-break` to allow wrapping for longer values

**Responsive**

Filter bar stacks vertically below 768px

---

## Task 15: Transition Briefs Page

Build a two-column Transition Briefs browsing page following PentEdge-CRM's detail layout pattern. Left panel lists briefs as clickable cards; right panel shows the selected brief's formatted content. Uses TypeScript, CSS Modules, and `--pm-*` design tokens throughout.

---

## Files to Create

### 1. `frontend/src/pages/TransitionBriefsPage.tsx`

-    Create the page component

```tsx
import { useState, useEffect, useCallback } from 'react'import styles from './TransitionBriefsPage.module.css'/* ── Types ── */type TransitionBrief = {  id: number  contactName: string  accountName: string  previousCoach: string  newCoach: string  generatedAt: string  content: string  syncRunId: number}/* ── Helpers ── */function formatDate(iso: string): string {  const d = new Date(iso)  return d.toLocaleDateString('en-US', {    month: 'short',    day: 'numeric',    year: 'numeric',  })}function formatDateTime(iso: string): string {  const d = new Date(iso)  return d.toLocaleString('en-US', {    month: 'short',    day: 'numeric',    year: 'numeric',    hour: 'numeric',    minute: '2-digit',  })}function getInitials(name: string): string {  return name    .split(' ')    .map((w) => w[0])    .join('')    .toUpperCase()    .slice(0, 2)}/* ── Brief content renderer ── */function BriefContent({ content }: { content: string }) {  // Split content into sections by markdown-style headings or double newlines  const lines = content.split('n')  const elements: React.ReactNode[] = []  lines.forEach((line, i) => {    const trimmed = line.trim()    if (!trimmed) {      elements.push(<div key={i} className={styles.contentSpacer} />)    } else if (trimmed.startsWith('### ')) {      elements.push(        <h4 key={i} className={styles.contentH3}>          {trimmed.slice(4)}        </h4>      )    } else if (trimmed.startsWith('## ')) {      elements.push(        <h3 key={i} className={styles.contentH2}>          {trimmed.slice(3)}        </h3>      )    } else if (trimmed.startsWith('# ')) {      elements.push(        <h2 key={i} className={styles.contentH1}>          {trimmed.slice(2)}        </h2>      )    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {      elements.push(        <li key={i} className={styles.contentListItem}>          {trimmed.slice(2)}        </li>      )    } else if (/^d+.s/.test(trimmed)) {      elements.push(        <li key={i} className={styles.contentListItemOrdered}>          {trimmed.replace(/^d+.s/, '')}        </li>      )    } else if (trimmed.startsWith('**') && trimmed.endsWith('**')) {      elements.push(        <p key={i} className={styles.contentBold}>          {trimmed.slice(2, -2)}        </p>      )    } else {      elements.push(        <p key={i} className={styles.contentParagraph}>          {trimmed}        </p>      )    }  })  return <div className={styles.contentBody}>{elements}</div>}/* ── Main Page ── */export default function TransitionBriefsPage() {  const [briefs, setBriefs] = useState<TransitionBrief[]>([])  const [selectedId, setSelectedId] = useState<number | null>(null)  const [loading, setLoading] = useState(true)  const [error, setError] = useState<string | null>(null)  const [searchTerm, setSearchTerm] = useState('')  const fetchBriefs = useCallback(async () => {    try {      setLoading(true)      const res = await fetch('/api/transition-briefs/')      if (!res.ok) throw new Error(`Failed to load briefs (${res.status})`)      const data = await res.json()      const list: TransitionBrief[] = Array.isArray(data) ? data : data.results ?? []      setBriefs(list)      if (list.length > 0 && selectedId === null) {        setSelectedId(list[0].id)      }    } catch (err) {      setError(err instanceof Error ? err.message : 'Unknown error')    } finally {      setLoading(false)    }  }, [selectedId])  useEffect(() => {    fetchBriefs()  }, [fetchBriefs])  const filtered = briefs.filter((b) => {    if (!searchTerm) return true    const q = searchTerm.toLowerCase()    return (      b.contactName.toLowerCase().includes(q) ||      b.accountName.toLowerCase().includes(q) ||      b.previousCoach.toLowerCase().includes(q) ||      b.newCoach.toLowerCase().includes(q)    )  })  const selected = briefs.find((b) => b.id === selectedId) ?? null  /* ── Loading state ── */  if (loading) {    return (      <div className={styles.wrapper}>        <div className={styles.loadingContainer}>          <div className={styles.spinnerOuter} />          <span className={styles.loadingText}>Loading transition briefs...</span>        </div>      </div>    )  }  /* ── Error state ── */  if (error) {    return (      <div className={styles.wrapper}>        <div className={styles.emptyState}>          <div className={styles.emptyIcon}>            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />            </svg>          </div>          <h3 className={styles.emptyTitle}>Error Loading Briefs</h3>          <p className={styles.emptyDescription}>{error}</p>          <button className={styles.retryBtn} onClick={fetchBriefs} type="button">            Retry          </button>        </div>      </div>    )  }  /* ── Empty state (no briefs at all) ── */  if (briefs.length === 0) {    return (      <div className={styles.wrapper}>        <div className={styles.pageHeader}>          <h1 className={styles.pageTitle}>Transition Briefs</h1>        </div>        <div className={styles.emptyState}>          <div className={styles.emptyIcon}>            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">              <path                d="M9 12h6M12 9v6M21 12a9 9 0 11-18 0 9 9 0 0118 0z"                stroke="currentColor"                strokeWidth="1.5"                strokeLinecap="round"                strokeLinejoin="round"              />            </svg>          </div>          <h3 className={styles.emptyTitle}>No Transition Briefs Yet</h3>          <p className={styles.emptyDescription}>            Transition briefs are automatically generated when a client is reassigned to a new coach.            Run a sync to detect reassignments.          </p>        </div>      </div>    )  }  /* ── Main layout ── */  return (    <div className={styles.wrapper}>      {/* Page header */}      <div className={styles.pageHeader}>        <h1 className={styles.pageTitle}>Transition Briefs</h1>        <span className={styles.briefCount}>          {briefs.length} brief{briefs.length !== 1 ? 's' : ''}        </span>      </div>      {/* Two-column detail body */}      <div className={styles.detailBody}>        {/* LEFT: Brief list panel */}        <aside className={styles.listPanel}>          {/* Search */}          <div className={styles.searchWrap}>            <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none">              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />            </svg>            <input              className={styles.searchInput}              type="text"              placeholder="Search briefs..."              value={searchTerm}              onChange={(e) => setSearchTerm(e.target.value)}            />            {searchTerm && (              <button                className={styles.clearSearch}                onClick={() => setSearchTerm('')}                type="button"              >                &amp;times;              </button>            )}          </div>          {/* Card list */}          <div className={styles.cardList}>            {filtered.length === 0 ? (              <div className={styles.noResults}>No briefs match your search.</div>            ) : (              filtered.map((brief) => (                <button                  key={brief.id}                  className={`${styles.briefCard} ${                    selectedId === brief.id ? styles.briefCardActive : ''                  }`}                  onClick={() => setSelectedId(brief.id)}                  type="button"                >                  <div className={styles.cardAvatar}>                    {getInitials(brief.contactName)}                  </div>                  <div className={styles.cardInfo}>                    <span className={styles.cardName}>{brief.contactName}</span>                    <span className={styles.cardAccount}>{brief.accountName}</span>                    <div className={styles.cardMeta}>                      <span className={styles.cardCoaches}>                        {brief.previousCoach} &rarr; {brief.newCoach}                      </span>                      <span className={styles.cardDate}>{formatDate(brief.generatedAt)}</span>                    </div>                  </div>                </button>              ))            )}          </div>        </aside>        {/* RIGHT: Brief detail panel */}        <main className={styles.detailPanel}>          {selected ? (            <>              {/* Detail header */}              <div className={styles.detailHeader}>                <div className={styles.detailAvatar}>                  {getInitials(selected.contactName)}                </div>                <div className={styles.detailHeaderInfo}>                  <h2 className={styles.detailTitle}>{selected.contactName}</h2>                  <div className={styles.detailSubtitle}>                    <span className={styles.detailAccount}>{selected.accountName}</span>                    <span className={styles.detailDivider}>&bull;</span>                    <span className={styles.detailDate}>                      Generated {formatDateTime(selected.generatedAt)}                    </span>                  </div>                </div>              </div>              {/* Coach reassignment badge row */}              <div className={styles.reassignmentRow}>                <div className={styles.coachBadge}>                  <span className={styles.coachBadgeLabel}>Previous Coach</span>                  <span className={styles.coachBadgeValue}>{selected.previousCoach}</span>                </div>                <div className={styles.arrowIcon}>                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">                    <path                      d="M5 12h14M13 6l6 6-6 6"                      stroke="currentColor"                      strokeWidth="2"                      strokeLinecap="round"                      strokeLinejoin="round"                    />                  </svg>                </div>                <div className={`${styles.coachBadge} ${styles.coachBadgeNew}`}>                  <span className={styles.coachBadgeLabel}>New Coach</span>                  <span className={styles.coachBadgeValue}>{selected.newCoach}</span>                </div>                <div className={styles.syncBadge}>                  Sync #{selected.syncRunId}                </div>              </div>              {/* Brief content */}              <div className={styles.detailContent}>                <BriefContent content={selected.content} />              </div>            </>          ) : (            <div className={styles.detailEmpty}>              <svg width="40" height="40" viewBox="0 0 24 24" fill="none">                <path                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"                  stroke="currentColor"                  strokeWidth="1.5"                  strokeLinecap="round"                  strokeLinejoin="round"                />              </svg>              <p>Select a brief from the list to view its details.</p>            </div>          )}        </main>      </div>    </div>  )}
```

---

### 2. `frontend/src/pages/TransitionBriefsPage.module.css`

-    Create the CSS Module with `--pm-*` variables

```css
/* ── Page Wrapper ── */.wrapper {  display: flex;  flex-direction: column;  flex: 1;  min-height: 0;  height: 100%;}/* ── Page Header ── */.pageHeader {  display: flex;  align-items: center;  gap: 12px;  flex-shrink: 0;  margin-bottom: 16px;}.pageTitle {  font-family: var(--font-primary);  font-weight: 700;  font-size: 20px;  color: var(--pm-text-primary);  margin: 0;}.briefCount {  display: inline-flex;  align-items: center;  padding: 3px 10px;  border-radius: var(--radius-full);  background: var(--pm-accent-primary-bg);  color: var(--pm-accent-primary);  font-family: var(--font-primary);  font-weight: 600;  font-size: 12px;}/* ── Two-Column Detail Body (matches PentEdge LeadDetailPage) ── */.detailBody {  display: flex;  gap: 20px;  flex: 1;  min-height: 0;}/* ── LEFT: List Panel ── */.listPanel {  width: 340px;  flex-shrink: 0;  display: flex;  flex-direction: column;  gap: 12px;  min-height: 0;}/* Search (matches PentEdge pages.module.css searchWrap) */.searchWrap {  display: flex;  align-items: center;  gap: 8px;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border);  border-radius: var(--radius-lg);  padding: 9px 14px;  transition: border-color 0.2s ease, box-shadow 0.2s ease;  flex-shrink: 0;}.searchWrap:focus-within {  border-color: var(--pm-accent-primary);  box-shadow: 0 0 0 3px var(--pm-accent-primary-bg);}.searchIcon {  flex-shrink: 0;  color: var(--pm-text-muted);}.searchInput {  border: none;  outline: none;  background: transparent;  font-family: var(--font-primary);  font-size: 14px;  color: var(--pm-input-text);  width: 100%;}.searchInput::placeholder {  color: var(--pm-input-placeholder);}.clearSearch {  font-size: 16px;  color: var(--pm-text-muted);  cursor: pointer;  line-height: 1;  background: none;  border: none;  transition: color 0.15s ease;}.clearSearch:hover {  color: var(--pm-text-primary);}/* Card list */.cardList {  display: flex;  flex-direction: column;  gap: 6px;  overflow-y: auto;  flex: 1;  min-height: 0;  padding-right: 4px;}.cardList::-webkit-scrollbar {  width: 4px;}.cardList::-webkit-scrollbar-track {  background: transparent;}.cardList::-webkit-scrollbar-thumb {  background: var(--pm-border);  border-radius: 4px;}/* Brief card (matches PentEdge --pm-card-bg, shadow, border-radius) */.briefCard {  display: flex;  align-items: flex-start;  gap: 12px;  width: 100%;  text-align: left;  padding: 14px 16px;  border-radius: 10px;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border);  cursor: pointer;  transition: all 0.15s ease;}.briefCard:hover {  background: var(--pm-card-bg-hover);  border-color: var(--pm-border-heavy);  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);}.briefCardActive {  background: var(--pm-accent-primary-bg);  border-color: var(--pm-accent-primary);  box-shadow: 0 1px 6px rgba(158, 133, 68, 0.12);}.briefCardActive:hover {  background: var(--pm-accent-primary-bg);  border-color: var(--pm-accent-primary);}/* Card avatar */.cardAvatar {  width: 38px;  height: 38px;  border-radius: 50%;  background: linear-gradient(135deg, var(--pm-accent-primary), var(--pm-accent-purple));  display: flex;  align-items: center;  justify-content: center;  font-family: var(--font-primary);  font-weight: 700;  font-size: 13px;  color: var(--pm-text-on-accent);  flex-shrink: 0;}/* Card info */.cardInfo {  display: flex;  flex-direction: column;  gap: 3px;  min-width: 0;  flex: 1;}.cardName {  font-family: var(--font-primary);  font-weight: 600;  font-size: 14px;  color: var(--pm-text-primary);  white-space: nowrap;  overflow: hidden;  text-overflow: ellipsis;}.cardAccount {  font-family: var(--font-primary);  font-weight: 400;  font-size: 12px;  color: var(--pm-text-grey);  white-space: nowrap;  overflow: hidden;  text-overflow: ellipsis;}.cardMeta {  display: flex;  align-items: center;  justify-content: space-between;  gap: 8px;  margin-top: 2px;}.cardCoaches {  font-family: var(--font-primary);  font-weight: 500;  font-size: 11px;  color: var(--pm-accent-primary);  white-space: nowrap;  overflow: hidden;  text-overflow: ellipsis;}.cardDate {  font-family: var(--font-primary);  font-weight: 400;  font-size: 11px;  color: var(--pm-text-muted);  white-space: nowrap;  flex-shrink: 0;}.noResults {  text-align: center;  padding: 32px 16px;  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-muted);}/* ── RIGHT: Detail Panel ── */.detailPanel {  flex: 1;  min-width: 0;  background: var(--pm-card-bg);  border: 1px solid var(--pm-border);  border-radius: 10px;  padding: 24px;  overflow-y: auto;  display: flex;  flex-direction: column;  gap: 20px;}/* Detail header */.detailHeader {  display: flex;  align-items: center;  gap: 14px;  padding-bottom: 16px;  border-bottom: 1px solid var(--pm-border-light);}.detailAvatar {  width: 48px;  height: 48px;  border-radius: 50%;  background: linear-gradient(135deg, var(--pm-accent-primary), var(--pm-accent-purple));  display: flex;  align-items: center;  justify-content: center;  font-family: var(--font-primary);  font-weight: 700;  font-size: 16px;  color: var(--pm-text-on-accent);  flex-shrink: 0;}.detailHeaderInfo {  display: flex;  flex-direction: column;  gap: 4px;  min-width: 0;}.detailTitle {  font-family: var(--font-primary);  font-weight: 700;  font-size: 18px;  color: var(--pm-text-primary);  margin: 0;}.detailSubtitle {  display: flex;  align-items: center;  gap: 8px;  flex-wrap: wrap;}.detailAccount {  font-family: var(--font-primary);  font-weight: 500;  font-size: 13px;  color: var(--pm-text-grey);}.detailDivider {  color: var(--pm-border-heavy);  font-size: 10px;}.detailDate {  font-family: var(--font-primary);  font-weight: 400;  font-size: 12px;  color: var(--pm-text-muted);}/* Reassignment row */.reassignmentRow {  display: flex;  align-items: center;  gap: 12px;  flex-wrap: wrap;}.coachBadge {  display: flex;  flex-direction: column;  gap: 2px;  padding: 10px 16px;  border-radius: var(--radius-lg);  background: var(--pm-badge-bg);  border: 1px solid var(--pm-badge-border);}.coachBadgeNew {  background: var(--pm-accent-green-bg);  border-color: var(--pm-accent-green);}.coachBadgeLabel {  font-family: var(--font-primary);  font-weight: 500;  font-size: 10px;  color: var(--pm-text-muted);  text-transform: uppercase;  letter-spacing: 0.5px;}.coachBadgeValue {  font-family: var(--font-primary);  font-weight: 600;  font-size: 14px;  color: var(--pm-text-primary);}.coachBadgeNew .coachBadgeValue {  color: var(--pm-accent-green);}.arrowIcon {  color: var(--pm-text-muted);  display: flex;  align-items: center;}.syncBadge {  margin-left: auto;  padding: 4px 12px;  border-radius: var(--radius-full);  background: var(--pm-accent-primary-bg);  color: var(--pm-accent-primary);  font-family: var(--font-primary);  font-weight: 600;  font-size: 12px;}/* ── Brief Content Typography ── */.detailContent {  flex: 1;  min-height: 0;}.contentBody {  display: flex;  flex-direction: column;  gap: 4px;}.contentH1 {  font-family: var(--font-primary);  font-weight: 700;  font-size: 18px;  color: var(--pm-text-primary);  margin: 16px 0 8px 0;  padding-bottom: 6px;  border-bottom: 1px solid var(--pm-border-light);}.contentH2 {  font-family: var(--font-primary);  font-weight: 700;  font-size: 15px;  color: var(--pm-text-primary);  margin: 14px 0 6px 0;}.contentH3 {  font-family: var(--font-primary);  font-weight: 600;  font-size: 13px;  color: var(--pm-text-secondary);  text-transform: uppercase;  letter-spacing: 0.3px;  margin: 12px 0 4px 0;}.contentParagraph {  font-family: var(--font-primary);  font-weight: 400;  font-size: 14px;  color: var(--pm-text-primary);  line-height: 1.65;  margin: 0;}.contentBold {  font-family: var(--font-primary);  font-weight: 600;  font-size: 14px;  color: var(--pm-text-primary);  line-height: 1.65;  margin: 0;}.contentListItem {  font-family: var(--font-primary);  font-weight: 400;  font-size: 14px;  color: var(--pm-text-primary);  line-height: 1.65;  margin-left: 20px;  list-style-type: disc;}.contentListItemOrdered {  font-family: var(--font-primary);  font-weight: 400;  font-size: 14px;  color: var(--pm-text-primary);  line-height: 1.65;  margin-left: 20px;  list-style-type: decimal;}.contentSpacer {  height: 8px;}/* ── Detail empty state (no selection) ── */.detailEmpty {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  gap: 12px;  flex: 1;  color: var(--pm-text-muted);  font-family: var(--font-primary);  font-size: 14px;}.detailEmpty p {  margin: 0;}/* ── Full-page Empty State ── */.emptyState {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  gap: 12px;  flex: 1;  min-height: 400px;  text-align: center;  padding: 40px 20px;}.emptyIcon {  color: var(--pm-text-muted);  opacity: 0.5;  margin-bottom: 4px;}.emptyTitle {  font-family: var(--font-primary);  font-weight: 700;  font-size: 16px;  color: var(--pm-text-primary);  margin: 0;}.emptyDescription {  font-family: var(--font-primary);  font-weight: 400;  font-size: 14px;  color: var(--pm-text-muted);  margin: 0;  max-width: 360px;  line-height: 1.5;}.retryBtn {  padding: 9px 20px;  border-radius: var(--radius-lg);  background: var(--pm-accent-primary);  color: var(--pm-text-on-accent);  font-family: var(--font-primary);  font-weight: 500;  font-size: 14px;  cursor: pointer;  border: none;  transition: background 0.15s ease;  margin-top: 8px;}.retryBtn:hover {  background: var(--pm-accent-primary-hover);}/* ── Loading ── */.loadingContainer {  display: flex;  flex-direction: column;  align-items: center;  justify-content: center;  min-height: 400px;  gap: 16px;  flex: 1;}@keyframes spinOuter {  to {    transform: rotate(360deg);  }}.spinnerOuter {  width: 48px;  height: 48px;  border-radius: 50%;  border: 3px solid var(--pm-border-light);  border-top-color: var(--pm-accent-primary);  animation: spinOuter 0.8s linear infinite;}.loadingText {  font-family: var(--font-primary);  font-size: 14px;  font-weight: 500;  color: var(--pm-text-muted);}/* ── Responsive ── */@media (max-width: 900px) {  .listPanel {    width: 280px;  }}@media (max-width: 768px) {  .detailBody {    flex-direction: column;    gap: 12px;  }  .listPanel {    width: 100%;    max-height: 300px;  }  .detailPanel {    min-height: 400px;  }}@media (max-width: 480px) {  .pageTitle {    font-size: 18px;  }  .detailPanel {    padding: 16px;  }  .briefCard {    padding: 10px 12px;  }}
```

---

## Integration Checklist

-    Add route for `/transition-briefs` in the app router pointing to `TransitionBriefsPage`
-    Add sidebar navigation entry for "Transition Briefs" in the main layout component
-    Verify the API endpoint `GET /api/transition-briefs/` returns an array (or `{ results: [...] }`) with fields: `id`, `contactName`, `accountName`, `previousCoach`, `newCoach`, `generatedAt`, `content`, `syncRunId`
-    Confirm `variables.css` with `--pm-*` tokens is imported at the app root
-    Test loading state displays spinner
-    Test empty state appears when no briefs exist
-    Test clicking a brief card highlights it and renders the right panel
-    Test search filters cards by contact name, account name, or coach name
-    Test brief content renders markdown-style headings, paragraphs, and lists
-    Test responsive layout: stacks vertically on screens below 768px
-    Verify no hardcoded hex colors in CSS -- all via `var(--pm-*)` tokens

---

## Design Pattern Notes

Pattern

PentEdge Source

Applied Here

Two-column detail layout

`LeadDetailPage.module.css` `.detailBody`

`.detailBody` with 340px list + flex:1 detail

Card styling

`--pm-card-bg`, 10px border-radius, 1px border

`.briefCard` with same tokens

Active state

`--pm-accent-primary-bg` + accent border

`.briefCardActive`

Avatar fallback

`LeadDetailPage` `.heroAvatarFallback` gradient

`.cardAvatar` / `.detailAvatar`

Search bar

`pages.module.css` `.searchWrap` pattern

`.searchWrap` identical structure

Empty state

`pages.module.css` `.empty` + `.loadingContainer`

`.emptyState` centered with icon

Loading spinner

`pages.module.css` `.spinnerOuter`

Same keyframe + token usage

Typography

`--font-primary`, `--pm-text-primary/secondary/muted`

All content headings and paragraphs

---

## Task 16: Source Editor Page (Admin)

**Files:**

-   Create: `frontend/src/pages/SourceEditorPage.tsx`
-   Create: `frontend/src/pages/SourceEditorPage.module.css`

This page lets admins view and edit the simulated Salesforce source data (coaches, accounts, contacts) using tabbed editable tables. After making changes here, the admin triggers a sync from the Admin Dashboard to test change detection.

---

-    **Step 1: Create the CSS Module**

`frontend/src/pages/SourceEditorPage.module.css`:

```css
/* * Source Editor Page styles * Mirrors PentEdge CRM patterns: tabs from pages.module.css, * table from tables.module.css, inputs from forms.module.css *//* ── Page wrapper ── */.wrapper {  display: flex;  flex-direction: column;  gap: 0;  flex: 1;  min-height: 0;  height: 100%;}/* ── Header ── */.header {  flex-shrink: 0;  margin-bottom: 12px;}.title {  font-family: var(--font-primary);  font-weight: 600;  font-size: 20px;  color: var(--pm-text-primary);  margin: 0 0 4px;  letter-spacing: -0.01em;}.description {  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-muted);  margin: 0;  line-height: 1.5;}.descriptionHighlight {  color: var(--pm-accent-primary);  font-weight: 500;}/* ── Tabs (matches PentEdge pages.module.css .tabs/.tab/.tabActive) ── */.tabs {  margin-bottom: 8px;  flex-shrink: 0;  display: flex;  align-items: center;  gap: 0;  background: var(--pm-card-bg);  border-radius: var(--radius-lg);  padding: 3px;  border: 1px solid var(--pm-border);  width: fit-content;}.tab {  padding: 7px 22px;  border-radius: var(--radius-md);  font-family: var(--font-primary);  font-weight: 500;  font-size: 14px;  color: var(--pm-text-muted);  background: transparent;  border: none;  cursor: pointer;  transition: all 0.15s ease;}.tab:hover {  color: var(--pm-text-primary);}.tabActive {  background: var(--pm-accent-primary);  color: var(--pm-text-on-accent);}.tabActive:hover {  color: var(--pm-text-on-accent);}/* ── Table wrapper (matches PentEdge tables.module.css) ── */.tableWrap {  flex: 1;  min-height: 0;  overflow: auto;  background: var(--pm-card-bg);  border-radius: var(--radius-xl);  border: 1px solid var(--pm-border);  margin-top: 6px;}.table {  min-width: 100%;  border-collapse: collapse;  table-layout: auto;}/* ── Header cells (sticky, matches tables.module.css .th) ── */.th {  position: sticky;  top: 0;  z-index: 10;  background: var(--pm-table-header-bg);  padding: 10px 12px;  text-align: left;  font-family: var(--font-primary);  font-weight: 500;  font-size: 14px;  color: var(--pm-table-header-color);  white-space: nowrap;  user-select: none;  border-bottom: 1px solid var(--pm-table-border);  min-width: 120px;}/* ── Rows (matches tables.module.css .tr) ── */.tr {  border-bottom: 1px solid var(--pm-table-border);  transition: background 0.15s ease;}.tr:last-child {  border-bottom: none;}.tr:hover {  background: var(--pm-table-row-hover);}/* ── Data cells (matches tables.module.css .td) ── */.td {  padding: 8px 12px;  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-text-primary);  white-space: nowrap;  min-width: 120px;}/* ── Inline editable input (matches forms.module.css .input) ── */.inlineInput {  width: 100%;  padding: 6px 10px;  border: 1px solid var(--pm-input-border);  border-radius: var(--radius-md);  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-input-text);  background: var(--pm-input-bg);  outline: none;  box-sizing: border-box;  transition: border-color 0.2s ease, box-shadow 0.2s ease;}.inlineInput:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}.inlineInput::placeholder {  color: var(--pm-input-placeholder);}/* ── Inline select dropdown (matches forms.module.css .select + filterSelect pattern) ── */.inlineSelect {  width: 100%;  padding: 6px 10px;  border: 1px solid var(--pm-input-border);  border-radius: var(--radius-md);  font-family: var(--font-primary);  font-size: 13px;  color: var(--pm-input-text);  background: var(--pm-input-bg);  outline: none;  cursor: pointer;  box-sizing: border-box;  transition: border-color 0.2s ease, box-shadow 0.2s ease;  -webkit-appearance: none;  appearance: none;  background-image: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M6 9l6 6 6-6' stroke='%239CA3AF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");  background-repeat: no-repeat;  background-position: right 8px center;  padding-right: 26px;}.inlineSelect:focus {  border-color: var(--pm-input-focus-border);  box-shadow: 0 0 0 3px var(--pm-input-focus-ring);}/* ── Checkbox (styled to match PentEdge accent) ── */.checkbox {  width: 16px;  height: 16px;  accent-color: var(--pm-accent-primary);  cursor: pointer;}/* ── Empty state ── */.empty {  text-align: center;  padding: 60px 14px;  font-family: var(--font-primary);  font-size: 14px;  color: var(--pm-text-muted);}/* ── Status indicator for save feedback ── */.saveStatus {  font-family: var(--font-primary);  font-size: 12px;  font-weight: 500;  margin-left: 12px;  transition: opacity 0.3s ease;}.saveStatusSuccess {  color: var(--pm-accent-green);}.saveStatusError {  color: var(--pm-accent-red);}/* ── Responsive ── */@media (max-width: 768px) {  .tabs {    width: 100%;    overflow-x: auto;    -ms-overflow-style: none;    scrollbar-width: none;  }  .tabs::-webkit-scrollbar {    display: none;  }  .title {    font-size: 18px;  }}
```

-    **Step 2: Create the TypeScript component**

`frontend/src/pages/SourceEditorPage.tsx`:

```tsx
import { useState, useEffect, useCallback } from "react";import api from "../api/client";import s from "./SourceEditorPage.module.css";/* ── Types ── */interface Coach {  id: number;  name: string;  email: string;  is_active: boolean;}interface Account {  id: number;  name: string;  industry: string;  coach: number | null;}interface Contact {  id: number;  name: string;  title: string;  account_name: string;  coach: number | null;}type TabKey = "coaches" | "accounts" | "contacts";const TAB_LABELS: { key: TabKey; label: string }[] = [  { key: "coaches", label: "Coaches" },  { key: "accounts", label: "Accounts" },  { key: "contacts", label: "Contacts" },];/* ── Component ── */export default function SourceEditorPage() {  const [coaches, setCoaches] = useState<Coach[]>([]);  const [accounts, setAccounts] = useState<Account[]>([]);  const [contacts, setContacts] = useState<Contact[]>([]);  const [tab, setTab] = useState<TabKey>("coaches");  const [saveStatus, setSaveStatus] = useState<{    message: string;    type: "success" | "error";  } | null>(null);  /* Fetch all source data */  const fetchData = useCallback(async () => {    try {      const [cRes, aRes, tRes] = await Promise.all([        api.get("/salesforce/coaches/"),        api.get("/salesforce/accounts/"),        api.get("/salesforce/contacts/"),      ]);      setCoaches(cRes.data);      setAccounts(aRes.data);      setContacts(tRes.data);    } catch {      showStatus("Failed to load source data", "error");    }  }, []);  useEffect(() => {    fetchData();  }, [fetchData]);  /* Status flash helper */  const showStatus = (message: string, type: "success" | "error") => {    setSaveStatus({ message, type });    setTimeout(() => setSaveStatus(null), 2000);  };  /* ── Patch helpers ── */  const updateCoach = async (id: number, field: string, value: unknown) => {    try {      await api.patch(`/salesforce/coaches/${id}/`, { [field]: value });      showStatus("Saved", "success");      fetchData();    } catch {      showStatus("Save failed", "error");    }  };  const updateAccount = async (id: number, field: string, value: unknown) => {    try {      await api.patch(`/salesforce/accounts/${id}/`, { [field]: value });      showStatus("Saved", "success");      fetchData();    } catch {      showStatus("Save failed", "error");    }  };  const updateContact = async (id: number, field: string, value: unknown) => {    try {      await api.patch(`/salesforce/contacts/${id}/`, { [field]: value });      showStatus("Saved", "success");      fetchData();    } catch {      showStatus("Save failed", "error");    }  };  /* ── Render ── */  return (    <div className={s.wrapper}>      {/* Header */}      <div className={s.header}>        <h1 className={s.title}>          Simulated Salesforce Editor          {saveStatus && (            <span              className={`${s.saveStatus} ${                saveStatus.type === "success"                  ? s.saveStatusSuccess                  : s.saveStatusError              }`}            >              {saveStatus.message}            </span>          )}        </h1>        <p className={s.description}>          Modify source data here, then{" "}          <span className={s.descriptionHighlight}>            trigger a sync from Admin Dashboard          </span>{" "}          to test change detection. Changes made on this page update the          simulated Salesforce database directly — they will not appear in the          application until a sync is run.        </p>      </div>      {/* Tabs */}      <div className={s.tabs}>        {TAB_LABELS.map((t) => (          <button            key={t.key}            className={`${s.tab} ${tab === t.key ? s.tabActive : ""}`}            onClick={() => setTab(t.key)}          >            {t.label}          </button>        ))}      </div>      {/* Coaches table */}      {tab === "coaches" && (        <div className={s.tableWrap}>          {coaches.length === 0 ? (            <div className={s.empty}>No coaches in source data</div>          ) : (            <table className={s.table}>              <thead>                <tr>                  <th className={s.th}>Name</th>                  <th className={s.th}>Email</th>                  <th className={s.th}>Active</th>                </tr>              </thead>              <tbody>                {coaches.map((c) => (                  <tr key={c.id} className={s.tr}>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={c.name}                        onChange={(e) =>                          setCoaches((prev) =>                            prev.map((x) =>                              x.id === c.id                                ? { ...x, name: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) => updateCoach(c.id, "name", e.target.value)}                      />                    </td>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={c.email}                        onChange={(e) =>                          setCoaches((prev) =>                            prev.map((x) =>                              x.id === c.id                                ? { ...x, email: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) =>                          updateCoach(c.id, "email", e.target.value)                        }                      />                    </td>                    <td className={s.td}>                      <input                        type="checkbox"                        className={s.checkbox}                        checked={c.is_active}                        onChange={(e) =>                          updateCoach(c.id, "is_active", e.target.checked)                        }                      />                    </td>                  </tr>                ))}              </tbody>            </table>          )}        </div>      )}      {/* Accounts table */}      {tab === "accounts" && (        <div className={s.tableWrap}>          {accounts.length === 0 ? (            <div className={s.empty}>No accounts in source data</div>          ) : (            <table className={s.table}>              <thead>                <tr>                  <th className={s.th}>Account Name</th>                  <th className={s.th}>Industry</th>                  <th className={s.th}>Assigned Coach</th>                </tr>              </thead>              <tbody>                {accounts.map((a) => (                  <tr key={a.id} className={s.tr}>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={a.name}                        onChange={(e) =>                          setAccounts((prev) =>                            prev.map((x) =>                              x.id === a.id                                ? { ...x, name: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) =>                          updateAccount(a.id, "name", e.target.value)                        }                      />                    </td>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={a.industry}                        onChange={(e) =>                          setAccounts((prev) =>                            prev.map((x) =>                              x.id === a.id                                ? { ...x, industry: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) =>                          updateAccount(a.id, "industry", e.target.value)                        }                      />                    </td>                    <td className={s.td}>                      <select                        className={s.inlineSelect}                        value={a.coach ?? ""}                        onChange={(e) =>                          updateAccount(                            a.id,                            "coach",                            e.target.value ? Number(e.target.value) : null                          )                        }                      >                        <option value="">Unassigned</option>                        {coaches.map((c) => (                          <option key={c.id} value={c.id}>                            {c.name}                          </option>                        ))}                      </select>                    </td>                  </tr>                ))}              </tbody>            </table>          )}        </div>      )}      {/* Contacts table */}      {tab === "contacts" && (        <div className={s.tableWrap}>          {contacts.length === 0 ? (            <div className={s.empty}>No contacts in source data</div>          ) : (            <table className={s.table}>              <thead>                <tr>                  <th className={s.th}>Name</th>                  <th className={s.th}>Title</th>                  <th className={s.th}>Account</th>                  <th className={s.th}>Assigned Coach</th>                </tr>              </thead>              <tbody>                {contacts.map((c) => (                  <tr key={c.id} className={s.tr}>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={c.name}                        onChange={(e) =>                          setContacts((prev) =>                            prev.map((x) =>                              x.id === c.id                                ? { ...x, name: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) =>                          updateContact(c.id, "name", e.target.value)                        }                      />                    </td>                    <td className={s.td}>                      <input                        className={s.inlineInput}                        value={c.title}                        onChange={(e) =>                          setContacts((prev) =>                            prev.map((x) =>                              x.id === c.id                                ? { ...x, title: e.target.value }                                : x                            )                          )                        }                        onBlur={(e) =>                          updateContact(c.id, "title", e.target.value)                        }                      />                    </td>                    <td className={s.td}>{c.account_name}</td>                    <td className={s.td}>                      <select                        className={s.inlineSelect}                        value={c.coach ?? ""}                        onChange={(e) =>                          updateContact(                            c.id,                            "coach",                            e.target.value ? Number(e.target.value) : null                          )                        }                      >                        <option value="">Unassigned</option>                        {coaches.map((co) => (                          <option key={co.id} value={co.id}>                            {co.name}                          </option>                        ))}                      </select>                    </td>                  </tr>                ))}              </tbody>            </table>          )}        </div>      )}    </div>  );}
```

-    **Step 3: Verify TypeScript compiles**

```bash
cd frontendnpx tsc --noEmit
```

Confirm zero errors. Fix any unused imports or variables if flagged.

-    **Step 4: Commit**

```bash
git add frontend/src/pages/SourceEditorPage.tsx frontend/src/pages/SourceEditorPage.module.cssgit commit -m "feat: add source editor page with PentEdge-styled tabs and editable tables"
```

---

**Design notes:**

Pattern

PentEdge source

How applied

Tab navigation

`pages.module.css` `.tabs` / `.tab` / `.tabActive`

Identical structure: pill-shaped container with `--pm-card-bg`, active tab uses `--pm-accent-primary`

Table wrapper

`tables.module.css` `.tableWrap`

Card with `--pm-card-bg`, rounded `--radius-xl`, 1px `--pm-border`

Sticky header

`tables.module.css` `.th`

`position: sticky; top: 0` with `--pm-table-header-bg` and `--pm-table-header-color`

Hover rows

`tables.module.css` `.tr:hover`

`--pm-table-row-hover` background on hover

Inline inputs

`forms.module.css` `.input`

Same padding/border/radius/focus-ring using `--pm-input-*` variables

Select dropdowns

`forms.module.css` `.select` + `pages.module.css` `.filterSelect`

Custom chevron SVG via `background-image`, `appearance: none`, `--pm-input-*` variables

Checkbox

`pages.module.css` `.colCheckLabel input`

`accent-color: var(--pm-accent-primary)`

Empty state

`pages.module.css` `.empty`

Centered muted text

---

## Task 17: App Router + Wire Everything Together

**Files:**

-   Create: `frontend/src/components/LoadingSpinner.tsx`
-   Create: `frontend/src/components/ProtectedRoute.tsx`
-   Create: `frontend/src/components/AdminRoute.tsx`
-   Modify: `frontend/src/App.tsx`
-   Modify: `frontend/src/main.tsx`

---

-    **Step 1: Create `LoadingSpinner.tsx`**

`frontend/src/components/LoadingSpinner.tsx`:

```tsx
export default function LoadingSpinner() {  return (    <div      style={{        display: 'flex',        justifyContent: 'center',        alignItems: 'center',        height: '100vh',        background: '#f8f9fb',      }}    >      <div        style={{          width: 36,          height: 36,          border: '3px solid #e5e7eb',          borderTopColor: '#2563eb',          borderRadius: '50%',          animation: 'spin 0.6s linear infinite',        }}      />      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>    </div>  )}
```

-    **Step 2: Create `ProtectedRoute.tsx`**

`frontend/src/components/ProtectedRoute.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom'import { useAuth } from '../context/AuthContext'import LoadingSpinner from './LoadingSpinner'export default function ProtectedRoute() {  const { user, loading } = useAuth()  if (loading) return <LoadingSpinner />  if (!user) return <Navigate to="/login" replace />  return <Outlet />}
```

-    **Step 3: Create `AdminRoute.tsx`**

`frontend/src/components/AdminRoute.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom'import { useAuth } from '../context/AuthContext'import LoadingSpinner from './LoadingSpinner'export default function AdminRoute() {  const { user, loading } = useAuth()  if (loading) return <LoadingSpinner />  if (!user) return <Navigate to="/login" replace />  if (user.role !== 'admin') return <Navigate to="/" replace />  return <Outlet />}
```

-    **Step 4: Write `App.tsx` with routing**

`frontend/src/App.tsx`:

```tsx
import { lazy, Suspense } from 'react'import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'import { AuthProvider } from './context/AuthContext'import { ThemeProvider } from './context/ThemeContext'import LoadingSpinner from './components/LoadingSpinner'import ProtectedRoute from './components/ProtectedRoute'import AdminRoute from './components/AdminRoute'import CrmLayout from './components/CrmLayout'// Lazy-loaded page components for code splittingconst LoginPage = lazy(() => import('./pages/LoginPage'))const CoachDashboard = lazy(() => import('./pages/CoachDashboard'))const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))const AuditTrailPage = lazy(() => import('./pages/AuditTrailPage'))const BriefsPage = lazy(() => import('./pages/BriefsPage'))const SourceEditorPage = lazy(() => import('./pages/SourceEditorPage'))// Prefetch common pages after initial loadif (typeof window !== 'undefined') {  window.addEventListener(    'load',    () => {      setTimeout(() => {        import('./pages/CoachDashboard')        import('./pages/BriefsPage')      }, 1000)    },    { once: true }  )}export default function App() {  return (    <BrowserRouter>      <ThemeProvider>        <AuthProvider>          <Suspense fallback={<LoadingSpinner />}>            <Routes>              {/* Public route */}              <Route path="/login" element={<LoginPage />} />              {/* Protected routes — any authenticated user */}              <Route element={<ProtectedRoute />}>                <Route element={<CrmLayout />}>                  <Route path="/" element={<CoachDashboard />} />                  <Route path="/briefs" element={<BriefsPage />} />                </Route>              </Route>              {/* Admin-only routes */}              <Route element={<AdminRoute />}>                <Route element={<CrmLayout />}>                  <Route path="/admin" element={<AdminDashboard />} />                  <Route path="/audit" element={<AuditTrailPage />} />                  <Route path="/source" element={<SourceEditorPage />} />                </Route>              </Route>              {/* Catch-all redirect */}              <Route path="*" element={<Navigate to="/" replace />} />            </Routes>          </Suspense>        </AuthProvider>      </ThemeProvider>    </BrowserRouter>  )}
```

-    **Step 5: Update `main.tsx`**

`frontend/src/main.tsx`:

```tsx
import React from 'react'import ReactDOM from 'react-dom/client'import App from './App'import './styles/global.css'ReactDOM.createRoot(document.getElementById('root')!).render(  <React.StrictMode>    <App />  </React.StrictMode>)
```

-    **Step 6: Test full stack**

Terminal 1:

```bash
cd backendsource venv/Scripts/activateGEMINI_API_KEY=your-key-here python manage.py runserver
```

Terminal 2:

```bash
cd frontendnpm run dev
```

Test flow:

1.  Visit `/login` — LoginPage renders (no auth required)
2.  Login as `admin` / `admin123`
3.  Redirected to `/` — CoachDashboard renders inside CrmLayout (sidebar + header)
4.  Navigate to `/admin` — AdminDashboard renders (admin sees sync controls, all coaches)
5.  Navigate to `/audit` — AuditTrailPage renders (admin only)
6.  Navigate to `/source` — SourceEditorPage renders (admin only)
7.  Navigate to `/briefs` — BriefsPage renders (any authenticated user)
8.  Logout, login as `alice` / `alice123`
9.  Visit `/admin` directly — redirected to `/` (not admin)
10.  Visit `/audit` directly — redirected to `/` (not admin)
11.  Visit `/source` directly — redirected to `/` (not admin)
12.  Visit `/briefs` — BriefsPage renders scoped to Alice's data
13.  Visit `/nonexistent` — redirected to `/`
14.  Open DevTools Network tab — verify page chunks load lazily on first navigation

-    **Step 7: Verify TypeScript compiles clean**

```bash
cd frontendnpx tsc --noEmit
```

Fix any errors before proceeding. Common issues:

-   `AuthContext` must export a `user` object with a `role` property (used by `AdminRoute`)
    
-   `ThemeProvider` must exist in `context/ThemeContext.tsx`
    
-   `CrmLayout` must render `<Outlet />` for nested routes
    
-   All lazy-imported pages must use `export default`
    
-    **Step 8: Commit**
    

```bash
git add frontend/src/components/LoadingSpinner.tsx frontend/src/components/ProtectedRoute.tsx frontend/src/components/AdminRoute.tsx frontend/src/App.tsx frontend/src/main.tsxgit commit -m "feat: wire up app router with lazy loading, protected + admin routes, CrmLayout"
```

---

**Architecture notes:**

-   **Pattern mirrors PentEdge-CRM** -- `ProtectedRoute` and `AdminRoute` use the `<Outlet />` pattern (layout routes) instead of wrapper-component children. This lets `CrmLayout` nest cleanly as a second layout route.
-   **Code splitting** -- Every page is `React.lazy()` loaded. The `<Suspense>` boundary wraps all routes with `LoadingSpinner` as fallback. Each page only downloads when first visited.
-   **Route nesting** -- Two groups of `CrmLayout` children: one guarded by `ProtectedRoute` (coach + admin), one guarded by `AdminRoute` (admin only). Both render inside the same shell (sidebar + header + `<Outlet />`).
-   **Provider order** -- `BrowserRouter` > `ThemeProvider` > `AuthProvider` > `Suspense` > `Routes`. Auth needs to be inside the router so `<Navigate>` works. Theme wraps auth so auth components can use theme.
-   **Prefetching** -- After initial page load, `CoachDashboard` and `BriefsPage` chunks are prefetched (most common coach navigations) to eliminate loading spinners on subsequent clicks.

---

## Task 18: Make Audit Records Immutable

The PRD requires audit records to never be editable or deletable via API. Django admin could still delete them — we need to prevent that too.

**Files:**

-   Modify: `backend/sync/models.py`
    
-    **Step 1: Override delete on AuditRecord**
    

Add to the `AuditRecord` model in `backend/sync/models.py`:

```python
def delete(self, *args, **kwargs):    raise ValueError("Audit records cannot be deleted")def save(self, *args, **kwargs):    if self.pk:        raise ValueError("Audit records cannot be modified")    super().save(*args, **kwargs)
```

-    **Step 2: Verify no audit endpoints allow write operations**

Check that `sync/views.py` only has GET endpoints for audit records (already true in our implementation).

-    **Step 3: Commit**

```bash
git add sync/models.pygit commit -m "feat: enforce immutability on audit records"
```

---

## Task 19: Add CSRF Token Endpoint for Frontend

Django's session auth needs CSRF tokens. The frontend needs a way to get one before the first POST.

**Files:**

-   Modify: `backend/config/settings.py`, `backend/users/views.py`, `backend/users/urls.py`
    
-    **Step 1: Add CSRF view**
    

Add to `backend/users/views.py`:

```python
from django.middleware.csrf import get_token@api_view(["GET"])@permission_classes([AllowAny])def csrf_view(request):    return Response({"csrfToken": get_token(request)})
```

Add to `backend/users/urls.py`:

```python
path("csrf/", views.csrf_view, name="csrf"),
```

-    **Step 2: Add CSRF cookie settings**

Add to `backend/config/settings.py`:

```python
CSRF_COOKIE_HTTPONLY = False  # Allow JS to read the cookieCSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]
```

-    **Step 3: Update frontend to fetch CSRF on load**

In `frontend/src/context/AuthContext.tsx`, add to the initial useEffect:

```javascript
useEffect(() => {  // Get CSRF token first, then check auth  api.get("/auth/csrf/").then(() => {    api      .get("/auth/me/")      .then((res) => setUser(res.data))      .catch(() => setUser(null))      .finally(() => setLoading(false));  });}, []);
```

-    **Step 4: Commit**

```bash
git add backend/ frontend/git commit -m "feat: add CSRF token endpoint for frontend auth"
```

---

## Task 20: Environment Setup + Documentation

**Files:**

-   Create: `backend/.env.example`
    
-   Create: `README.md`
    
-    **Step 1: Create .env.example**
    

`backend/.env.example`:

```
GEMINI_API_KEY=your-gemini-api-key-hereDJANGO_SECRET_KEY=change-me-in-production
```

-    **Step 2: Write README.md**

`README.md`:

```markdown
# Coach-Client Reassignment Detection & HandlingA full-stack application that syncs coaching assignment data from a simulated Salesforce source, detects changes, maintains an immutable audit trail, enforces role-based access control, and generates AI-powered transition briefs.## Architecture**The core challenge:** Salesforce provides no change notifications. On every sync, the app pulls the entire dataset and diffs it against its local copy to determine what changed.**Two separate databases:**- `db_salesforce.sqlite3` — Simulated Salesforce (source of truth). The app reads from it but never writes to it.- `db.sqlite3` — Application database (local mirror + audit trail + briefs + users).**Tech stack:** Django 5 + DRF (backend), React 18 + Vite + TypeScript + CSS Modules (frontend), SQLite x2, Google Gemini (AI briefs).## Setup### Backend```bashcd backendpython -m venv venvsource venv/Scripts/activate  # Windows: venvScriptsactivatepip install -r requirements.txtpython manage.py migrate --database=defaultpython manage.py migrate --database=salesforcepython manage.py seed_salesforcepython manage.py create_test_usersexport GEMINI_API_KEY=your-key-herepython manage.py runserver
```

### Frontend

```bash
cd frontendnpm installnpm run dev
```

### Test Accounts

Username

Password

Role

admin

admin123

Admin

alice

alice123

Coach

bob

bob123

Coach

carol

carol123

Coach

dave

dave123

Coach

eve

eve123

Coach

## Testing Change Detection

1.  Login as admin
2.  Trigger initial sync (Admin Dashboard)
3.  Go to Source Editor — modify assignments (e.g., change FinanceHub's coach from Alice to Eve)
4.  Trigger sync again
5.  Check Audit Trail for detected changes
6.  Login as the affected coaches to verify access control

```
- [ ] **Step 3: Commit**```bashgit add .env.example README.mdgit commit -m "docs: add README and environment setup"
```

---

## Summary

Task

What it builds

Phase

1

Django project + dual DB config

Setup

2

Salesforce sim models + seed data

Phase 1

3

Salesforce sim CRUD API

Phase 1

4

User model + auth

Phase 3

5

Local coaching models + permissions

Phase 1/3

6

Sync engine + change detection + audit trail

Phase 1/2

7

Coaching API with access control

Phase 3

8

AI transition briefs (Gemini)

Phase 4

9

React frontend setup

Phase 3

10

Login page

Phase 3

11

Navbar

Phase 3

12

Coach dashboard

Phase 3

13

Admin dashboard

Phase 3

14

Audit trail page

Phase 2/3

15

Briefs page

Phase 4

16

Source editor page

Phase 1

17

App router + wire up

All

18

Audit record immutability

Phase 2

19

CSRF token handling

Phase 3

20

README + env setup

Docs