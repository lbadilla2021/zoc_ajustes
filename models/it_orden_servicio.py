# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ITTipoTrabajo(models.Model):
    _name = "it.tipo.trabajo"
    _description = "Tipo de Trabajo"

    name = fields.Char("Nombre", required=True)
    active = fields.Boolean(default=True)


class ITTipoServicio(models.Model):
    _name = "it.tipo.servicio"
    _description = "Tipo de Servicio"

    name = fields.Char("Nombre", required=True)
    active = fields.Boolean(default=True)


class ITOrdenServicio(models.Model):
    _name = "it.orden.servicio"
    _description = "Proyecto"
    _rec_name = "descripcion_servicio"
    _order = "id desc"

    name = fields.Char("Código", required=True, copy=False, default=lambda self: _("Nuevo"))
    numero_pedido = fields.Char("Número de pedido")
    ito = fields.Char("ITO")
    cliente_id = fields.Many2one(
        "res.partner", string="Cliente", domain="[('parent_id', '=', False)]"
    )
    establecimiento_id = fields.Many2one(
        "res.partner",
        string="Establecimiento",
        domain="[('parent_id', '=', cliente_id)]",
    )
    descripcion_servicio = fields.Text("Nombre de Servicio")
    observacion = fields.Text("Observación")
    tipo_trabajo_id = fields.Many2one("it.tipo.trabajo", string="Tipo de trabajo")
    tipo_servicio_id = fields.Many2one("it.tipo.servicio", string="Tipo de servicio")
    fecha_adjudicacion = fields.Date("Fecha Adjudicación")
    fecha_inicio_programada = fields.Date("Fecha Inicio Programada")
    fecha_termino_programada = fields.Date("Fecha Término Programada")
    duracion_horas = fields.Float("Duración (horas)")
    cantidad_turnos = fields.Integer("Cantidad de turnos")
    cantidad_equipos = fields.Integer("Cantidad de equipos")
    valor_adjudicado = fields.Float("Valor Adjudicado")
    valor_final = fields.Float("Valor Final")
    estado = fields.Selection(
        [
            ("licitacion", "Licitación"),
            ("perdido", "Perdido"),
            ("adjudicado", "Adjudicado"),
            ("planificado", "Planificado"),
            ("por_cobrar", "Por Cobrar"),
            ("cobrado", "Cobrado"),
        ],
        string="Estado",
        required=True,
        default="licitacion",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Cotización anterior",
        copy=False,
        ondelete="set null",
    )
    quotation_ids = fields.One2many(
        "sale.order",
        "faena_id",
        string="Cotizaciones",
    )
    quotation_count = fields.Integer(
        string="Cantidad de cotizaciones",
        compute="_compute_quotation_count",
    )

    @api.onchange("cliente_id")
    def _onchange_cliente_id(self):
        for record in self:
            if (
                record.establecimiento_id
                and record.establecimiento_id.parent_id != record.cliente_id
            ):
                record.establecimiento_id = False

    @api.constrains("descripcion_servicio")
    def _check_nombre_servicio(self):
        for record in self:
            if not (record.descripcion_servicio or "").strip():
                raise ValidationError(_("Debe ingresar el Nombre de Servicio."))

    @api.constrains("cliente_id", "establecimiento_id")
    def _check_establecimiento_cliente(self):
        for record in self.filtered("establecimiento_id"):
            if record.establecimiento_id.parent_id != record.cliente_id:
                raise ValidationError(
                    _("El establecimiento debe ser un contacto o dirección del cliente seleccionado.")
                )

    @api.depends("quotation_ids")
    def _compute_quotation_count(self):
        for record in self:
            record.quotation_count = len(record.quotation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code("it.proyecto") or _("Nuevo")
        return super().create(vals_list)

    def _check_required_fields(self, field_names, action_name):
        missing_fields = [
            self._fields[field].string
            for field in field_names
            if (
                self[field] is False
                or self[field] is None
                or (isinstance(self[field], str) and not self[field].strip())
            )
        ]
        if missing_fields:
            raise ValidationError(
                "Debe completar los siguientes campos para %s: %s"
                % (action_name, ", ".join(missing_fields))
            )

    def action_descartar(self):
        self.write({"estado": "perdido"})

    def action_adjudicar(self):
        for record in self:
            record._check_required_fields(
                ["cliente_id", "establecimiento_id", "tipo_trabajo_id", "tipo_servicio_id"],
                "adjudicar",
            )
            adjudicated_orders = record.quotation_ids.filtered(
                lambda order: order.state != "cancel"
            )
            valor_adjudicado = sum(adjudicated_orders.mapped("amount_total"))
            adjudicated_orders.with_context(skip_proyecto_valor_update=True).write(
                {"zoc_incluida_valor_adjudicado": True}
            )
            values = {
                "estado": "adjudicado",
                "valor_adjudicado": valor_adjudicado,
                "valor_final": valor_adjudicado,
            }
            if not record.fecha_adjudicacion:
                values["fecha_adjudicacion"] = fields.Date.context_today(record)
            record.write(values)

    def action_planificar(self):
        for record in self:
            record._check_required_fields(
                ["ito", "fecha_inicio_programada", "fecha_termino_programada"],
                "planificar",
            )
            record.estado = "planificado"

    def action_cobrar(self):
        for record in self:
            record._check_required_fields(["valor_adjudicado", "valor_final"], "cobrar")
            record.estado = "por_cobrar"

    def action_cerrar(self):
        self.write({"estado": "cobrado"})

    def action_open_quotations(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_quotations_with_onboarding"
        )
        action["domain"] = [("faena_id", "=", self.id)]
        action["context"] = {
            "default_faena_id": self.id,
            "default_partner_id": self.cliente_id.id,
        }
        return action

    def _actualizar_valor_final_desde_cotizaciones(self):
        for record in self:
            if record.estado not in ("adjudicado", "planificado", "por_cobrar", "cobrado"):
                continue
            adicionales = record.quotation_ids.filtered(
                lambda order: (
                    order.state != "cancel"
                    and not order.zoc_incluida_valor_adjudicado
                )
            )
            valor_final = record.valor_adjudicado + sum(adicionales.mapped("amount_total"))
            if record.valor_final != valor_final:
                record.with_context(skip_proyecto_valor_update=True).write(
                    {"valor_final": valor_final}
                )

    def init(self):
        sequence = self.env["ir.sequence"].search([("code", "=", "it.proyecto")], limit=1)
        if not sequence:
            self.env["ir.sequence"].create(
                {
                    "name": "Proyecto",
                    "code": "it.proyecto",
                    "prefix": "P",
                    "padding": 5,
                    "company_id": False,
                }
            )
        self.env.cr.execute(
            """
            UPDATE it_orden_servicio
               SET descripcion_servicio = name
             WHERE descripcion_servicio IS NULL
                OR btrim(descripcion_servicio) = ''
            """
        )
