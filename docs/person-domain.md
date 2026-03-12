# Dominio Person

`Person` representa la identidad real del cliente final dentro de un tenant y es el centro del dominio del portal.

## Relación principal

```text
Person
 ├─ PersonCompanyRelation
 ├─ Employee
 ├─ Document
 ├─ Case
 ├─ PersonRequest
 └─ User (portal)
```

## Reglas arquitectónicas

1. El portal resuelve identidad con `PortalContext` (`user_id`, `person_id`, `client_id`).
2. La visibilidad se centraliza en `PortalVisibilityService`.
3. Servicios de portal (`PortalService`, `PortalDashboardService`) solo componen datos dentro de ese perímetro.

## Módulo portal consolidado

```text
app/modules/portal/
  portal_routes.py
  portal_service.py
  portal_visibility_service.py
  portal_dashboard_service.py
  portal_audit_service.py
  context.py
  schemas.py
```

El directorio `modules/frontoffice` queda únicamente como compatibilidad legacy.
