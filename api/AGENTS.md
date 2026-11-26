# CLAUDE.md — FastAPI Sub-Agent

Este archivo complementa el CLAUDE.md raíz. Contiene las convenciones exactas del código para trabajar dentro de `api/`.

**Referencia de endpoints:** Consultar `API_ENDPOINTS.md` en este directorio para la especificación completa de la API (rutas, bodies, responses, roles requeridos).

## Estructura de Capas

Cada dominio (property, booking, guest, pricing, base_price) sigue exactamente estas 5 capas:

```
models/{domain}.py          → SQLAlchemy ORM model
schemas/{domain}.py         → Pydantic schemas (Base, Create, Update, Response)
repositories/{domain}_repository.py → Data access (queries async)
services/{domain}_service.py        → Business logic + validaciones
routers/{domain}.py         → Endpoints HTTP
```

**Flujo obligatorio:** Router → Service → Repository → DB. Los routers NUNCA acceden a la base de datos directamente.

## Patrones de Código

### Model (SQLAlchemy)

```python
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class NuevoModelo(Base):
    __tablename__ = "nuevo_modelos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # campos...
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
```

- PKs: siempre `UUID(as_uuid=True)` con `default=uuid.uuid4`
- Timestamps: `server_default=func.now()` para created_at, `onupdate=func.now()` para updated_at
- Soft delete: campo `is_active = Column(Boolean, default=True)`
- Monetarios: `Numeric(10, 2)`

### Schema (Pydantic)

```python
from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class DomainBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)

class DomainCreate(DomainBase):
    pass  # o campos adicionales para creación

class DomainUpdate(BaseModel):  # NO hereda de Base
    name: Optional[str] = Field(None, min_length=1, max_length=200)

class DomainResponse(DomainBase):
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
```

- `Create` hereda de `Base`
- `Update` hereda de `BaseModel` directamente (todos los campos Optional)
- `Response` hereda de `Base` y agrega `id`, timestamps, `is_active`
- Siempre `Config.from_attributes = True` en Response

### Repository

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.domain import Domain
from schemas.domain import DomainCreate, DomainUpdate
import uuid

class DomainRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DomainCreate, **extra_fields) -> Domain:
        obj = Domain(**data.model_dump(), **extra_fields)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> Domain | None:
        result = await self.db.execute(select(Domain).where(Domain.id == id))
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Domain]:
        result = await self.db.execute(
            select(Domain).where(Domain.is_active == True).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, data: DomainUpdate) -> Domain | None:
        obj = await self.get_by_id(id)
        if not obj:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID) -> Domain | None:
        obj = await self.get_by_id(id)
        if not obj:
            return None
        obj.is_active = False  # soft delete
        return obj
```

- Recibe `AsyncSession` en `__init__`
- `flush()` + `refresh()` después de crear/actualizar (NO `commit()`, lo hace `get_db`)
- Delete es soft delete (`is_active = False`)
- Retorna `None` si no encuentra, NUNCA lanza excepciones

### Service

```python
from models.domain import Domain
from schemas.domain import DomainCreate, DomainUpdate
from repositories.domain_repository import DomainRepository
from exceptions.general import NotFoundException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

class DomainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DomainRepository(db)

    async def create(self, data: DomainCreate, **kwargs) -> Domain:
        return await self.repo.create(data, **kwargs)

    async def get(self, id: uuid.UUID) -> Domain:
        obj = await self.repo.get_by_id(id)
        if not obj:
            raise NotFoundException("Recurso no encontrado")
        return obj

    async def update(self, id: uuid.UUID, data: DomainUpdate) -> Domain:
        obj = await self.repo.update(id, data)
        if not obj:
            raise NotFoundException("Recurso no encontrado")
        return obj

    async def delete(self, id: uuid.UUID) -> Domain:
        obj = await self.repo.delete(id)
        if not obj:
            raise NotFoundException("Recurso no encontrado")
        return obj
```

- Recibe `AsyncSession` en `__init__`, instancia el Repository
- Lanza `NotFoundException` cuando el repo retorna `None`
- Validaciones de negocio van aquí (conflictos de fechas de reservas, validaciones sobre valores combinados en updates parciales, etc.)
- Usar excepciones de `exceptions/general.py`:
  - `NotFoundException` (404)
  - `ForbiddenException` (403)
  - `BadRequestException` (400)
  - `ConflictException` (409)
  - `UnauthorizedException` (401)

### Router

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from schemas.domain import DomainCreate, DomainUpdate, DomainResponse
from services.domain_service import DomainService
from core.database import get_db
from dependencies.auth import get_current_user, has_role
from models.user import User as Usuario
from core.roles import Role

router = APIRouter(prefix="/domain", tags=["domain"])

@router.post("/", response_model=DomainResponse, status_code=201)
async def create(
    data: DomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(has_role(Role.ROLE_EXAMPLE))
):
    return await DomainService(db).create(data)

@router.get("/", response_model=List[DomainResponse])
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return await DomainService(db).list(skip, limit)
```

- `APIRouter(prefix="/domain", tags=["domain"])`
- Instancia `Service(db)` en cada endpoint (NO como dependencia global)
- Auth: `get_current_user` para solo autenticado, `has_role(Role.XXX)` para permisos
- Paginación: `skip` y `limit` con `Query()`
- Status codes: 201 para POST, 204 para DELETE, 200 implícito para GET/PUT

### Registrar nuevo router en main.py

```python
from routers import nuevo_router
app.include_router(nuevo_router.router)
```


## Enums Disponibles (core/enums.py)

| Enum | Valores |
|------|---------|
| `UserRole` | `admin`, `manager`, `owner` |
| `BookingStatus` | `CONFIRMED`, `TENTATIVE`, `CANCELLED`, `PAID` |
| `BookingSource` | `AIRBNB`, `BOOKING`, `DIRECT`, `MANUAL`, `CHATBOT` |
| `BotFailureReason` | `unavailable`, `over_capacity`, `invalid_dates`, `property_not_found`, `capacity_unknown` |
| `DocumentType` | `DU`, `EXTRANJERO` |
| `PaymentMethod` | `CASH`, `TRANSFER`, `CARD`, `OTHER` |
| `PricingAdjustmentType` | `PERCENTAGE`, `FIXED_PRICE` |

## Precios (services/pricing_service.py)

- Precio por noche de la fecha `d`: base = `PropertyBasePrice` vigente en `d`, o `Property.base_price`.
- Regla ganadora: entre las reglas que cubren `d` (fechas inclusive), la de mayor `priority`; empate → la más reciente (`created_at`, luego `id`). Las reglas pueden superponerse.
- `PERCENTAGE` → `base * (1 + value/100)` (value > -100); `FIXED_PRICE` → `value` (> 0); sin regla → base.
- Reglas y precios base se traen una sola vez por rango (`PricingRuleRepository.get_overlapping`, ya ordenado por precedencia) y se resuelven en memoria: nada de una query por noche. Lo usan la cotización, el calendario y el resumen financiero.
- `Booking.total_amount` es un snapshot tomado al crear la reserva; si la cotización falla, la creación falla. Cambiar reglas no modifica reservas existentes (tampoco las PAID).
- El resumen financiero es solo de ingresos (`total_income`, `paid_income`, `pending_income`, ocupación).

## Integración chatbot (routers/bot.py, routers/public.py)

- `GET /public/catalog` (sin auth): markdown de propiedades activas armado por `services/catalog_service.py`. Solo datos para huéspedes: nunca ids de managers/owners, emails, reservas ni huéspedes.
- `/bot/*` es un router aparte de los de JWT de usuario: `dependencies=[Depends(require_bot_key)]` (`dependencies/bot_auth.py`). Espera `Authorization: Bearer <BOT_API_KEY>` y compara con `hmac.compare_digest`. Sin header o clave incorrecta → 401; `BOT_API_KEY` vacía → 503 `bot integration disabled`.
- **Resultados de negocio siempre HTTP 200.** `BotService` (`services/bot_service.py`) **devuelve** `BotFailure` (`{"ok": false, "reason", "message"}`) en lugar de lanzar excepciones; los mensajes en español viven en `services/bot_outcomes.py`. 422 solo para bodies mal formados. Los response models son `Union[Exito, BotFailure]`.
- Fechas: `check_in >= hoy` (fecha del servidor), `check_out > check_in`, `check_out` exclusivo.
- Disponibilidad: `PropertyRepository.get_available` (una sola query con `NOT EXISTS` sobre reservas no canceladas) + `PricingService.quote_property` por candidata (precios por rango, sin N+1). `max_guests` nulo → excluida.
- **Holds:** reserva `TENTATIVE`, `source=CHATBOT`, `guest_id` nulo, datos del lead y `expires_at = now(UTC) + HOLD_TTL_HOURS`. El insert corre en un SAVEPOINT (`db.begin_nested()`): si el `EXCLUDE` lo rechaza, se devuelve `unavailable` y la transacción del request sigue usable.
- **Expiración lazy:** `BookingRepository.expire_stale_holds()` pasa a `CANCELLED` los `TENTATIVE` con `expires_at` vencido (nunca toca reservas sin `expires_at`). Se llama al inicio de availability/quote/hold del bot, crear/editar/aceptar reservas y el calendario, en la misma transacción. Aceptar, pagar o pasar a `CONFIRMED`/`PAID` borra `expires_at`; cancelar lo conserva.
- Tests: fixtures `bot_key` / `bot_headers` en `tests/conftest.py`; helpers en `tests/bot_helpers.py`. La DB de test recrea el constraint `excl_bookings_no_overlap` tras `create_all`.

## Permisos (core/roles.py)

| Role | Valores disponibles en `role_hierarchy` |
|------|---------|
| `Role.ROLE_PROPERTY_CREATE` | ADMIN, MANAGER, OWNER |
| `Role.ROLE_PROPERTY_UPDATE` | ADMIN, MANAGER, OWNER |
| `Role.ROLE_PROPERTY_DELETE` | ADMIN, MANAGER, OWNER |
| `Role.ROLE_BOOKING_CREATE` | ADMIN, MANAGER |
| `Role.ROLE_BOOKING_UPDATE` | ADMIN, MANAGER |
| `Role.ROLE_BOOKING_DELETE` | ADMIN, MANAGER |
| `Role.ROLE_BOOKING_SYNC` | ADMIN, MANAGER |
| `Role.ROLE_GUEST_MANAGE` | ADMIN, MANAGER |

## Seguridad (core/security.py)

- Hashing: Argon2 via `passlib`
- JWT: `python-jose` con HS256
- Token payload: `{"sub": "<user_uuid>", "role": "<role>", "exp": <timestamp>}`
- Funciones: `get_password_hash()`, `verify_password()`, `create_access_token()`, `decode_token()`

## Base de Datos

- **Engine:** asyncpg + SQLAlchemy async
- **Sesión:** `get_db()` auto-commit en éxito, auto-rollback en excepción
- **NO usar `session.commit()`** en repos/services — lo maneja `get_db()`
- **Usar `flush()` + `refresh()`** para obtener valores generados por la DB
- **Migraciones:** Alembic (async). Archivos en `alembic/`. Ejecutar con `alembic revision --autogenerate -m "mensaje"` y `alembic upgrade head`
- **Entrypoint:** `entrypoint.sh` ejecuta `alembic upgrade head` antes de iniciar uvicorn
- **Constraints DB:** CHECK, FK con `ondelete`, EXCLUDE (bookings overlap), indexes compuestos — definidos en models y migración

## Deploy

- `Dockerfile`: Multi-stage build (builder → final slim), usuario `appuser` no-root
- `docker-compose.yml`: servicio `web` (FastAPI) + `db` (PostgreSQL 16), healthchecks, restart policies
- `api/requirements.txt`: dependencias con version pins
- Comando: `docker compose up --build`

## Tests

- **Framework:** pytest + pytest-asyncio, httpx AsyncClient con ASGITransport
- **DB real:** PostgreSQL `quila_test_db` (creada por `deploy/init-test-db.sql`)
- **Ejecución:** `docker exec quila_api pytest tests/ -v`
- **Estructura:** `tests/conftest.py` (fixtures: client, users, tokens, property), un archivo por dominio
- **Limpieza:** Cada test limpia todas las tablas vía `autouse` fixture

## Idioma

- Mensajes de error y términos de dominio en **español**
- Nombres de código (clases, funciones, variables) en **inglés**
- Endpoints paths en **inglés** (excepto `/auth/perfil`)
