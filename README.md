# gestium

## Smoke test (curl)

Script de validación rápida sin Postman ni dependencias extra (solo bash + python).

```bash
BASE_URL=http://localhost:5000 \
CLIENT_A_ID=<uuid-tenant-a> \
CLIENT_B_ID=<uuid-tenant-b> \
bash scripts/smoke.sh
```

Notas:
- `BASE_URL` es opcional (default: `http://localhost:5000`).
- `CLIENT_A_ID` y `CLIENT_B_ID` deben ser los UUIDs de los tenants seeded "Tenant A" y "Tenant B".
