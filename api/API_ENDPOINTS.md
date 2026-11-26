# API Endpoints - Quila

Base URL: `http://localhost:8000/api/v1`

## Autenticación

Todos los endpoints (excepto login y register) requieren header:
```
Authorization: Bearer {access_token}
```

### POST /auth/register
Registrar nuevo usuario.

**Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "full_name": "string",
  "role": "ADMIN" | "MANAGER" | "OWNER"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "full_name": "string",
  "role": "string",
  "is_active": true,
  "created_at": "datetime"
}
```

---

### POST /auth/login
Iniciar sesión.

**Body (form-data):**
```
username: string
password: string
```

**Response:** `200 OK`
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

---

### GET /auth/perfil
Obtener perfil del usuario actual.

**Auth:** Required

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "full_name": "string",
  "role": "string",
  "is_active": true,
  "created_at": "datetime"
}
```

---

## Propiedades

### POST /properties
Crear propiedad.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "name": "string",
  "address": "string",
  "description": "string (optional)",
  "owner_id": "uuid (optional)",
  "base_price": 100.00
}
```
> `manager_id` se asigna automáticamente del usuario autenticado
> `base_price`: Precio BRUTO por noche (lo que paga el huésped cuando no aplica ninguna regla de precio)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "string",
  "address": "string",
  "description": "string",
  "manager_id": "uuid",
  "owner_id": "uuid",
  "base_price": 100.00,
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_active": true
}
```

---

### GET /properties
Listar todas las propiedades.

**Auth:** Required

**Query Params:**
- `skip`: int (default: 0)
- `limit`: int (default: 100, max: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "string",
    "address": "string",
    ...
  }
]
```

---

### GET /properties/my-managed
Listar propiedades gestionadas por el usuario actual.

**Auth:** Required

**Response:** `200 OK` (Array de propiedades)

---

### GET /properties/my-owned
Listar propiedades del usuario actual como dueño.

**Auth:** Required

**Response:** `200 OK` (Array de propiedades)

---

### GET /properties/{property_id}
Obtener detalle de propiedad.

**Auth:** Required

**Response:** `200 OK` (Objeto propiedad)

---

### PUT /properties/{property_id}
Actualizar propiedad.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "name": "string (optional)",
  "address": "string (optional)",
  "description": "string (optional)",
  "owner_id": "uuid (optional)",
  "base_price": 100.00
}
```

**Response:** `200 OK` (Objeto propiedad actualizado)

---

### DELETE /properties/{property_id}
Eliminar propiedad (soft delete).

**Auth:** Required (ADMIN)

**Response:** `204 No Content`

---

## Huéspedes

### POST /guests
Crear huésped.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "full_name": "string",
  "email": "string",
  "phone": "string (optional)",
  "document_type": "DU" | "EXTRANJERO",
  "document_number": "string"
}
```
> `document_number` se normaliza automáticamente (mayúsculas, sin espacios)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "document_type": "string",
  "document_number": "string",
  "created_at": "datetime"
}
```

---

### GET /guests
Listar todos los huéspedes.

**Auth:** Required

**Query Params:**
- `skip`: int (default: 0)
- `limit`: int (default: 100, max: 100)

**Response:** `200 OK` (Array de huéspedes)

---

### GET /guests/{guest_id}
Obtener detalle de huésped.

**Auth:** Required

**Response:** `200 OK` (Objeto huésped)

---

### PUT /guests/{guest_id}
Actualizar huésped.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "full_name": "string (optional)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "document_type": "DU" | "EXTRANJERO (optional)",
  "document_number": "string (optional)"
}
```

**Response:** `200 OK` (Objeto huésped actualizado)

---

### DELETE /guests/{guest_id}
Eliminar huésped.

**Auth:** Required (MANAGER o ADMIN)

**Response:** `204 No Content`

---

## Reservas

### POST /bookings
Crear reserva.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "property_id": "uuid",
  "guest_id": "uuid (optional)",
  "check_in": "YYYY-MM-DD",
  "check_out": "YYYY-MM-DD",
  "summary": "string",
  "description": "string (optional)",
  "status": "CONFIRMED" | "TENTATIVE" | "CANCELLED" (default: CONFIRMED),
  "source": "AIRBNB" | "BOOKING" | "DIRECT" | "MANUAL" (default: DIRECT)
}
```
> Valida automáticamente conflictos de fechas.
> `total_amount` se cotiza al crear la reserva (mismo cálculo que `price-quote`) y queda como snapshot: cambiar reglas de precio no lo modifica. Si la cotización falla (p. ej. propiedad inexistente), la reserva no se crea.

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "ical_uid": "string",
  "property_id": "uuid",
  "guest_id": "uuid",
  "check_in": "date",
  "check_out": "date",
  "summary": "string",
  "description": "string",
  "status": "string",
  "source": "string",
  "total_amount": "decimal",
  "paid_amount": "decimal | null",
  "external_id": "string",
  "ical_url": "string",
  "last_synced_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

### GET /bookings
Listar todas las reservas.

**Auth:** Required

**Query Params:**
- `skip`: int (default: 0)
- `limit`: int (default: 100, max: 100)

**Response:** `200 OK` (Array de reservas)

---

### GET /bookings/{booking_id}
Obtener detalle de reserva.

**Auth:** Required

**Response:** `200 OK` (Objeto reserva)

---

### PUT /bookings/{booking_id}
Actualizar reserva.

**Auth:** Required (MANAGER o ADMIN)

**Body:**
```json
{
  "guest_id": "uuid (optional)",
  "check_in": "YYYY-MM-DD (optional)",
  "check_out": "YYYY-MM-DD (optional)",
  "summary": "string (optional)",
  "description": "string (optional)",
  "status": "CONFIRMED" | "TENTATIVE" | "CANCELLED (optional)"
}
```
> Valida conflictos si se actualizan fechas

**Response:** `200 OK` (Objeto reserva actualizado)

---

### DELETE /bookings/{booking_id}
Cancelar reserva (soft delete).

**Auth:** Required (MANAGER o ADMIN)

**Response:** `204 No Content`

---

### GET /properties/{property_id}/bookings
Listar reservas de una propiedad específica.

**Auth:** Required

**Query Params:**
- `skip`: int (default: 0)
- `limit`: int (default: 100, max: 100)

**Response:** `200 OK` (Array de reservas)

---

## Códigos de Error

- `400` Bad Request - Validación fallida
- `401` Unauthorized - No autenticado o token inválido
- `403` Forbidden - Sin permisos suficientes
- `404` Not Found - Recurso no encontrado
- `409` Conflict - Conflicto (ej: email duplicado, fechas solapadas)
- `422` Unprocessable Entity - Error de validación de datos
- `500` Internal Server Error

---

## Tipos de Documento (DocumentType)

- `DU`: Documento Único (Argentina) - Solo números
- `EXTRANJERO`: Documento extranjero - Alfanumérico

## Estados de Reserva (BookingStatus)

- `CONFIRMED`: Confirmada
- `TENTATIVE`: Tentativa
- `CANCELLED`: Cancelada
- `PAID`: Pagada

## Fuentes de Reserva (BookingSource)

- `AIRBNB`: Importada de Airbnb
- `BOOKING`: Importada de Booking.com
- `DIRECT`: Creada directamente en el sistema
- `MANUAL`: Creada manualmente

## Roles de Usuario

- `ADMIN`: Acceso completo
- `MANAGER`: Gestión de propiedades, reservas y huéspedes

- `OWNER`: Solo visualización de propiedades

## Pricing (Precios Dinámicos)

### POST /properties/{id}/pricing-rules
Crear una regla de precio (temporada). Las reglas pueden superponerse.
**Auth:** Manager/Admin

**Body:**
```json
{
  "name": "Temporada Alta",
  "start_date": "2026-12-20",
  "end_date": "2027-01-05",
  "adjustment_type": "PERCENTAGE" | "FIXED_PRICE",
  "adjustment_value": 30.00,
  "priority": 10
}
```
> `start_date` y `end_date` son inclusive; `end_date >= start_date` (una regla puede cubrir un solo día).
> `adjustment_type = PERCENTAGE`: `adjustment_value` es el porcentaje sobre el precio base y debe ser mayor a -100 (30 = +30 %, -10 = -10 %).
> `adjustment_type = FIXED_PRICE`: `adjustment_value` es el precio por noche y debe ser mayor a 0.
> `priority`: entero, default 0.
> Errores de validación en el alta: `422`.

**Modelo de Precios (por noche, fecha `d`):**
- Base: el `PropertyBasePrice` vigente en `d`; si no hay, `Property.base_price`.
- Regla ganadora: entre las reglas que cubren `d`, la de mayor `priority`; si empatan, la creada más recientemente.
- `PERCENTAGE` → `base × (1 + valor / 100)`; `FIXED_PRICE` → `valor`; sin regla → base.
- El total de una estadía suma las noches de `[check_in, check_out)` y se redondea a 2 decimales.
- Las reservas existentes conservan su `total_amount`: editar o crear reglas no las modifica (incluidas las `PAID`).

### GET /properties/{id}/pricing-rules
Listar reglas de precio de una propiedad.
**Auth:** Authenticated

### PUT /pricing-rules/{id}
Actualizar una regla de precio. Permite solapamientos.
**Auth:** Manager/Admin

**Body:** `PricingRuleUpdate` (todos los campos opcionales: `name`, `start_date`, `end_date`, `adjustment_type`, `adjustment_value`, `priority`; `null` = sin cambios)
> Las fechas y el par tipo/valor se validan sobre la regla resultante: por ejemplo, pasar a `FIXED_PRICE` conservando un valor negativo devuelve `400`.

### DELETE /pricing-rules/{id}
Eliminar una regla de precio.
**Auth:** Manager/Admin

### GET /properties/{id}/calendar
Obtener calendario con precios calculados día por día.
**Auth:** Authenticated

**Query Params:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD

**Response:** Array de objetos diarios (`start_date` y `end_date` inclusive; `rule_name` es la regla ganadora de ese día)
```json
[
  {
    "date": "2026-01-01",
    "price": 100.00,
    "status": "AVAILABLE" | "RESERVED",
    "rule_name": "Año Nuevo" | null
  }
]
```

### GET /properties/{id}/financial-summary
Obtener resumen mensual de ingresos (sin costos).
**Auth:** Authenticated

**Query Params:**
- `year`: int (YYYY)
- `month`: int (1-12)

**Response:**
```json
{
  "year": 2026,
  "month": 1,
  "days_in_month": 31,
  "occupied_days": 20,
  "occupancy_rate": 64.52,
  "total_bookings": 5,
  "total_income": 2000.00,
  "paid_income": 1200.00,
  "pending_income": 800.00
}
```
> Considera las reservas no canceladas con noches dentro del mes. El ingreso de cada reserva es `paid_amount` si está registrado, si no su `total_amount`, prorrateado por las noches que caen en el mes; las reservas sin total guardado usan los precios por noche vigentes.
> `paid_income`: reservas `PAID`. `pending_income`: el resto. `total_income = paid_income + pending_income`.
