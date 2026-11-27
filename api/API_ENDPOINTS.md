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
  "base_price": 100.00,
  "max_guests": 4,
  "amenities": ["Wifi", "Parrilla"],
  "check_in_time": "14:00",
  "check_out_time": "10:00",
  "cancellation_policy": "string (optional)",
  "house_rules": "string (optional)"
}
```
> `manager_id` se asigna automáticamente del usuario autenticado
> Campos de catálogo (`max_guests` > 0, `amenities` lista de strings, horarios `HH:MM`, `cancellation_policy`, `house_rules`): todos opcionales y `null` en propiedades existentes. Se publican en `GET /public/catalog` y los usa el chatbot; una propiedad con `max_guests` nulo nunca aparece en la búsqueda del bot.
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
  "max_guests": 4,
  "amenities": ["Wifi", "Parrilla"],
  "check_in_time": "14:00:00",
  "check_out_time": "10:00:00",
  "cancellation_policy": "string | null",
  "house_rules": "string | null",
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
  "base_price": 100.00,
  "max_guests": "int | null (optional)",
  "amenities": "string[] | null (optional)",
  "check_in_time": "HH:MM | null (optional)",
  "check_out_time": "HH:MM | null (optional)",
  "cancellation_policy": "string | null (optional)",
  "house_rules": "string | null (optional)"
}
```
> Enviar `null` explícito borra un campo de catálogo; omitirlo lo deja igual.

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
> `total_amount` se cotiza al crear la reserva (mismo cálculo que `price-quote`) y queda como snapshot: cambiar reglas de precio no lo modifica. Solo se recalcula si cambian las fechas de la reserva (`PUT /bookings/{booking_id}`). Si la cotización falla (p. ej. propiedad inexistente), la reserva no se crea.

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
  "expires_at": "datetime | null",
  "guests": "int | null",
  "lead_name": "string | null",
  "lead_phone": "string | null",
  "lead_email": "string | null",
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
> Valida conflictos si se actualizan fechas. Si las fechas cambian de verdad, `total_amount` se vuelve a cotizar con las reglas vigentes (mismo cálculo que al crear); si la cotización falla, la actualización falla. Reenviar las mismas fechas o cambiar otros campos no toca el total. En reservas `PAID` se recalcula `total_amount` pero nunca se modifican `paid_amount`, `paid_at` ni `payment_method`.

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
- `CHATBOT`: Hold creado por el chatbot (`POST /bot/holds`)

## Holds del chatbot

- Un hold es una reserva `TENTATIVE` con `source=CHATBOT`, `guest_id` nulo, datos del lead (`lead_name`, `lead_phone`, `lead_email`), `guests` y `expires_at = ahora + HOLD_TTL_HOURS` (default 24).
- **Expiración lazy:** antes de la búsqueda/cotización/hold del bot, de crear, editar o aceptar reservas y del calendario, toda reserva `TENTATIVE` con `expires_at` vencido pasa a `CANCELLED` en la misma transacción. Las reservas sin `expires_at` nunca se tocan. No hay scheduler.
- `POST /bookings/{booking_id}/accept` confirma el hold y borra `expires_at` (un hold ya vencido no se puede aceptar). Pagarlo o pasarlo a `CONFIRMED`/`PAID` por `PUT` también borra `expires_at`. Cancelarlo conserva `expires_at`: el panel lo muestra como "Vencido" cuando la fecha ya pasó.

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


---

## Catálogo público

### GET /public/catalog
Catálogo en markdown de las propiedades activas, pensado para que el chatbot lo ingiera (RAG).

**Auth:** Ninguna (público)

**Response:** `200 OK`, `Content-Type: text/plain; charset=utf-8`
```markdown
# Catálogo de cabañas

## Cabaña del Lago

Vista al lago.

- Dirección: Ruta 40 km 3
- Capacidad: hasta 4 huéspedes
- Comodidades: Wifi, Parrilla
- Check-in: desde las 14:00
- Check-out: hasta las 10:00
- Precio: desde $150.00 por noche

### Política de cancelación

Reembolso total hasta 7 días antes.

### Reglas de la casa

No se permiten fiestas.
```
> El precio es el precio base vigente hoy (sin reglas de temporada). Nunca expone ids de managers u owners, emails, reservas ni huéspedes.

---

## Integración chatbot (/bot)

Contrato máquina a máquina para chatv2. Router separado de los endpoints con JWT de usuario.

**Auth:** `Authorization: Bearer <BOT_API_KEY>` (variable de entorno, comparación en tiempo constante).
- Sin header o clave incorrecta → `401`.
- `BOT_API_KEY` vacía → todas las rutas `/bot/*` responden `503` `{"detail": "bot integration disabled"}` (nunca quedan abiertas).

**Convención de resultados:** los resultados de negocio son siempre `200 OK` (chatv2 solo ve `Tool returned HTTP <code>` en respuestas no 2xx).
- Éxito: el body incluye `"ok": true`.
- Falla de negocio: `{"ok": false, "reason": "<code>", "message": "<texto en español>"}`.
- Body mal formado (JSON inválido, campo faltante, `guests` < 1, fecha no ISO, UUID o email inválido) → también `200` con `reason: "invalid_input"` y un `message` que nombra los campos inválidos, para que el bot pueda corregir los argumentos. Solo en `/bot/*`: el resto de la API sigue respondiendo `422`.
- La clave se valida antes: sin clave válida un body mal formado responde `401` (o `503` si el bot está deshabilitado), nunca `200`.
- `lead_email` vacío o solo espacios se trata como ausente (`null`).

| `reason` | Cuándo |
|----------|--------|
| `invalid_input` | Body mal formado; `message` lista los campos (ej. `check_in`) |
| `invalid_dates` | `check_in` anterior a hoy (fecha de negocio en `BUSINESS_TIMEZONE`, por defecto `America/Argentina/Buenos_Aires`) o `check_out <= check_in` |
| `property_not_found` | Cabaña inexistente o inactiva |
| `capacity_unknown` | La cabaña no tiene `max_guests` cargado |
| `over_capacity` | `guests` > `max_guests` |
| `unavailable` | Las fechas se solapan con una reserva o un hold vigente (`POST /bot/holds`) |

**Fechas:** ISO `YYYY-MM-DD`; `check_out` es exclusivo (noches = `check_out - check_in`). Los montos se serializan como strings decimales (`"450.00"`).

### GET /bot/health
Verifica que la clave esté configurada y sea aceptada. **Response:** `{"ok": true}`

### POST /bot/availability
Cabañas activas con `max_guests >= guests` (las de capacidad nula se excluyen) sin reservas ni holds vigentes que se solapen, cada una cotizada.

**Body:**
```json
{"check_in": "2026-12-10", "check_out": "2026-12-13", "guests": 3}
```

**Response:** `200 OK`
```json
{
  "ok": true,
  "nights": 3,
  "options": [
    {"property_id": "uuid", "name": "Cabaña del Lago", "max_guests": 4, "total_amount": "450.00", "nightly_average": "150.00"}
  ]
}
```
> Sin resultados: `{"ok": true, "nights": 3, "options": []}`. Falla posible: `invalid_dates`.

### POST /bot/quote
Cotiza una cabaña e indica si las fechas están libres.

**Body:**
```json
{"property_id": "uuid", "check_in": "2026-12-10", "check_out": "2026-12-13", "guests": 3}
```

**Response:** `200 OK`
```json
{"ok": true, "property_id": "uuid", "name": "Cabaña del Lago", "nights": 3, "total_amount": "450.00", "available": true}
```
> Fallas posibles: `invalid_dates`, `property_not_found`, `capacity_unknown`, `over_capacity`.

### POST /bot/holds
Pre-reserva la cabaña para un lead. Crea una reserva `TENTATIVE`, `source=CHATBOT`, con snapshot de `total_amount`, que vence a las `HOLD_TTL_HOURS` horas salvo que una persona la acepte desde el panel.

**Body:**
```json
{
  "property_id": "uuid",
  "check_in": "2026-12-10",
  "check_out": "2026-12-13",
  "guests": 3,
  "lead_name": "Ana Pérez",
  "lead_phone": "+54 9 11 5555-0000",
  "lead_email": "ana@example.com (optional)",
  "notes": "string (optional)"
}
```
> `summary` = `"Hold chatbot - <lead_name>"`, `notes` → `description`, `guest_id` nulo.

**Response:** `200 OK`
```json
{
  "ok": true,
  "hold_id": "uuid",
  "property_id": "uuid",
  "name": "Cabaña del Lago",
  "check_in": "2026-12-10",
  "check_out": "2026-12-13",
  "nights": 3,
  "total_amount": "450.00",
  "expires_at": "2026-11-27T15:04:05.123456Z"
}
```
> Fallas posibles: `invalid_dates`, `property_not_found`, `capacity_unknown`, `over_capacity`, `unavailable` (incluye la carrera en la que el constraint `EXCLUDE` rechaza el insert).

### Herramientas para registrar en chatv2

chatv2 llama cada herramienta con `POST <endpoint_url>`, el JSON de argumentos como body y `Authorization: <auth_header>`. Reemplazar `https://example.com` por la URL pública de la API y `<BOT_API_KEY>` por la clave configurada. Cada objeto sigue el schema `ToolCreate` de chatv2.

```json
[
  {
    "name": "search_availability",
    "description": "Busca cabañas disponibles para un rango de fechas y cantidad de huéspedes. Devuelve cada opción con su precio total y promedio por noche. Usala antes de ofrecer cabañas. Si ok es false, explicale al huésped el message.",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "check_in": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de llegada, formato YYYY-MM-DD. No puede ser en el pasado."},
        "check_out": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de salida, formato YYYY-MM-DD. Debe ser posterior a check_in (la noche de salida no se cobra)."},
        "guests": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Cantidad de huéspedes."}
      },
      "required": ["check_in", "check_out", "guests"],
      "additionalProperties": false
    },
    "endpoint_url": "https://example.com/bot/availability",
    "auth_header": "Bearer <BOT_API_KEY>"
  },
  {
    "name": "get_quote",
    "description": "Cotiza una cabaña puntual para un rango de fechas y cantidad de huéspedes, e indica si esas fechas están libres (available). Usá el property_id devuelto por search_availability. Si ok es false, explicale al huésped el message.",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "property_id": {"type": "string", "format": "uuid", "pattern": "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", "description": "Id de la cabaña (property_id de search_availability)."},
        "check_in": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de llegada, formato YYYY-MM-DD."},
        "check_out": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de salida, formato YYYY-MM-DD."},
        "guests": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Cantidad de huéspedes."}
      },
      "required": ["property_id", "check_in", "check_out", "guests"],
      "additionalProperties": false
    },
    "endpoint_url": "https://example.com/bot/quote",
    "auth_header": "Bearer <BOT_API_KEY>"
  },
  {
    "name": "create_hold",
    "description": "Pre-reserva una cabaña para el huésped y bloquea las fechas por tiempo limitado (ver expires_at) hasta que una persona del equipo confirme la reserva y el pago. Usala solo cuando el huésped confirmó cabaña, fechas y cantidad de huéspedes, y te dio su nombre y teléfono. Si ok es false con reason unavailable, ofrecé otras fechas o cabañas.",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "property_id": {"type": "string", "format": "uuid", "pattern": "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", "description": "Id de la cabaña elegida."},
        "check_in": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de llegada, formato YYYY-MM-DD."},
        "check_out": {"type": "string", "format": "date", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "description": "Fecha de salida, formato YYYY-MM-DD."},
        "guests": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Cantidad de huéspedes."},
        "lead_name": {"type": "string", "minLength": 1, "maxLength": 255, "description": "Nombre y apellido del huésped."},
        "lead_phone": {"type": "string", "minLength": 3, "maxLength": 50, "description": "Teléfono de contacto del huésped, idealmente con código de país."},
        "lead_email": {"type": "string", "format": "email", "maxLength": 255, "description": "Email del huésped (opcional)."},
        "notes": {"type": "string", "maxLength": 2000, "description": "Comentarios del huésped para el equipo (opcional)."}
      },
      "required": ["property_id", "check_in", "check_out", "guests", "lead_name", "lead_phone"],
      "additionalProperties": false
    },
    "endpoint_url": "https://example.com/bot/holds",
    "auth_header": "Bearer <BOT_API_KEY>"
  }
]
```

Para ingerir el catálogo en el RAG de chatv2, registrar la URL `https://example.com/public/catalog` (GET sin autenticación).
