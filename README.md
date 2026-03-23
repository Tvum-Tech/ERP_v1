Here is your **clean, properly formatted, copy-paste ready `README.md`** 👇
(You can paste this directly into GitHub — formatting will render perfectly)

---

```markdown
# 📘 Lighting ERP System (BOQ & Configuration Engine)

---

## 🚀 Overview

This project is a **Django-based ERP system** designed for **Lighting Design, Configuration, and BOQ (Bill of Quantities) generation**.

It enables engineers and business teams to:

- Design lighting configurations at **Project → Area → SubArea level**
- Select products based on **technical filters**
- Automatically determine **compatible drivers and accessories**
- Generate **version-controlled configurations**
- Produce **audit-safe BOQ outputs**

---

## 🏗️ System Architecture

```

Project → Area → SubArea → Configuration → Products → Drivers/Accessories → BOQ

```

---

## 📦 Core Modules

### 1. 🏢 Projects Module

Manages project hierarchy.

#### Project
- `project_code` (auto-generated)
- Name, metadata

#### Area
- `area_code` (auto-generated)
- Linked to Project

#### SubArea
- `subarea_code` (auto-generated)
- Linked to Area

---

### 2. 💡 Configurations Module (Core Engine)

Handles lighting configurations with **versioning**.

#### LightingConfiguration
- Project, Area, SubArea
- Version number
- `is_active`
- `created_at`

#### ConfigurationDriver
- Linked driver + quantity

#### ConfigurationAccessory
- Linked accessory + quantity

---

### 3. 📦 Masters Module (Product Intelligence)

Central repository for all product-related data.

#### Product
- Mounting style
- Beam angle
- Lumen output
- CCT (Kelvin)
- Wattage
- Make, Order Code
- Electrical specs

#### Driver
- Max wattage
- Voltage/current range
- Constant type (CC/CV)
- Dimming protocol
- IP rating

#### Accessory
- Compatible mounting styles
- Diameter range
- IP compatibility

---

### 4. ⚙️ Compatibility Engine

A **pure service layer** that determines compatibility.

#### Functions
```

get_compatible_drivers(products)
get_compatible_accessories(products)

```

#### Key Rules
- Electrical compatibility (CC/CV)
- Total wattage validation
- Voltage/current matching
- Mounting compatibility
- IP rating constraints
- Intersection logic (**must support ALL products**)

---

### 5. 🔄 Versioning Engine

Ensures **ERP-grade immutability and audit compliance**.

#### Function
```

create_configuration_version()

```

#### Rules
- Every save creates a **new version**
- Previous versions become inactive
- No deletion allowed
- Full traceability maintained

---

### 6. 📊 BOQ Module

Generates Bill of Quantities from configurations.

#### BOQItem
- Product, Driver, Accessory
- Quantity
- Pricing

#### Integrity Rules
- Linked to configuration version
- Immutable
- Audit-safe

---

## 🌐 API Endpoints

### Configuration APIs
```

POST /api/configurations/save_batch/
POST /api/configurations/compatibility/
GET  /api/configurations/by-area/<area_id>/

```

### Project Hierarchy
```

GET /api/projects/
GET /api/areas/
GET /api/subareas/

```

### Product Filtering
```

POST /api/products/filter/

```

---

## 🧠 Configuration Workflow

1. Select **Project**
2. Select **Area**
3. Select **SubArea**
4. Apply filters:
   - Mounting Style
   - Beam Angle
   - Lumen Output
   - CCT
   - Wattage
5. Select Products
6. Fetch:
   - Compatible Drivers
   - Compatible Accessories
7. Save Configuration → **New Version Created**

---

## 🔐 Permissions

- `IsEditorOrReadOnly` → Default protection
- `AllowAny` → Used for compatibility endpoints (calculation APIs)

---

## 🧾 Code Generation Strategy

All hierarchy levels use **auto-generated codes**:

| Entity   | Example               |
|----------|----------------------|
| Project  | OFFICE-12-20260129   |
| Area     | LOBBY-3-20260129     |
| SubArea  | RECEPTION-7-20260129 |

✔ Immutable  
✔ Unique  
✔ ERP-compliant  

---

## 🧪 Tech Stack

- **Backend:** Django + Django REST Framework  
- **Database:** SQLite (Development)  
- **Architecture:** Service-based ERP design  
- **API:** RESTful  

---

## ⚠️ Important Notes

- Do NOT delete configurations → use versioning
- Compatibility logic is **deterministic and centralized**
- Migrations must always be applied after model changes
- Designed for **scalability and audit compliance**

---

## 🚀 Future Enhancements

- Approval Workflow (Draft → Approved)
- Pricing Engine (Margin, Discount)
- Rule Engine UI (No hardcoding)
- Excel / PDF BOQ export
- Role-based access control
- Analytics & reporting dashboards

---

## 👨‍💻 Author

Lighting ERP System – Built for scalable configuration, engineering validation, and BOQ automation.
```

---

## ✅ Done

You can now:

* Paste this into `README.md`
* Commit directly to GitHub
* Use it in interviews / portfolio

---

If you want next, I can:

* Add **architecture diagram (image-based)**
* Create **Swagger API docs**
* Add **setup & installation section**
* Make this **resume-ready project explanation**

Just tell me 👍
