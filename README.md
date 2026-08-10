# Finanzas

App personal de finanzas conectada a bancos reales vía Enable Banking
(Open Banking / PSD2). Originalmente una app SwiftUI+SwiftData para iOS;
migrada a una PWA (Next.js) + backend (FastAPI) para poder usarla desde
cualquier dispositivo, gratis — con **paridad funcional completa** respecto
a la app original.

## Plan de migración

No se reescribió todo de golpe — se migró por fases, manteniendo la app
existente usable mientras tanto:

1. **Backend** *(completada)* — toda la lógica de Enable Banking (autorización
   PSD2, sincronización de saldos y movimientos, categorización automática)
   vive en `backend/`, un servicio FastAPI independiente de cualquier cliente.
2. **PWA mínima** *(completada)* — Next.js con login, saldo y movimientos,
   consumiendo el backend de la fase 1.
3. **Resto de features** *(completada)* — presupuestos, alertas, análisis
   (dashboard mensual con gráficos y detección de traspasos internos),
   CRUD de categorías, deudores (repartir gastos), y todos los controles
   de cuentas (visibilidad, eliminar entidad) que faltaban en la Fase 2.
4. **Cerrar la app SwiftUI** *(lista para hacerse)* — ver más abajo.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js + TypeScript + Tailwind (PWA) |
| Backend | FastAPI (Python) |
| Base de datos | SQLite (ver `backend/README.md` para la nota sobre persistencia en producción) |
| Open Banking | Enable Banking |
| Despliegue frontend | Vercel |
| Despliegue backend | Render (free tier) |

```
PWA (iPhone / Android / PC)
        │
        ▼
     Backend (FastAPI)
        │
        ▼
   Enable Banking
        │
        ▼
       Banco
```

## Estructura del repo

- `backend/` — API FastAPI. Ver `backend/README.md` para cómo correrla en
  local, la lista completa de endpoints y cómo desplegarla.
- `frontend/` — PWA Next.js. Ver `frontend/README.md` para la estructura
  de páginas y las diferencias conscientes con la app iOS.
- `start-demo.bat` + `backend/seed_demo.py` — arranque de un vistazo en
  Windows con datos de ejemplo, sin necesitar credenciales reales de
  Enable Banking (ver más abajo).

## Puesta en marcha local

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar EB_APPLICATION_ID, EB_PRIVATE_KEY_PEM, etc.
uvicorn app.main:app --reload

# Frontend (otra terminal)
cd frontend && npm install
cp .env.example .env.local
npm run dev
```

Abre `http://localhost:3000`. En Windows, `start-demo.bat` hace todo esto
automáticamente y siembra datos de ejemplo (ver su cabecera).

Verificado end-to-end con navegador real, funcionalidad completa: login,
saldo (cuentas agrupadas por banco, conectar banco, refrescar saldo,
ocultar cuenta/saldo, eliminar entidad), movimientos (sincronizar,
recategorizar, dividir con deudores), presupuestos, alertas, análisis
(gráficos, traspasos internos excluidos, detalle de categoría), categorías
(crear/editar/borrar/reordenar/recalcular) y deudores (deuda manual,
registrar pago, cancelar deuda).

## Fase 4 — cerrar la app SwiftUI

La PWA cubre, con datos reales verificados, **todo** lo que hacía la app
iOS original: Cuentas, Movimientos, Análisis, Presupuestos, Alertas,
Categorías y Deudores — no queda ninguna feature de la app original sin su
equivalente aquí.

"Cerrar" la app SwiftUI es, en la práctica, dejar de abrirla y de mantener
su proyecto Xcode ahora que la PWA la cubre por completo — no es algo que
se pueda automatizar desde aquí: ese proyecto no es un repo al que esta
sesión tenga acceso, así que la decisión y el archivado quedan de tu lado.
Sugerencia concreta cuando quieras dar el paso: archiva el repo de la app
iOS en GitHub (o bórralo si no te importa perder el historial) y, si sigues
usando `docs/callback.html` en GitHub Pages para ese repo, puedes apagar
Pages también — la PWA ya no lo necesita (el redirect de Enable Banking va
directo al backend).

## Estado

- [x] Fase 1: backend con toda la lógica de Enable Banking
- [x] Fase 2: PWA mínima (login, saldo, movimientos)
- [x] Fase 3: presupuestos, alertas, análisis, categorías, deudores
- [x] Fase 4: lista para cerrarse (decisión manual, ver arriba) — **paridad
      funcional completa con la app SwiftUI**
