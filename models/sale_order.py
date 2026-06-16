# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    faena_id = fields.Many2one(
        "it.orden.servicio",
        string="Nombre de Servicio",
        domain=[
            (
                "estado",
                "in",
                ["licitacion", "adjudicado", "planificado", "por_cobrar"],
            )
        ],
        index=True,
        copy=False,
        ondelete="set null",
    )
    zoc_incluida_valor_adjudicado = fields.Boolean(
        string="Incluida en Valor Adjudicado",
        copy=False,
        readonly=True,
        help="Cotización considerada dentro del monto adjudicado del Proyecto.",
    )

    @api.onchange("faena_id")
    def _onchange_faena_id(self):
        if self.faena_id:
            self.partner_id = self.faena_id.cliente_id
            self.partner_shipping_id = self.faena_id.establecimiento_id

    @api.model_create_multi
    def create(self, vals_list):
        self._prepare_proyecto_values(vals_list)
        orders = super().create(vals_list)
        if not self.env.context.get("skip_proyecto_valor_update"):
            orders.mapped("faena_id")._actualizar_valor_final_desde_cotizaciones()
        return orders

    def write(self, vals):
        proyectos = self.mapped("faena_id")
        values = dict(vals)
        if "faena_id" in values:
            values["zoc_incluida_valor_adjudicado"] = False
        self._prepare_proyecto_values([values])
        result = super().write(values)
        if not self.env.context.get("skip_proyecto_valor_update"):
            (proyectos | self.mapped("faena_id"))._actualizar_valor_final_desde_cotizaciones()
        return result

    def unlink(self):
        proyectos = self.mapped("faena_id")
        result = super().unlink()
        if not self.env.context.get("skip_proyecto_valor_update"):
            proyectos._actualizar_valor_final_desde_cotizaciones()
        return result

    def _prepare_proyecto_values(self, vals_list):
        proyectos = self.env["it.orden.servicio"].browse(
            [vals["faena_id"] for vals in vals_list if vals.get("faena_id")]
        ).exists()
        proyectos_by_id = {proyecto.id: proyecto for proyecto in proyectos}
        for vals in vals_list:
            proyecto = proyectos_by_id.get(vals.get("faena_id"))
            if proyecto:
                vals["partner_id"] = proyecto.cliente_id.id
                if proyecto.establecimiento_id:
                    vals["partner_shipping_id"] = proyecto.establecimiento_id.id

    def init(self):
        self.env.cr.execute(
            """
            UPDATE sale_order AS sale
               SET faena_id = service.id
              FROM it_orden_servicio AS service
             WHERE service.sale_order_id = sale.id
               AND sale.faena_id IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE sale_order AS sale
               SET zoc_incluida_valor_adjudicado = TRUE
              FROM it_orden_servicio AS service
             WHERE sale.faena_id = service.id
               AND service.estado IN ('adjudicado', 'planificado', 'por_cobrar', 'cobrado')
               AND sale.zoc_incluida_valor_adjudicado IS DISTINCT FROM TRUE
            """
        )
