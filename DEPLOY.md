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

## 6. Monitorización de errores (opcional, Sentry)

Backend y frontend tienen soporte para Sentry ya integrado en el código,
desactivado por defecto (si no defines el DSN, no hace nada).

1. Crea una cuenta gratis en [sentry.io](https://sentry.io) (plan Developer,
   gratis) y un proyecto Python (para el backend) y otro Next.js (frontend).
2. Backend, en Render → Environment: añade `SENTRY_DSN` con el DSN del
   proyecto Python.
3. Frontend, en Vercel → Environment Variables: añade
   `NEXT_PUBLIC_SENTRY_DSN` con el DSN del proyecto Next.js (Production +
   Preview) y haz **Redeploy**.

## 7. Backups de la base de datos

Turso hace backups automáticos en cada commit — no hay que configurar nada.
En el plan gratuito, puedes restaurar a cualquier punto de las **últimas 24
horas** (point-in-time recovery). Para restaurar: crea una base nueva a
partir de la existente en el timestamp deseado con `turso db create --from-db
pwa-finanzas --timestamp <ISO-8601>`, y apunta `DATABASE_URL` a la nueva base
si confirmas que es la que quieres conservar.

## 8. Rotar secretos tras las pruebas

`APP_JWT_SECRET` y `APP_PASSWORD_HASH` se generaron durante el desarrollo
inicial — una vez todo funciona, genera unos nuevos (mismos comandos del
paso 2) y actualízalos en Render. Al cambiar `APP_JWT_SECRET` se invalidan
todas las sesiones activas (tendrás que volver a hacer login).

## 9. Recuperar contraseña por email (opcional, Resend)

Sin configurar esto, "olvidé mi contraseña" no falla, pero tampoco llega
ningún email (queda logueado en Render, nada más).

1. Crea cuenta gratis en [resend.com](https://resend.com) (3.000 emails/mes
   gratis).
2. **API Keys** → crea una → cópiala.
3. En Render → Environment: añade `RESEND_API_KEY` con esa clave.
4. Importante — **sin verificar un dominio propio en Resend**, el email
   remitente por defecto (`onboarding@resend.dev`) solo puede enviar al
   email con el que te registraste en Resend, no a cualquier usuario de la
   app. Si vas a tener varias personas usando la app, en Resend →
   **Domains** → añade y verifica un dominio tuyo, y luego define
   `RESEND_FROM_EMAIL` en Render como `Finanzas <noreply@tudominio.com>`.

## 10. Cerrar el registro abierto (opcional, código de invitación)

Por defecto cualquiera con el enlace puede crear una cuenta. Para exigir un
código:

1. En Render → Environment: añade `REGISTRATION_INVITE_CODE` con el código
   que quieras (cualquier texto, es solo un secreto compartido — no hace
   falta que sea complejo, no protege datos sensibles, solo filtra quién
   puede registrarse).
2. Comparte ese código solo con quien quieras que se registre.
3. Para dejar de exigirlo, borra la variable (o vacíala) en Render.
