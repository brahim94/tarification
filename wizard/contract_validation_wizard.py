# -*- encoding: utf-8 -*-

from openerp import models, fields, api, exceptions, _
from openerp import workflow
from openerp.exceptions import ValidationError


class ContractvalidationWizard(models.TransientModel):
    _inherit = "contract.validation.wizard"

    type_contract = fields.Selection(
        [("abonnement", "Abonnement"), ("package", "Package")],
        string="Type Contract",
    )

    @api.multi
    def action_confirm(self):
        contract_id = self.contract_id
        if self.next_seq:
            contract_id.name = self.env["ir.sequence"].get("res.contract.seq")
        contract_id._subscription_validation()
        if self.choice == "create":
            if (
                contract_id.is_template == False
                and contract_id.type_contract == "package"
            ):
                open_paid_invoice_id = contract_id._check_open_paid_invoice_exist()
                draft_invoice_id = contract_id._check_draft_invoice_exist()
                if open_paid_invoice_id:
                    raise ValidationError("Facture déjà gnérée")
                elif draft_invoice_id:
                    draft_invoice_id.button_reset_taxes()
                    workflow.trg_validate(
                        self._uid,
                        "account.invoice",
                        draft_invoice_id.id,
                        "invoice_open",
                        self._cr,
                    )
                    draft_invoice_id.invoice_print_auto()
                    draft_invoice_id.action_send_mail_auto()
                    draft_invoice_id._gen_xml_file(9)
                else:
                    contract_id.generate_subscription_invoice(self.date)
            else:
                contract_id.action_create_invoice(self.date)

        contract_id.state = "pending"
