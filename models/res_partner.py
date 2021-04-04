# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    ### For Category Code - T ###
    # custom_office_id = fields.Many2one('custom.office', string='Bureau Douanier')
    # custom_office_cin_code = fields.Char('CIN Autoirsée par ADII', size=10)

    ### For Category Code - M ###
    # code_douane = fields.Integer(string='Code Douane')
    edi_code = fields.Char(string="Code EDI", size=20)
    code_port = fields.Many2one("code.port", string="Code Port")
    number_limit_container = fields.Integer("Nombre limite de conteneurs")

    ### For Category Code - FRET_FWD ###
    metle_attachment_id = fields.Binary(type="binary", string="Autorisation du METLE")
    metle_attachment_name = fields.Char(string="Autorisation du METLE Name")
    oc_attachment_id = fields.Binary(type="binary", string="Autorisation OC")
    oc_attachment_name = fields.Char(string="Autorisation OC Name")

    custom_office_line_ids = fields.One2many(
        "custom.office.line", "partner_id", string="Bureaux Douaniers Lines"
    )

    @api.onchange("number_limit_container")
    def onchange_number_limit_container(self):
        if self.number_limit_container:
            if self.number_limit_container < 0 or self.number_limit_container > 5:
                raise ValidationError(
                    "Nombre limite de conteneurs should be between 1 to 5."
                )

    @api.model
    def create(self, values):
        res = super(ResPartner, self).create(values)
        if (
            res.number_limit_container
            and res.number_limit_container < 0
            or res.number_limit_container > 5
        ):
            raise ValidationError(
                "Nombre limite de conteneurs should be between 1 to 5."
            )
        # if values.get('categ_id'):
        #     res.portnet_user_ids.write({'categ_code': res.categ_id.code})
        return res

    @api.multi
    def write(self, values):
        res = super(ResPartner, self).write(values)
        if (
            self.number_limit_container
            and self.number_limit_container < 0
            or self.number_limit_container > 5
        ):
            raise ValidationError(
                "Nombre limite de conteneurs should be between 1 to 5."
            )
        if values.get("categ_id"):
            self.portnet_user_ids.write({"categ_code": self.categ_id.code})
        return res


class UserPortnet(models.Model):
    _inherit = "user.portnet"

    ### For Category Code - CONS ###
    custom_office_id = fields.Many2one("custom.office", string="Bureau Douanier")
    custom_office_cin_code = fields.Char("CIN Autoirsée par ADII", size=10)
    categ_code = fields.Char(string="Code Category")


class CustomOffice(models.Model):
    _name = "custom.office"
    _description = "Custom Office"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)


class CodePort(models.Model):
    _name = "code.port"
    _description = "Code Port"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)


class CustomOfficeLine(models.Model):
    _name = "custom.office.line"
    _description = "Custom Office Line"
    _rec_name = "custom_office_id"

    partner_id = fields.Many2one("res.partner", string="Client")
    custom_office_id = fields.Many2one(
        "custom.office", string="Bureau Douanier", required=True
    )
    custom_office_cin_code = fields.Char(
        "CIN Autoirsée par ADII", size=10, required=True
    )
