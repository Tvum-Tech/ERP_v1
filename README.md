📘 ERP_v1 – Enterprise Resource Planning System
📌 1. Project Overview

ERP_v1 is a modular, scalable Enterprise Resource Planning system built using Django REST Framework and Vue.js, designed to manage multiple business domains such as CRM, HRM, Finance, and Inventory.

The system follows a Domain-Driven Design (DDD-inspired architecture) rather than traditional Django MVT, enabling better scalability, maintainability, and separation of concerns.

🎯 Key Objectives
Build a modular ERP platform
Enable plug-and-play integrations (e.g., external CRM like HubSpot)
Separate business logic from infrastructure
Support scalable enterprise architecture
🏗️ 2. System Architecture
🔷 High-Level Architecture
User → Frontend (Vue.js)
→ Backend API (Django DRF)
→ Business Logic Layer
→ Repository Layer
→ Database (PostgreSQL)
🔷 Backend Architecture (DDD Inspired)

Instead of Django’s default MVT, the system is structured into:

Core Layers:
Layer Responsibility
Domain Core business entities & rules
Logic Business logic processing
Repository Database interaction
Handlers (Views) API endpoints
Tests Unit & integration tests

👉 This separation allows:

Clean code
Easy scaling
Replaceable infrastructure
🔷 Request Flow
Request → URL Router → View (Handler)
→ Logic Layer
→ Repository Layer
→ Database
→ Response → Client
🔷 Advanced Design Feature
🔥 Repository Factory Pattern
Uses use_case_type
Dynamically switches data source (e.g., DB vs external CRM)

👉 Example:

use_case_type=“default” → DB
use_case_type=“hubspot” → External API

✅ This enables plug-and-play integrations without changing views

🧩 3. Project Structure
ERP_v1/
│
├── core/
│ ├── apps/
│ │ ├── crm/
│ │ ├── hrm/
│ │ ├── fintech/
│ │ └── common/
│ │
│ ├── frontend/
│ │ ├── crm/
│ │ ├── hrm/
│ │
│
├── manage.py
├── requirements.txt
├── .env-example

🛠️ 4. Technology Stack
Backend
Python
Django
Django REST Framework
Pydantic (validation instead of DRF serializers)
PostgreSQL
Djoser (authentication)
Swagger (API docs)
Frontend
Vue.js
JavaScript

⚙️ 5. Setup & Installation
🔷 Backend Setup
git clone https://github.com/Tvum-Tech/ERP_v1.git
cd ERP_v1

cp .env-example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
🔷 Frontend Setup
cd core/frontend/crm
npm install
npm run serve
🔷 Run Tests
pytest

📡 6. API Documentation
Swagger UI:
http://localhost:8000/api/v1/docs/

👉 APIs are auto-documented using OpenAPI/Swagger.

🧱 7. Functional Modules (Roadmap)
Module Status
CRM (Customer Management) Ongoing
HRM (Human Resources) Planned
SCM (Supply Chain) Planned
Inventory Planned
Finance / Accounting Planned

🔐 8. Security & Authentication
Token-based authentication using Djoser
Environment-based configuration (.env)
Separation of concerns ensures reduced risk exposure

🚀 9. Deployment Strategy (Recommended)
Suggested Setup:
Backend → AWS EC2 / Docker
Database → AWS RDS (PostgreSQL)
Frontend → Vercel / Netlify
Static files → AWS S3

📈 10. Scalability Design
Key Highlights:
Modular apps (crm, hrm, etc.)
Replaceable repositories (DB / external APIs)
Independent business logic layer
API-first architecture

👉 This allows:

Microservices transition (future)
Easy scaling per module

🧪 11. Testing Strategy
Pytest-based testing
Layer-wise testing:
Domain tests
Logic tests
Repository tests
API tests

⚠️ 12. Known Limitations
HRM, SCM modules not fully implemented
Frontend limited to CRM module
No CI/CD pipeline defined yet

🔮 13. Future Enhancements
Full ERP module implementation
Multi-tenant architecture
Role-based access control (RBAC)
Event-driven architecture (Kafka / Celery)
AI-driven automation (fits your current work 🔥)

🧠 14. Key Engineering Decisions
Decision Reason
Avoid Django MVT Better scalability
Use Pydantic Strong validation
Repository Pattern Decoupling DB
Factory Pattern External integrations

🧾 15. Conclusion

ERP_v1 is designed as a modern, scalable ERP system with:

Clean architecture (DDD-inspired)
Modular extensibility
API-first design
Enterprise-ready patterns
