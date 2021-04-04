# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from openerp import workflow


class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    contract_id = fields.Many2one("res.contract", string="Contract")
    reference = fields.Char(string="Ref. du règlement")

    @api.model
    def _clear_draft_transactions(self):
        for voucher in self.search([('contract_id', '!=', False), ('contract_id.etat_paiement', '=', 'posted'), ('state', '=', 'draft')]):
            voucher.unlink()
    
    @api.multi
    def open_record(self):
        context = self.env.context
        return {
            'type': 'ir.actions.act_window',
            'name': 'Open Line',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': context.get('default_active_id'),
            'target': 'new',
        }

    # def _check_paid_voucher_available_from_contract(self):
    #     # voucher_ids = self.search_count([('contract_id', '=', self.contract_id.id), ('state', '=', 'posted')])
    #     invoice_ids = self.env['account.invoice'].search_count([('contract_id', '=', self.contract_id.id), ('state', '=', 'paid')])
    #     if invoice_ids >= 1:
    #         raise ValidationError("Souscription déjà payée.")
    #     return True

    # @api.multi
    # def action_move_line_create(self):
    #     if self.contract_id:
    #         self._check_paid_voucher_available_from_contract()
    #     return super(AccountVoucher, self).action_move_line_create()

    # def get_cr_lines(self, vals, invoice_id):
    #     cr_lines = []
    #     if vals.get("value") and vals.get("value").get("line_cr_ids"):
    #         AccountMoveLine = self.env["account.move.line"]
    #         for line in vals["value"]["line_cr_ids"]:
    #             if isinstance(line, dict):
    #                 if line.get("move_line_id"):
    #                     move_line = AccountMoveLine.browse(line["move_line_id"])
    #                     if move_line.invoice and move_line.invoice.id == invoice_id.id:
    #                         line.update({"amount": self.amount})
    #                         cr_lines.append((0, 0, line))
    #                     elif move_line.ref == invoice_id.number:
    #                         line.update({"amount": self.amount})
    #                         cr_lines.append((0, 0, line))
    #                 if not cr_lines and line.get("name") == invoice_id.number:
    #                     line.update({"amount": self.amount})
    #                     cr_lines.append((0, 0, line))
    #     return cr_lines

    # def generate_move_lines(self, invoice_id):
    #     context = self._context.copy()

    #     self.onchange_partner_id(
    #         self.partner_id.id,
    #         self.journal_id.id,
    #         self.amount,
    #         (self.currency_id.id if self.currency_id else False),
    #         self.type,
    #         self.date,
    #         context=context,
    #     )
    #     vals = self.onchange_partner_id(
    #         self.partner_id.id,
    #         self.journal_id.id,
    #         self.amount,
    #         (self.currency_id.id if self.currency_id else False),
    #         self.type,
    #         self.date,
    #         context=context,
    #     )

    #     if self.line_cr_ids:
    #         self.line_cr_ids.unlink()
    #         self.line_cr_ids = self.get_cr_lines(vals, invoice_id)
    #     else:
    #         self.line_cr_ids = self.get_cr_lines(vals, invoice_id)
    #     # if self.line_cr_ids:
    #     #     lines_matched_invoice = self.line_cr_ids.filtered(lambda a: a.move_line_id.invoice.id == invoice_id.id)
    #     #     if lines_matched_invoice:
    #     #         lines_matched_invoice[0].write({'amount': self.amount})
    #     #     else:
    #     #         lines_unmatched_invoice = self.line_cr_ids.filtered(lambda a: a.move_line_id.invoice.id != invoice_id.id)
    #     #         lines_unmatched_invoice.write({'amount': 0.0})
    #     # else:
    #     #     self.line_cr_ids = self.get_cr_lines(vals)
    #     return True

    # def _make_invoice_paid(self):
    #     for line in self.line_cr_ids.filtered(
    #         lambda a: a.amount > 0.0 and a.move_line_id.invoice
    #     ):
    #         if (
    #             line.move_line_id.invoice.residual == 0.0
    #             and line.move_line_id.invoice.state == "open"
    #         ):
    #             # line.move_line_id.invoice.confirm_paid()
    #             line.move_line_id.invoice.write({'state': 'paid'})
    #     return True

    @api.multi
    def proforma_voucher(self):
        ### Automatic reconcile invoice with payment of subscription
        if self.contract_id:
            if self.contract_id.template_id.debut_validate == "date_reglement":
                self.contract_id.date_start = fields.Date.today()

            ### Find Draft if exist then process further
            draft_invoice_id = self.contract_id._check_draft_invoice_exist()
            if draft_invoice_id:
                draft_invoice_id.button_reset_taxes()
                workflow.trg_validate(
                    self._uid,
                    "account.invoice",
                    draft_invoice_id.id,
                    "invoice_open",
                    self._cr,
                )
                draft_invoice_id.invoice_print_auto()
                # draft_invoice_id.action_send_mail_auto()
                # draft_invoice_id._gen_xml_file(9)

                ### Reconcile Payments with Invoice
                # self.generate_move_lines(draft_invoice_id)
            else:
                open_invoice_id = self.contract_id._get_open_invoice_for_voucher()
                if not open_invoice_id:
                    ### Generate Open Invoice
                    self.contract_id.generate_subscription_invoice(self.date)
                # if open_invoice_id:
                #     print "Bypasssssssssss"
                #     # self.generate_move_lines(open_invoice_id)
                # else:
                #     ### Generate Open Invoice
                #     self.contract_id.generate_subscription_invoice(self.date)
                #     new_invoice_id = self.contract_id._get_open_invoice_for_voucher()

                    ### Reconcile Payments with Invoice
                    # if new_invoice_id:
                    #     self.generate_move_lines(new_invoice_id)
        # res = super(AccountVoucher, self).proforma_voucher()

        ### Update invoice to paid as per workflow
        # if self.contract_id and self.line_cr_ids:
        #     self._make_invoice_paid()

        return super(AccountVoucher, self).proforma_voucher()

    @api.multi
    def action_view_subscription(self):
        action = self.env.ref(
            "portnet_newtarification.action_contracts_souscription"
        ).read()[0]
        action["domain"] = [("id", "in", self.contract_id.ids)]
        action["res_id"] = self.contract_id.id
        action["views"] = [
            (view_id, mode) for (view_id, mode) in action["views"] if mode == "form"
        ] or action["views"]
        return action


class AccountVoucherLine(models.Model):
    _inherit = "account.voucher.line"

    contract_id = fields.Many2one(
        related="move_line_id.invoice.contract_id", string="Souscription"
    )


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _check_paid_invoice_available_from_contract(self):
        invoice_ids = self.search_count(
            [("contract_id", "=", self.contract_id.id), ("state", "=", "paid")]
        )
        if invoice_ids >= 1:
            # raise ValidationError("You already paid invoice against same subscription.")
            raise ValidationError("Souscription déjà payée.")
        return True

    @api.multi
    def write(self, values):
        if values.get("state") and values["state"] == "paid" and self.contract_id:
            self._check_paid_invoice_available_from_contract()
        return super(AccountInvoice, self).write(values)

    @api.multi
    def invoice_pay_customer(self):
        res = super(AccountInvoice, self).invoice_pay_customer()
        if self.contract_id:
            res.get("context").update({"default_contract_id": self.contract_id.id})
        return res

    @api.multi
    def action_view_subscription(self):
        action = self.env.ref(
            "portnet_newtarification.action_contracts_souscription"
        ).read()[0]
        action["domain"] = [("id", "in", self.contract_id.ids)]
        action["res_id"] = self.contract_id.id
        action["views"] = [
            (view_id, mode) for (view_id, mode) in action["views"] if mode == "form"
        ] or action["views"]
        return action
