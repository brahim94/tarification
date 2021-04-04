# -*- coding: utf-8 -*-

from openerp import api, fields, models, _


class ResTransaction(models.Model):
    _name = "res.transaction"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Transaction Id", track_visibility="onchange")
    contract_id = fields.Many2one("res.contract", "Contract")
    event_ref = fields.Char("Event Ref", track_visibility="onchange")
    date = fields.Datetime(string="Date", track_visibility="onchange")
    user = fields.Char(string="User", track_visibility="onchange")
    cancel_date = fields.Datetime(string="cancel date", track_visibility="onchange")
    motif = fields.Char(string="Motif", track_visibility="onchange")
    state = fields.Selection(
        string="Statut",
        selection=[("valid", "Valid"), ("cancelled", "Cancelled")],
        default="valid",
        track_visibility="onchange",
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE (name)", "Name must be unique."),
    ]

    @api.multi
    def action_cancel(self):
        return self.write({"state": "cancelled"})
