"""Conversaciones de prueba para estresar el CAG.

Cada perfil es una lista de turnos (turn_index, transcript, fact_to_remember).
fact_to_remember es lo que los turnos siguientes deberian seguir recordando
(o None si ese turno no agrega nada nuevo). Lo usa MemoryDriftMetric.

Los hechos son palabras cortas que el extractor guarda en el project_metadata
(nombre, tecnologias), salvo el presupuesto: el metadata no tiene un campo
para eso, y justamente queremos ver si se pierde.

Los tres perfiles tienen 20 turnos. Para N = 1, 3, 6, 10 y 20 se mira el
estado de la sesion en ese turno.
"""

TURN_POINTS = [1, 3, 6, 10, 20]

# Proyecto que crece: cada turno suma un requisito coherente
GROWING = [
    (1, "Proyecto Nimbus: plataforma web SaaS para que clinicas dentales agenden horas. Frontend en React y backend en Python con FastAPI.", "Nimbus"),
    (2, "La base de datos va a ser PostgreSQL.", "PostgreSQL"),
    (3, "Hay que agregar autenticacion con usuario y contraseña, y recuperar la clave por correo.", None),
    (4, "Los pacientes reciben recordatorios por SMS con Twilio.", "Twilio"),
    (5, "Cada clinica es un cliente distinto, tiene que ser multi-tenant.", None),
    (6, "Necesitamos un audit log de quien cambia cada hora agendada.", None),
    (7, "Exportar la agenda del mes a CSV.", None),
    (8, "Los pagos de la consulta se cobran con Stripe.", "Stripe"),
    (9, "Agrega un panel con metricas de ocupacion por profesional.", None),
    (10, "Las notificaciones internas van por Slack.", "Slack"),
    (11, "Hay que permitir reagendar desde un link en el correo.", None),
    (12, "Agrega roles: recepcion, profesional y administrador.", None),
    (13, "Los archivos de radiografias se guardan en Amazon S3.", "S3"),
    (14, "Agrega lista de espera cuando no hay horas.", None),
    (15, "Integracion con Google Calendar para los profesionales.", "Google Calendar"),
    (16, "Agrega encuestas de satisfaccion despues de la consulta.", None),
    (17, "El cache de disponibilidad va en Redis.", "Redis"),
    (18, "Agrega soporte para dos idiomas, español e ingles.", None),
    (19, "Los logs van a Datadog.", "Datadog"),
    (20, "Con todo lo anterior, ¿como queda la estimacion final del proyecto?", None),
]

# Proyecto que pivota: en el turno 5 cambia el stack de React Native a Flutter
PIVOT = [
    (1, "Proyecto Atlas: app movil para que los vecinos de un edificio reserven espacios comunes. La app se hace en React Native.", "Atlas"),
    (2, "El backend es Node.js con una API REST.", "Node.js"),
    (3, "Login con correo y con Google.", None),
    (4, "Calendario de reservas por espacio: quincho, gimnasio y sala de eventos.", None),
    (5, "Cambio importante: el equipo ya no quiere React Native, la app se va a hacer en Flutter.", "Flutter"),
    (6, "Notificaciones push cuando se confirma una reserva.", None),
    (7, "La base de datos es Firebase Firestore.", "Firestore"),
    (8, "El administrador puede bloquear un espacio por mantencion.", None),
    (9, "Agrega cobro por reserva del quincho.", None),
    (10, "Agrega reglamento que hay que aceptar antes de reservar.", None),
    (11, "Historial de reservas por departamento.", None),
    (12, "Reportes mensuales para la administracion.", None),
    (13, "Chat entre vecinos y conserjeria.", None),
    (14, "Votaciones simples de la comunidad.", None),
    (15, "Avisos de la administracion en la portada.", None),
    (16, "Registro de visitas en conserjeria.", None),
    (17, "Modo sin conexion para ver las reservas.", None),
    (18, "Accesibilidad: texto grande y alto contraste.", None),
    (19, "Publicar en App Store y Google Play.", None),
    (20, "Con todo lo anterior, ¿como queda la estimacion final y con que tecnologia?", None),
]

# Proyecto que se contradice: presupuesto de 30000 en el turno 3 y de 80000 en el 8
CONTRADICTION = [
    (1, "Proyecto Orion: herramienta interna para que el area de ventas registre visitas a clientes. Web con Django.", "Orion"),
    (2, "Los vendedores la usan desde el telefono, tiene que verse bien en movil.", None),
    (3, "El presupuesto es de 30000 euros, no mas.", "30000"),
    (4, "Cada visita guarda cliente, fecha, notas y proxima accion.", None),
    (5, "Reporte semanal por vendedor.", None),
    (6, "Importar la cartera de clientes desde un Excel.", None),
    (7, "Recordatorios de proxima accion por correo.", None),
    (8, "Corrijo: el presupuesto aprobado ahora es de 80000 euros.", "80000"),
    (9, "Agrega un mapa con las visitas del dia.", None),
    (10, "Agrega metas mensuales por vendedor.", None),
    (11, "El gerente ve el avance de todo el equipo.", None),
    (12, "Exportar las visitas a CSV.", None),
    (13, "Integracion con el correo para registrar visitas desde una invitacion.", None),
    (14, "Agrega fotos de la visita.", None),
    (15, "Agrega firma del cliente en pantalla.", None),
    (16, "Agrega campos personalizados por tipo de cliente.", None),
    (17, "Permisos por zona geografica.", None),
    (18, "Un tablero para la reunion de los lunes.", None),
    (19, "Respaldo diario de la base de datos.", None),
    (20, "Con todo lo anterior y el presupuesto vigente, ¿como queda la estimacion final?", None),
]

SCENARIOS = {
    "growing": {
        "turns": GROWING,
        "project_type": "web_saas",
        # hechos que dejan de valer desde cierto turno (ninguno aqui)
        "replaced": {},
        # palabras que se miran en el metadata en cada turno
        "watch": ["Nimbus"],
    },
    "pivot": {
        "turns": PIVOT,
        "project_type": "mobile_app",
        "replaced": {},
        # si quedan los dos, el metadata acumulo en vez de actualizar
        "watch": ["React Native", "Flutter"],
    },
    "contradiction": {
        "turns": CONTRADICTION,
        "project_type": "internal_tool",
        # desde el turno 8 el presupuesto de 30000 ya no es el vigente
        "replaced": {"30000": 8},
        "watch": ["30000", "80000"],
    },
}


# Hechos que deberian recordarse en el turno n: los declarados antes de n
# que no fueron reemplazados
def facts_expected(name, n):
    scenario = SCENARIOS[name]
    facts = []
    for turn_index, transcript, fact in scenario["turns"]:
        if fact is None or turn_index >= n:
            continue
        replaced_at = scenario["replaced"].get(fact)
        if replaced_at is not None and n >= replaced_at:
            continue
        facts.append(fact)
    return facts
