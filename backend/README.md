# Finanzas backend (Fases 1-4, paridad completa con la app iOS)

API en FastAPI que concentra toda la lógica que antes vivía dentro de la app
SwiftUI: integración con Enable Banking (Open Banking / PSD2), sincronización
de saldos y movimientos, categorización automática (con CRUD completo de
categorías), presupuestos, alertas, análisis mensual con detección de
traspasos internos, y deudores (repartos de gastos entre personas).

Multiusuario: cada persona se registra con su email (`POST /api/auth/register`)
y ve solo sus propios bancos, movimientos, categorías, presupuestos y
deudores — aislados por `user_id` en cada tabla. Al registrarse se le siembra
automáticamente el catálogo de categorías por defecto.

## Desarrollo local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completa EB_APPLICATION_ID, EB_PRIVATE_KEY_PEM, etc.
alembic upgrade head   # crea el esquema (tablas incluida `users`)
uvicorn app.main:app --reload
```

Crea tu cuenta desde la propia PWA (pantalla "Crear cuenta") o directamente:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tu@email.com", "password": "tu-contraseña"}'
```

La documentación interactiva queda en `http://localhost:8000/docs`.

### Migraciones

Los cambios de esquema se gestionan con Alembic (`backend/alembic/`). Tras
cambiar `app/models.py`, genera una migración nueva con
`alembic revision --autogenerate -m "descripcion"`, revísala a mano (SQLite/
libsql necesita `render_as_batch=True`, ya configurado en `alembic/env.py`) y
aplícala con `alembic upgrade head`. En producción, `render.yaml` ya ejecuta
`alembic upgrade head` antes de arrancar el servidor en cada deploy.

## Registrar el redirect en Enable Banking

En el panel de Enable Banking, registra como redirect URL:
`{BACKEND_PUBLIC_URL}/api/banks/callback` (p. ej.
`https://tu-backend.onrender.com/api/banks/callback`). El backend recibe el
`code`/`state` directamente del banco, crea la sesión, vincula las cuentas y
redirige al navegador de vuelta a `{FRONTEND_ORIGIN}/accounts`. Ya no hace
falta la página puente en GitHub Pages que usaba la app iOS
(`docs/callback.html` + custom URL scheme): al ser web, el redirect HTTPS
llega directo al backend.

## Base de datos en producción

**Importante si vas a desplegar gratis:** el plan free de Render usa disco
efímero — cada vez que el servicio duerme por inactividad o se hace un
redeploy, el filesystem se reinicia y el archivo SQLite se borra. Railway ya
no ofrece un tier gratuito real (solo crédito de prueba que caduca).

Para mantener el despliegue 100% gratis y con datos persistentes, la opción
recomendada es [Turso](https://turso.tech) (SQLite distribuido, tier gratuito
persistente, compatible con SQLAlchemy vía el dialecto `sqlite+libsql://`):

```bash
pip install sqlalchemy-libsql
# DATABASE_URL=sqlite+libsql://tu-db.turso.io?authToken=...
```

Alternativa si prefieres no tocar nada del código: Postgres gratis en
[Neon](https://neon.tech) o [Supabase](https://supabase.com) (cambia
`DATABASE_URL` a `postgresql+psycopg://...` y añade `psycopg[binary]` a
requirements — SQLAlchemy no necesita más cambios porque no se usa SQL nativo
en ningún sitio de este backend).

## Endpoints

| Método | Ruta                                  | Auth | Descripción |
|--------|----------------------------------------|------|-------------|
| POST   | `/api/auth/login`                     | No   | Login con contraseña, devuelve JWT de sesión |
| GET    | `/api/banks/aspsps?country=ES`        | Sí   | Lista bancos disponibles (2700+ vía Enable Banking) |
| POST   | `/api/banks/authorize`                | Sí   | Inicia la autorización PSD2, devuelve la URL de consentimiento del banco |
| GET    | `/api/banks/callback`                 | No*  | Redirect del banco tras el consentimiento; vincula cuentas y redirige a la PWA |
| GET    | `/api/banks/connections`              | Sí   | Lista bancos conectados con sus cuentas |
| DELETE | `/api/banks/connections/{id}`         | Sí   | Elimina una entidad bancaria y todo su historial |
| GET    | `/api/accounts`                       | Sí   | Lista cuentas vinculadas (saldo, IBAN, visibilidad) |
| PATCH  | `/api/accounts/{account_uid}`         | Sí   | Cambia nombre / visibilidad de una cuenta |
| POST   | `/api/accounts/{account_uid}/refresh-balance` | Sí | Refresca el saldo desde Enable Banking |
| GET    | `/api/transactions`                   | Sí   | Lista movimientos (filtros: `account_uid`, `category_id`, `date_from`, `date_to`) |
| PATCH  | `/api/transactions/{entry_reference}` | Sí   | Recategoriza un movimiento a mano |
| POST   | `/api/transactions/sync`              | Sí   | Sincroniza movimientos nuevos de todas las cuentas |
| GET    | `/api/categories`                     | Sí   | Lista las categorías |
| POST   | `/api/categories`                     | Sí   | Crea una categoría (nombre + icono) |
| PATCH  | `/api/categories/{id}`                | Sí   | Edita nombre/icono de una categoría |
| DELETE | `/api/categories/{id}`                | Sí   | Borra una categoría (protegida: "Otros" no se puede borrar); reasigna sus movimientos a "Otros" y borra su presupuesto si tenía |
| PUT    | `/api/categories/reorder`             | Sí   | Reordena las categorías (`ordered_ids`) |
| POST   | `/api/transactions/recategorize-uncategorized` | Sí | Vuelve a aplicar las reglas de categorización a los movimientos no categorizados a mano |
| POST   | `/api/transactions/{entry_reference}/split` | Sí | Divide un movimiento entre uno o varios deudores |
| GET    | `/api/budgets`                        | Sí   | Lista categorías con su límite mensual (si tiene) y el gasto real del mes |
| PUT    | `/api/budgets/{category_id}`          | Sí   | Fija o edita el límite mensual de una categoría |
| DELETE | `/api/budgets/{category_id}`          | Sí   | Quita el límite de una categoría |
| GET    | `/api/alerts`                         | Sí   | Alertas calculadas al vuelo: presupuesto ≥80%, cargos duplicados, comisiones bancarias |
| GET    | `/api/analysis/summary?year=&month=`  | Sí   | Ingresos/gastos/neto del mes (excluyendo traspasos internos), últimos 6 meses, % de presupuesto, desglose por categoría |
| GET    | `/api/debtors`                        | Sí   | Lista deudores con su saldo (positivo = te deben) |
| POST   | `/api/debtors`                        | Sí   | Crea un deudor |
| GET    | `/api/debtors/{id}`                   | Sí   | Detalle de un deudor: saldo + historial |
| DELETE | `/api/debtors/{id}`                   | Sí   | Borra un deudor y su historial |
| POST   | `/api/debtors/{id}/entries`           | Sí   | Añade una deuda manual (importe positivo = a cobrar, negativo = a pagar) |
| POST   | `/api/debtors/{id}/payments`          | Sí   | Registra un pago (el signo se decide según a favor de quién esté el saldo) |
| POST   | `/api/debtors/{id}/cancel`            | Sí   | Cancela la deuda pendiente con un ajuste a 0 |
| DELETE | `/api/debtors/{id}/entries/{entry_id}`| Sí   | Borra un movimiento del historial de deuda |

\* protegido por un `state` firmado con expiración de 15 min, no por el
Authorization header (el banco no puede enviarlo).

## Paridad con la app iOS

Todo lo que hacía la app SwiftUI tiene equivalente aquí: cuentas (saldo,
visibilidad, eliminar entidad), movimientos (categorizar, recategorizar,
sincronizar, dividir con deudores), categorías (CRUD + reordenar +
recalcular), presupuestos, alertas, análisis (incluida la detección de
traspasos internos entre cuentas propias, `app/internal_transfers.py`, para
excluirlos de ingresos/gastos) y deudores (`app/routers/debtors.py`: deudas
manuales, pagos, cancelación, repartos de movimientos).
