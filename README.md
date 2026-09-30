# Ofertas al Día

Panel para encontrar ofertas de Mercado Libre México, revisarlas y preparar su publicación en una comunidad pública de WhatsApp.

## Tecnologías

- `public/index.html`: estructura del panel.
- `public/styles.css`: diseño adaptable a celular y computadora.
- `public/app.js`: filtros, edición y apertura de WhatsApp.
- `app.py`: API Flask, autenticación, buscador y acceso a PostgreSQL.
- `db/schema.sql`: estructura de la base de datos.
- `vercel.json`: búsqueda automática cada tres horas.

## Desarrollo local en Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Abre `http://localhost:3000`. Sin variables configuradas, la aplicación trabaja con datos de demostración en memoria.

## Configuración en Vercel

1. Importa el repositorio como un proyecto nuevo.
2. Crea una base PostgreSQL desde el Marketplace de Vercel; Neon es compatible.
3. Ejecuta [`db/schema.sql`](db/schema.sql) en el editor SQL de la base.
4. Agrega en Vercel las variables descritas en [`.env.example`](.env.example).
5. Crea una aplicación en el portal de desarrolladores de Mercado Libre y configura `MERCADOLIBRE_ACCESS_TOKEN`.
6. Despliega el proyecto.

Vercel detecta automáticamente Flask y ejecuta `app.py` en el runtime oficial de Python. El cron llama a `/api/cron/scan` cada tres horas y se autentica con `CRON_SECRET`.

`ADMIN_USER` y `ADMIN_PASSWORD` protegen tanto el panel como la API. En producción, el servidor se niega a mostrar el panel si esas variables no existen.

## Enlaces de afiliado

El buscador importa productos mediante la API de Mercado Libre. El enlace monetizado debe proceder de la Central de Afiliados, la Barra de Afiliados o una integración oficial habilitada para tu cuenta. La aplicación no modifica URLs ni inventa identificadores de atribución.

## Envío a WhatsApp

Al pulsar **Enviar**, la oferta se marca como enviada y se abre WhatsApp con el texto completo. El administrador selecciona la comunidad y confirma el envío dentro de WhatsApp.
