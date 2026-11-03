# API Contract (derived from the FastAPI backend + what the React frontend actually uses)

The Django API must keep this contract so the unchanged React frontend keeps working.
All URLs have **no trailing slash**. All endpoints except `/signup`, `/login`, `/healthy` require
`Authorization: Bearer <access_token>`. Errors are returned as `{"detail": "<human readable string>"}`.

Legend: **[FE]** = used by the React frontend, **[API]** = exists in FastAPI but frontend does not call it (still kept).

## Auth

| Method | URL | Request | Success response |
|---|---|---|---|
| POST [FE] | `/signup` | JSON `{username, email, password, confirm_password}` | `201 {"detail": "User 'x' successfully registered", "id": 1}` |
| POST [FE] | `/login` | **form-urlencoded** `username`, `password` (NOT JSON) | `200 {"access_token": "...", "token_type": "bearer"}` |

- Signup rules: username 3-30 chars `^\w+$`; email valid, max 75; password min 8; `confirm_password` must match.
- Signup errors (400): `"Email already registered."`, `"Username already taken."`.
- Login failure: `401 {"detail": "Invalid credentials."}`.
- Token: HS256 JWT, 30 min lifetime, claims `sub`=username, `id`=user id. Frontend stores `access_token` in localStorage; **any 401 logs the user out** (axios interceptor), so expired/invalid tokens must give 401 (not 403).
- Rate limits (slowapi): signup 5/min, login 10/min per IP.

## Users

| Method | URL | Request | Response |
|---|---|---|---|
| GET [FE] | `/users/me` | - | `200 {"id", "username", "email"}` |
| PATCH [FE] | `/users/change-password` | `{current_password, new_password}` | `200 {"msg": "Password updated successfully."}`; 400 `"Current password is incorrect."` / `"New password must be at least 8 characters."` |
| DELETE [FE] | `/users/me` | - | `204` (cascades to expenses and budgets) |
| PUT [API] | `/user` | `{username}` | `200 {"msg": "Username updated successfully.", "username"}`; 400 `"Username already in use."` |
| DELETE [API] | `/user` | - | `204` |

## Expenses

Allowed categories (case-insensitive input, stored Title Case): `Groceries, Leisure, Electronics, Utilities, Clothing, Health, Others`.

| Method | URL | Notes |
|---|---|---|
| GET [FE] | `/expenses` | Query: `from_date`, `to_date` (YYYY-MM-DD), `period` (`week`=7d, `month`=30d, `3months`=90d), `page` (>=1, default 1), `limit` (1-100, default 10). Ordered by date desc. Response: `{"expenses": [ {id, user_id, amount, category, description, date} ], "page", "limit", "total"}` |
| POST [FE] | `/expenses` | Body `{amount (>0), category, description?, date? (default today)}`. Response `201 {"message": "Expense $12.5 added.", "id": 7}` (NOT the full object) |
| PUT [FE] | `/expenses/{id}` | **Partial update semantics** (only fields sent are changed). Response `200 {"message": "Expense with ID 7 successfully updated."}`; 404 `"The expense doesn't exist."` |
| DELETE [FE] | `/expenses/{id}` | `204`; 404 if not found or not owned |
| GET [FE] | `/expenses/export/csv` | Same filters as list, no pagination. Header `Content-Disposition: attachment; filename=expenses_YYYYMMDD.csv`. Columns: `ID,Date,Category,Amount,Description` |
| GET [FE] | `/expenses/export/pdf` | Same filters. `application/pdf`, attachment. Table + total row |
| GET [FE] | `/expenses/summary/monthly?month=&year=` | Both required. `{"year","month","total_expenses","expense_count","average_expense"}` (zeros when empty) |
| GET [FE] | `/expenses/summary/category?month=&year=` | Both optional. `{"grand_total", "categories": [{category, total, count, percentage}]}` ordered by total desc |

- 400 `"'from_date' cannot be later than 'to_date'."`, 400 `"Invalid 'period' value. Accepted values are 'week', 'month', '3months'."`.
- A user can only see/modify their own expenses (other users' ids -> 404).
- Side effect: add/update triggers a budget-alert email for that expense's month (FastAPI did it synchronously in the request).

## Budgets

| Method | URL | Notes |
|---|---|---|
| POST [FE] | `/budgets` | Body `{category, amount (>0), month 1-12, year 2000-2100}`. **Upsert** on (user, category, month, year). Returns `201 {id, category, amount, month, year}` (201 even when updating) |
| GET [FE] | `/budgets?month=&year=` | Defaults to current month/year. **Plain JSON array** (not paginated) of `{id, category, amount, month, year}` |
| GET [FE] | `/budgets/alerts?month=&year=` | `{"month","year","alerts":[{category, budget_limit, spent, remaining, percentage_used, status}]}`; status `ok` (<80%), `warning` (>=80%), `exceeded` (spent > limit) |
| DELETE [FE] | `/budgets/{id}` | `204`; 404 `"Budget not found."` |

`/budgets/alerts` must be routed before `/budgets/{id}`.

## Health

`GET /healthy` -> `200 {"status": "Healthy"}`.

## Places where default Django/DRF behaviour differs from what the frontend expects

| # | Frontend expects | DRF default | Fix in Django |
|---|---|---|---|
| 1 | No trailing slash (`/expenses`) | `DefaultRouter` uses `/expenses/` and redirects | `DefaultRouter(trailing_slash=False)` |
| 2 | Login via **form-urlencoded** `username`/`password`, response `access_token` + `token_type` | simplejwt `TokenObtainPairView` takes JSON, returns `access` + `refresh` | Custom login view (+ `FormParser`) returning the old shape; refresh endpoint can exist extra |
| 3 | Login field named `username` | If email is the login, field would be `email` | Custom auth backend that accepts **username or email** in that field |
| 4 | Errors as `{"detail": "string"}` (`err.response.data.detail` is rendered directly) | Validation errors are `{"field": ["msg"]}`; also 422 in FastAPI vs 400 in DRF | Custom `EXCEPTION_HANDLER` flattening to a `detail` string |
| 5 | List response `{expenses, page, limit, total}` with `limit` param | `PageNumberPagination` -> `{count, next, previous, results}` with `page_size` | Custom pagination class (`page_size_query_param="limit"`, custom `get_paginated_response`) |
| 6 | `amount` as JSON **number** | `DecimalField` serialises as string | `COERCE_DECIMAL_TO_STRING = False` (or FloatField on output) |
| 7 | `POST /expenses` -> `{message, id}`, `PUT` -> `{message}` | ModelViewSet returns the object | Override `create`/`update` response |
| 8 | `PUT /expenses/{id}` partial | `PUT` is full update in DRF | Treat PUT as `partial=True` |
| 9 | `POST /budgets` upsert, always 201 | create-only, unique violation -> 400 | Custom `create` using `update_or_create` |
| 10 | `GET /budgets` is a bare array | Pagination would wrap it | Disable pagination on that viewset |
| 11 | `date` as `YYYY-MM-DD` | same | OK (`DateField`). Frontend does `.split('T')[0]`, harmless |
| 12 | 401 on bad/expired token | simplejwt returns 401 | OK (ensure no 403 for unauthenticated: JWT auth supplies `WWW-Authenticate`) |
| 13 | Expense response includes `user_id` | Serializer would omit FK unless declared | Include `user_id` read-only field |
| 14 | `/expenses/summary/*` and `/expenses/export/*` live under `/expenses` | Router would treat them as `{id}` | `@action(detail=False)` on the viewset (routes are matched before the detail route) |
| 15 | Vite dev proxy forwards only `/login /signup /expenses /budgets /users /health` | n/a | Django must be on port 8000; `/user` is not proxied (frontend does not use it) |
| 16 | In production the SPA is served by the backend from `frontend/dist` | n/a | Serve `dist` via WhiteNoise / catch-all template view (optional) |
