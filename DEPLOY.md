# Guía de despliegue a producción

Estos pasos requieren tus propias cuentas y credenciales (Render, Vercel,
Turso, Enable Banking) — nadie más que tú puede crearlas o pegar los
secretos, así que están escritos para que los ejecutes tú directamente en
cada dashboard.

## 1. Base de datos persistente (Turso)

```bash
curl -sSfL https://get.tur.so/install.sh | bash
turso auth login
turso db create pwa-finanzas
turso db show pwa-finanzas --url
turso db tokens create pwa-finanzas
```

Con la URL y el token construye:

```
DATABASE_URL=sqlite+libsql://<url-sin-protocolo>?authToken=<token>
```

## 2. Backend en Render

1. Entra en [render.com](https://render.com) → **New → Blueprint** → conecta
   el repo `eadrianjm16/PWA-Finanzas`. Render detecta `render.yaml` en la
   raíz y crea el servicio `pwa-finanzas-backend` (`rootDir: backend`).
2. En la pestaña **Environment** del servicio, rellena a mano (no van en el
   blueprint, son secretos):
   - `DATABASE_URL` → la de Turso del paso 1.
   - `EB_APPLICATION_ID` y `EB_PRIVATE_KEY_PEM` → tus credenciales reales de
     Enable Banking.
   - `APP_JWT_SECRET` → genera uno tú: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   - `APP_PASSWORD_HASH` → genera el hash de tu contraseña real (no la
     escribas en ningún chat): `python -c "from app.security import hash_password; print(hash_password('tu-contraseña'))"`.
   - `FRONTEND_ORIGIN` → la URL que te dé Vercel en el paso 3 (puedes volver
     a editar esta variable después).
   - `BACKEND_PUBLIC_URL` → la URL que te dé Render para este servicio (algo
     como `https://pwa-finanzas-backend.onrender.com`).
3. Deploy. Comprueba `https://<tu-backend>.onrender.com/docs`.

## 3. Registrar el redirect en Enable Banking

En el panel de Enable Banking, añade como redirect URL:
`{BACKEND_PUBLIC_URL}/api/banks/callback` (la del paso anterior).

## 4. Frontend en Vercel

1. En [vercel.com](https://vercel.com) → **Add New → Project** → importa el
   mismo repo, **Root Directory: `frontend`**.
2. Variable de entorno: `NEXT_PUBLIC_API_BASE_URL` = la URL del backend en
   Render (paso 2).
3. Deploy. Copia la URL final de Vercel y vuelve a Render para actualizar
   `FRONTEND_ORIGIN` con esa URL exacta (si no, el backend rechazará las
   peticiones por CORS).

## 5. Verificación

- Login en la PWA con tu contraseña real.
- Conectar un banco real desde `/accounts` → completar el flujo de Enable
  Banking hasta el final (no solo generar la URL de autorización).
- Confirmar que tras un redeploy de Render los datos siguen ahí (prueba de
  que Turso está funcionando, no SQLite efímero).
