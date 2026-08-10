# Finanzas frontend (Fases 1-4, paridad completa con la app iOS)

PWA en Next.js (App Router) + TypeScript + Tailwind con todas las
funciones de la app SwiftUI original: login, saldo, movimientos,
presupuestos, alertas, análisis y deudores, consumiendo el
[backend](../backend). Instalable en iPhone/Android/PC (manifest + service
worker de app-shell).

## Desarrollo local

```bash
cd frontend
npm install   # genera package-lock.json (no versionado en este repo)
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL -> tu backend local
npm run dev
```

Abre `http://localhost:3000`. Necesitas el backend corriendo (ver
`../backend/README.md`) con `FRONTEND_ORIGIN` apuntando a esta misma URL, o
las peticiones fallarán por CORS.

## Estructura

- `src/lib/api.ts` — fetch wrapper que añade el `Authorization: Bearer` y
  normaliza errores.
- `src/lib/auth.tsx` — contexto de sesión (token en `localStorage`, uso
  personal single-user).
- `src/lib/icons.tsx` — mapeo de nombres de icono (los mismos ~30 que la app
  iOS, vía `lucide-react`) + componente `CategoryIcon`.
- `src/components/AuthGuard.tsx` — redirige a `/login` si no hay sesión.
- `src/app/login` — formulario de contraseña.
- `src/app/accounts` — "Saldo": total agregado, cuentas agrupadas por banco,
  conectar un banco nuevo (`src/components/BankPicker.tsx`), refrescar
  saldo, ocultar cuenta/saldo por cuenta, eliminar una entidad bancaria.
- `src/app/movimientos` — lista agrupada por día, botón "Sincronizar"; tocar
  un movimiento abre `src/components/TransactionDetail.tsx` para
  recategorizar o dividirlo entre deudores (reparto igual o por cantidad
  fija, como `SplitTransactionView` en la app iOS). Los movimientos
  divididos llevan una insignia "Dividido".
- `src/app/presupuestos` — límite mensual por categoría con barra de
  progreso vs. gasto real; tocar una categoría permite fijar/editar/quitar
  el límite.
- `src/app/alertas` — lista de alertas calculadas por el backend.
- `src/app/analisis` — dashboard mensual: navegación mes a mes, totales +
  neto, traspasos internos excluidos ("no computable"), % de presupuesto
  previsto, gráfico de barras de los últimos 6 meses
  (`src/components/BarChart.tsx`) y donut de gasto por categoría
  (`src/components/DonutChart.tsx`); tocar una categoría abre su detalle
  (`src/components/CategoryDetail.tsx`) con los movimientos de ese mes.
  Los gráficos son SVG hechos a mano — sin librería de charts, para no
  añadir peso a una PWA que se instala en el móvil.
- `src/app/categorias` — CRUD de categorías: crear (nombre + icono, grid de
  30 iconos vía `CategoryEditor.tsx`), editar, borrar (protege "Otros",
  reasigna sus movimientos), reordenar (flechas arriba/abajo — sustituye al
  drag-and-drop de `CategoryReorderView` de iOS, más simple de implementar
  en web y accesible igual), y "Recalcular categorías de movimientos
  existentes".
- `src/app/deudores` + `src/app/deudores/[id]` — lista de deudores con
  saldo ("Te debe"/"Le debes"), detalle con historial, registrar pago,
  añadir deuda manual, marcar deuda como cancelada.
- `src/app/mas` — pestaña "Más" (Alertas, Deudores, Categorías, Salir):
  con 8 destinos en total no caben todos en la barra inferior, igual que
  la app iOS los agrupaba bajo su propio "Más" automático de UITabBar.
- `public/manifest.json` + `public/sw.js` — instalabilidad como PWA (el SW
  solo cachea el app-shell del propio origen; las respuestas del backend,
  en otro origen, nunca se cachean).

## Despliegue (Vercel, gratis)

1. Importa el repo en Vercel, root directory `frontend/`.
2. Variable de entorno `NEXT_PUBLIC_API_BASE_URL` = URL pública del backend.
3. En el backend, `FRONTEND_ORIGIN` debe apuntar al dominio que te dé Vercel
   (para CORS y para el redirect tras conectar un banco).

## Diferencias conscientes con la app iOS

Paridad funcional completa; estos detalles cambian de forma deliberada al
migrar de iOS a web, sin perder funcionalidad:

- Reordenar categorías es con flechas arriba/abajo en vez de arrastrar
  (drag-and-drop táctil fiable cross-browser es bastante más código para
  el mismo resultado).
- Confirmaciones destructivas (borrar categoría, borrar deudor, eliminar
  banco) usan `window.confirm()` en vez de una hoja de confirmación nativa.
- `public/icons/icon.svg` es un icono provisional (una "F" sobre fondo
  oscuro) en vez del icono real de la app. Funciona para instalar en
  Android/desktop; para que el icono de pantalla de inicio de iOS se vea
  nítido, sustitúyelo por un `apple-touch-icon.png` de 180×180 real y
  referéncialo en `src/app/layout.tsx` (`icons.apple`).
