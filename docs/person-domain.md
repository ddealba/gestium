# Person Domain

`Person` es la identidad real del cliente final dentro de un tenant. Es el centro del dominio del portal (frontoffice), y todas las reglas de visibilidad parten de esta entidad.

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

## Entidades vinculadas

- **PersonCompanyRelation**: define vínculos persona↔empresa (por ejemplo `owner`) y habilita contexto de empresa en portal.
- **Employee**: representa rol laboral de la persona en una empresa concreta.
- **Document**: puede estar ligado a `person_id`, `employee_id` o `company_id`; su visibilidad portal se calcula desde relaciones de `Person`.
- **Case**: expediente personal o de empresa visible para la persona según su alcance.
- **PersonRequest**: solicitudes/tareas asignadas directamente a la persona.
- **User (portal)**: credencial de acceso al portal; siempre debe apuntar a un `person_id` válido.

## Principio arquitectónico

Para evitar fugas de datos:

1. Todo acceso de portal usa `PortalContext` (`user_id`, `person_id`, `client_id`).
2. Toda lectura de datos visibles pasa por `PortalVisibilityService`.
3. Servicios de portal componen resultados sobre ese perímetro de visibilidad.
