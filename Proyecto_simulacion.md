# **Proyecto Simulaci´on de colas** 

Prof. Lisbeth Torres 

## Objetivo General: 

Aplicar la simulaci´on de eventos discretos para modelar sistemas de l´ıneas de espera a partir de descripciones operativas reales, abstraer sus par´ametros matem´aticos, validar el simulador frente a modelos anal´ıticos (Ley de Little) y evaluar escenarios complejos de toma de decisiones. 

## Situaciones 

1. El departamento de desarrollo de software de una empresa cuenta con un ´unico servidor dedicado exclusivamente a compilar y ejecutar pruebas automatizadas (CI/CD Runner) para los commits que env´ıan sus programadores. 

Seg´un los registros hist´oricos del departamento: 

- Los desarrolladores env´ıan trabajos al servidor de forma aleatoria e independiente a lo largo de la jornada laboral, registr´andose un promedio de 1 trabajo cada 4 minutos. 

- El tiempo que tarda el servidor en compilar y probar un trabajo var´ıa considerablemente dependiendo de la complejidad del c´odigo, pero se ha determinado que sigue un comportamiento sin memoria (exponencial) con una duraci´on promedio de 3 minutos por trabajo. 

- El servidor procesa las solicitudes estrictamente en el orden en que van llegando (FIFO) y tiene capacidad de almacenamiento en cola pr´acticamente ilimitada. 

### Tareas del Estudiante: Extracci´on y Modelado de Par´ametros: 

- _a_ ) Identificar las tasas _λ_ y _µ_ en una unidad de tiempo consistente, verificar la condici´on de estabilidad del sistema ( _ρ_ menor a 1) y justificar por qu´e el sistema corresponde a un modelo M/M/1. 

- _b_ ) Implementar un simulador de eventos discretos para modelar el comportamiento del servidor. 

- _c_ ) Tras descartar el per´ıodo transitorio inicial (warm-up), estimar mediante m´ultiples r´eplicas: N´umero promedio de trabajos en el servidor ( _L_ ) y en espera ( _Lq_ ). Tiempo promedio de respuesta total ( _W_ ) y tiempo de espera en cola ( _Wq_ ). 



- _d_ ) Demostrar num´ericamente que los valores simulados satisfacen las relaciones de Little ( _L_ = _λW_ y _Lq_ = _λWq_ ) y comparar los resultados contra las f´ormulas anal´ıticas exactas del modelo M/M/1 mediante intervalos de confianza del 95 %. 

2. Sistema Avanzado — Centro de Triaje de Incidentes Una firma financiera opera un Centro de Operaciones de Seguridad (SOC) optimizado con tres analistas expertos en paralelo para investigar y resolver alertas de intrusi´on. Sin embargo, debido a limitaciones en la infraestructura de monitoreo en tiempo real, el sistema cuenta con un buffer o espacio de cola f´ısico estrictamente finito. El flujo operativo y sus restricciones son los siguientes: 

      - Espacio de Cola Finito ( _K_ ): El sistema de espera tiene una capacidad m´axima combinada (o para alertas preventivas) de _K_ = 8 trabajos en cola. 

      - Si una alerta llega y los tres analistas est´an ocupados junto con los 8 espacios de cola llenos, el sistema no puede almacenar la alerta, por lo que es rechazada inmediatamente (dropped / blocked) y se registra como una p´erdida cr´ıtica en el cumplimiento de auditor´ıa. 

      - Alertas Cr´ıticas (Tipo 1 - Alta Prioridad): Ocurren con un tiempo promedio entre llegadas de 20 minutos ( _λ_ 1 = 0 _,_ 05). Tienen prioridad absoluta de atenci´on sobre las preventivas. Su tiempo de servicio sigue una distribuci´on Uniforme entre 15 y 25 minutos. 

      - Nota: Si la cola est´a llena, las alertas cr´ıticas tambi´en pueden ser bloqueadas, lo que representa una falla severa de dise˜no que los estudiantes deben evaluar. 

      - Alertas Preventivas (Tipo 2 - Baja Prioridad): Llegan a raz´on de 6 alertas por hora ( _λ_ 2 = 0 _,_ 10). Su tiempo de revisi´on se modela mediante una distribuci´on Weibull con par´ametro de forma _k_ = 1 _,_ 5 y escala _λw_ = 12 minutos. 

      - Disciplina de Servicio: Prioridad no expropiativa (non-preemptive). Cuando un analista se desocupa, atiende primero a cualquier alerta cr´ıtica en espera; si no las hay, atiende a la alerta preventiva m´as antigua. 

### Tareas del Estudiante 

- Modelado y Simulaci´on: 

- Programar el motor de eventos discretos incorporando tres servidores, distribuciones no exponenciales, disciplina de prioridad y un control estricto de capacidad m´axima en cola ( _K_ = 8) con rechazo de paquetes/alertas desbordadas. 

- Estimaci´on de M´etricas: 

- Simular una operaci´on continua de 30 d´ıas y reportar: 

- Tiempo medio de resoluci´on total ( _W_ 1 _, W_ 2) y tiempo en cola ( _Wq_ 1 _, Wq_ 2) considerando ´unicamente las alertas admitidas. 

- Longitud promedio de la cola ( _Lq_ ). 

- Porcentaje de utilizaci´on conjunta de los tres analistas. 

Tasa de p´erdida o probabilidad de bloqueo ( _P_ loss) expresada como el porcentaje de alertas descartadas por falta de espacio en el buffer respecto al total de llegadas. 

Preguntas y Situaciones Hipot´eticas 

Los estudiantes deber´an ejecutar experimentos adicionales en su simulador para responder a la gerencia: 

-  Escenario A (Sobrecarga de Alertas Preventivas): Si una campa˜na de marketing digital o un cambio en las reglas de los sensores eleva la llegada de Alertas Preventivas un 40 % ( _λ_ 2 pasa a equivaler a 8 _,_ 4 alertas/hora), ¿en qu´e porcentaje aumenta la probabilidad de bloqueo ( _P_ loss)? ¿Se saturan los tres analistas? 

-  Escenario B (Dilema de Dise˜no: ¿Ampliar Buffer o Contratar un 4to Analista?): La gerencia dispone de presupuesto para una ´unica mejora:Ampliar la capacidad f´ısica de la cola de _K_ = 8 a _K_ = 16 espacios.Contratar un cuarto analista ( _s_ = 4) manteniendo la cola en _K_ = 8. Mediante simulaci´on, determine cu´al de las dos alternativas reduce de forma m´as dr´astica las alertas perdidas por bloqueo ( _P_ loss) y cu´al optimiza mejor los tiempos de espera. 