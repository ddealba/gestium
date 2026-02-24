# gestium

## Quickstart (Docker)

```bash
docker compose up --build
```

Con la stack arriba:

- UI: `http://localhost:5000/app/login`
- Credenciales smoke:
  - `adminA@test.com` / `Passw0rd!`
  - `viewerA@test.com` / `Passw0rd!`
  - `adminB@test.com` / `Passw0rd!`

## API smoke

Ejecuta el smoke desde el contenedor `api` sin configurar variables manuales:

```bash
docker compose exec api bash scripts/smoke.sh
```

Opcional: para correrlo contra otro host, define `BASE_URL`.

```bash
BASE_URL=http://localhost:5000 bash scripts/smoke.sh
```

## Modo demo (datos completos)

Para cargar un dataset más completo (empresas, empleados, casos, documentos, extracciones y eventos):

```bash
docker compose exec api flask seed --scenario demo
```

Este seed es idempotente (puedes ejecutarlo varias veces sin duplicar información clave).
