ESTIMATION_EXAMPLES = [
    {
        "meeting_summary": (
            "Una cadena de 3 tiendas de ropa necesita una plataforma web interna para "
            "gestionar inventario: alta de productos con tallas y colores, stock por "
            "tienda, traspasos entre tiendas, alertas de stock bajo y un dashboard de "
            "ventas. Login para empleados con dos roles (administrador y vendedor). "
            "No necesitan app móvil; se usará desde el navegador del mostrador."
        ),
        "estimation": """## Estimación: Plataforma de Gestión de Inventario

### Desglose de tareas:
1. Diseño UI/UX (wireframes + diseño visual): 40 horas
2. Backend API: productos, variantes y stock por tienda: 60 horas
3. Traspasos entre tiendas y alertas de stock bajo: 25 horas
4. Autenticación y roles: 20 horas
5. Dashboard de ventas con métricas: 30 horas
6. Testing y QA: 25 horas
7. Despliegue y puesta en marcha: 10 horas

**Total estimado: 210 horas**
**Equipo recomendado:** 2 desarrolladores full-stack + 1 diseñador UX (part-time)
**Duración estimada:** 6-8 semanas

### Supuestos y riesgos
- No hay integración con el TPV actual (se cargaría por CSV). Si se requiere, +30-50 h.
- El cliente entrega el catálogo inicial en un formato estructurado.
""",
    },
    {
        "meeting_summary": (
            "Un restaurante quiere una app de reservas: los clientes reservan mesa desde "
            "la web y reciben confirmación por email y recordatorio por WhatsApp. El "
            "personal ve un panel con el plano de mesas y las reservas del día, y puede "
            "bloquear mesas. Quieren cobrar una señal con tarjeta en grupos de más de 8 "
            "personas. Plazo deseado: antes de la temporada de verano (3 meses)."
        ),
        "estimation": """## Estimación: Sistema de Reservas para Restaurante

### Desglose de tareas:
1. Diseño UI/UX (web pública + panel interno): 35 horas
2. Motor de reservas: disponibilidad, turnos y bloqueos: 50 horas
3. Web pública de reservas (responsive): 30 horas
4. Panel del personal con plano de mesas: 45 horas
5. Notificaciones: email + recordatorio WhatsApp: 20 horas
6. Pagos de señal con tarjeta (Stripe): 25 horas
7. Testing y QA: 30 horas
8. Despliegue y formación al personal: 10 horas

**Total estimado: 245 horas**
**Equipo recomendado:** 1 desarrollador backend + 1 desarrollador frontend + 1 diseñador UX (part-time)
**Duración estimada:** 8-10 semanas (encaja en el plazo de 3 meses)

### Supuestos y riesgos
- La API de WhatsApp Business requiere aprobación de plantillas (puede tardar 1-2 semanas).
- Alternativa a valorar: soluciones SaaS (TheFork, CoverManager) si no se busca diferenciación.
""",
    },
]
