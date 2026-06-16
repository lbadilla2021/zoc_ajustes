# ZOC Ajustes

Extiende Ventas para crear y relacionar presupuestos y pedidos con Proyectos.

## Responsabilidad

- Agrega el campo opcional **Nombre de Servicio** a presupuestos y pedidos.
- Completa cliente y establecimiento al seleccionar un Proyecto.
- Muestra el Nombre de Servicio asociado en la lista de presupuestos.
- Muestra las cotizaciones relacionadas dentro del formulario del Proyecto.
- Agrega el acceso a Proyectos desde el menu de Ventas.

La definicion de Proyectos vive en este modulo. La integracion con Informes de
Turno se realiza desde el modulo `informe_turno`, que consume estos Proyectos.
