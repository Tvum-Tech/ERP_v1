
```markdown
# 📘 Lighting ERP API Documentation (Swagger)



## 🚀 Overview

This API powers the **Lighting ERP System**, enabling:

- Project & hierarchy management (Project → Area → SubArea)
- Lighting configuration with versioning
- Compatibility engine (Drivers & Accessories)
- BOQ generation and pricing
- Role-based access & audit logs

Base URL:
```

[http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)

```

Swagger UI:
```

[http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)

```


## 🔐 Authentication APIs

### Login
```

POST /api/auth/login/

````

**Request**
```json
{
  "username": "string",
  "password": "string"
}
````

**Response**

```json
{
  "access": "jwt_token",
  "refresh": "refresh_token"
}
```


### Refresh Token

```
POST /api/auth/refresh/
```


## 🏢 Projects & Hierarchy

### Projects

```
GET    /api/projects/projects/
POST   /api/projects/projects/
GET    /api/projects/projects/{id}/
PUT    /api/projects/projects/{id}/
DELETE /api/projects/projects/{id}/
```


### Areas

```
GET    /api/projects/areas/
POST   /api/projects/areas/
GET    /api/projects/areas/{id}/
PUT    /api/projects/areas/{id}/
DELETE /api/projects/areas/{id}/
```


### SubAreas

```
GET    /api/projects/subareas/
POST   /api/projects/subareas/
GET    /api/projects/subareas/{id}/
PUT    /api/projects/subareas/{id}/
DELETE /api/projects/subareas/{id}/
```


## 💡 Configurations Module

### Create Configuration

```
POST /api/configurations/
```


### Save Batch (ERP Core)

```
POST /api/configurations/save_batch/
```

✔ Creates versioned configuration
✔ Handles products, drivers, accessories


### Get Configurations

```
GET /api/configurations/
GET /api/configurations/{id}/
```


### Filter Configurations

```
GET /api/configurations/by-project/{project_id}/
GET /api/configurations/by-area/{area_id}/
GET /api/configurations/by-subarea/{subarea_id}/
```


## ⚙️ Compatibility Engine

### Multi-Product Compatibility

```
POST /api/configurations/compatibility/
```

**Request**

```json
{
  "product_ids": [1, 2, 3]
}
```

**Response**

```json
{
  "drivers": [...],
  "accessories": [...]
}
```

✔ Returns only compatible drivers & accessories
✔ Uses ERP rule engine


### Single Product Compatibility

```
GET /api/configurations/compatibility/product/{product_id}/
```


## 📦 Masters Module

### Products

```
GET    /api/masters/products/
POST   /api/masters/products/
GET    /api/masters/products/{prod_id}/
PUT    /api/masters/products/{prod_id}/
DELETE /api/masters/products/{prod_id}/
```

### Drivers

```
GET    /api/masters/drivers/
POST   /api/masters/drivers/
GET    /api/masters/drivers/{id}/
PUT    /api/masters/drivers/{id}/
DELETE /api/masters/drivers/{id}/
```


### Accessories

```
GET    /api/masters/accessories/
POST   /api/masters/accessories/
GET    /api/masters/accessories/{id}/
PUT    /api/masters/accessories/{id}/
DELETE /api/masters/accessories/{id}/
```


## 📊 BOQ Module

### Generate BOQ

```
POST /api/boq/generate/{project_id}/
```


### BOQ Items

```
GET    /api/boq/items/
POST   /api/boq/items/
GET    /api/boq/items/{id}/
PUT    /api/boq/items/{id}/
DELETE /api/boq/items/{id}/
```


### Update Price

```
PATCH /api/boq/items/{boq_item_id}/price/
```


### Approve BOQ

```
POST /api/boq/approve/{boq_id}/
```


### Apply Margin

```
POST /api/boq/apply-margin/{boq_id}/
```


### Export BOQ

```
GET /api/boq/export/excel/{boq_id}/
GET /api/boq/export/pdf/{boq_id}/
```


### BOQ Summary

```
GET /api/boq/summary/{project_id}/
GET /api/boq/summary/detail/{boq_id}/
```

### BOQ Versions

```
GET /api/boq/versions/{project_id}/
```


## 🔐 Users & Roles

### Users

```
GET    /api/users/
POST   /api/users/
GET    /api/users/{id}/
PUT    /api/users/{id}/
DELETE /api/users/{id}/
```


### Roles

```
GET    /api/roles/
POST   /api/roles/
GET    /api/roles/{id}/
PUT    /api/roles/{id}/
DELETE /api/roles/{id}/
```


### Assign Role

```
POST /api/users/{id}/assign-role/
```


### Assign Permissions

```
POST /api/roles/{id}/assign-permissions/
```


## 📜 Audit & Common

### Current User

```
GET /api/common/me/
```


### Audit Logs

```
GET /api/common/audit/logs/
```


## 🔑 Authentication

Most endpoints require:

```
Authorization: Bearer <access_token>
```


## 🧠 Key ERP Concepts

* **Versioning** → Every configuration is immutable
* **Compatibility Engine** → Central rule system
* **BOQ Integrity** → Linked to configuration versions
* **Hierarchy** → Project → Area → SubArea
* **Audit Logs** → Full traceability


## ⚠️ Notes

* Do NOT modify DB manually
* Always use API for consistency
* Versioning ensures audit compliance
* Compatibility rules are deterministic


## 🚀 Swagger UI

👉 Access full interactive docs:

```
http://127.0.0.1:8000/api/docs/
```

## 👨‍💻 Author

Lighting ERP API – Built for scalable lighting design, configuration, and BOQ automation.

```

## ✅ What you now have

- Full Swagger → Human-readable doc
- GitHub-ready
- Client/demo-ready
- Interview-ready

```
