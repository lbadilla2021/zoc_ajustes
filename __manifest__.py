# -*- coding: utf-8 -*-
{
    "name": "Barca Ajustes al modulo Ventas",
    "summary": "Integra Proyectos con presupuestos y pedidos de venta",
    "version": "18.0.4.1.0",
    "category": "Sales",
    "author": "ZOC",
    "license": "LGPL-3",
    "depends": [
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/tipo_trabajo_servicio_views.xml",
        "views/sale_order_views.xml",
        "views/faena_views.xml",
    ],
    "installable": True,
    "application": False,
}
