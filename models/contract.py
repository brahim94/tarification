# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from openerp import workflow
from openerp.exceptions import AccessError, Warning
import datetime


class ResContract(models.Model):
    _name = "res.contract"
    _inherit = ["res.contract", "ir.needaction_mixin"]

    active = fields.Boolean(string="Active", default=True)

    active_package = fields.Selection(
        [("Actif", "Actif"), ("Inactif", "Inactif")],
        string="Etat package",
        default="Actif",
        track_visibility="onchange",
    )

    type_contract = fields.Selection(
        [("abonnement", "Abonnement"), ("package", "Package")],
        string="Type Contract",
        default="abonnement",
    )

    is_active_subscription = fields.Boolean(compute='_compute_active_subscription', string="Active")
    exercice = fields.Selection([('EN_COURS', 'EN_COURS'), ('PROCHAIN', 'PROCHAIN')], string="Exercice", default="EN_COURS")

    ### Information Facturation
    criteria_factures = fields.Selection(
        [("1", "Titre d'importation"), ("2", "Escale"), ("3", "DUM")],
        string="Critére de facturation",
    )
    type_paiment = fields.Selection(
        [("prepaiement", "Pré-paiement"), ("postpaiement", "Post-paiement")],
        string="Type paiement",
    )
    debut_validate = fields.Selection(
        [
            # ("debut_encourse", "Début année en cours"),
            ("debut_venir", "Début année à venir"),
            ("date_souscription", "Date souscription"),
            ("date_reglement", "Date réglement"),
        ],
        string="Debut de validité",
    )
    type_service = fields.Selection(
        [("fix", "Fixe"), ("tranches", "Tranches"), ("aucun", "Aucun")],
        string="Type de frais de services",
    )
    service_fee = fields.Char(string="Frais de services")
    description_package = fields.Text(string="Description Package")
    add_balance = fields.Integer(string="Solde Supplémentaire")
    type_service_line_ids = fields.One2many(
        "contract.service.line", "contract_id", string="Tranche Service Lines"
    )

    ### Information Contract
    parameter_decompte = fields.Selection(
        [("1", "Envoi pour domiciliation"), ("2", "Envoi du manifeste"), ("3", "Integration DUM")],
        string="Paramétre de décompte",
    )
    validate_package = fields.Selection(
        [
            ("fin_dannee", "Fin d'année"),
            ("mansuelle", "Mansuelle"),
            ("trimestrielle", "Trimestrielle"),
            ("semestrielle", "Semestrielle"),
        ],
        string="Validité du package",
    )
    transaction_no = fields.Selection(
        [
            ("transaction_limit", "Nombre de transactions limité"),
            ("transaction_illimit", "Nombre de  transactions illlimité"),
        ],
        string="Nombre de transactions",
    )
    transaction_no_limit = fields.Integer(string="Nombre de Transaction limité")

    ### Package
    total_subscription = fields.Integer(
        compute="_compute_totals_for_packages", string="Souscription"
    )
    total_expire = fields.Integer(
        compute="_compute_totals_for_packages", string="Expiré"
    )
    total_encourse = fields.Integer(
        compute="_compute_totals_for_packages", string="En course"
    )
    total_suspended = fields.Integer(
        compute="_compute_totals_for_packages", string="Suspendu"
    )

    ### subscription
    total_autorise = fields.Integer(compute="_compute_totals", string="Autorisé")
    total_consomme = fields.Integer(compute="_compute_totals", string="Consommé")
    total_restant = fields.Integer(compute="_compute_totals", string="Restant")
    total_depassement = fields.Integer(
        compute="_compute_totals", string="Dépassemement"
    )

    ### Portnet API
    id_portnet = fields.Integer(string="ID GU Portnet", track_visibility="onchange")
    date_create_portnet = fields.Datetime(
        string="Date creation GU", track_visibility="onchange"
    )
    date_write_portnet = fields.Datetime(
        string="Derniere modification GU", track_visibility="onchange"
    )
    date_sync_portnet = fields.Datetime(
        string="Derniere synchronisation GU", track_visibility="onchange"
    )

    ### Fieldsfor Facturation and Paiement
    invoice_ids = fields.One2many("account.invoice", "contract_id", string="Invoices")
    voucher_ids = fields.One2many("account.voucher", "contract_id", string="Voucher")

    etat_facturation = fields.Selection(
        [
            ("paid", "Paid"),
            ("open", "Ouvert"),
            ("draft", "Brouillon"),
            ("pas_de_facture", "Pas de facture"),
        ],
        string="Etat Facturation",
        readonly=True,
        compute="_compute_etat_facturation",
        index=True,
    )

    etat_paiement = fields.Selection(
        [
            ("posted", "Posted"),
            ("draft", "Brouillon"),
            ("pas_de_paiement", "Pas de paiement"),
        ],
        string="Etat Paiement",
        readonly=True,
        compute="_compute_etat_paiement",
        index=True,
    )

    state = fields.Selection(
        string="Statut",
        selection=[
            ("draft", "Brouillon"),
            ("pending", "En cours"),
            ("expire", "Expiré"),
            ("suspend", "Suspendu"),
            ("closed", "Clôturé"),
        ],
        default="draft",
        track_visibility="onchange",
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE (name)", "Name must be unique."),
    ]

    @api.onchange('exercice')
    def onchange_exercice(self):
        if self.exercice == 'PROCHAIN':
            self.date_start = fields.Date.from_string(fields.Date.today()).replace(month=1, day=1) + relativedelta(years=1)
            self.date = fields.Date.from_string(fields.Date.today()).replace(month=12, day=31) + relativedelta(years=1)
        else:
            self.onchange_debut_validate()
            self.onchange_validate_package()

    @api.depends('date_start', 'date')
    def _compute_active_subscription(self):
        for record in self:
            subscription_status = False
            if record.date_start <= fields.Date.today() and fields.Date.today() <= record.date:
                subscription_status = True
            record.is_active_subscription = subscription_status

    @api.multi
    def action_validate(self,create_invoice=False):
        context = self._context.copy()
        context.update({'default_type_contract': self.type_contract})
        wizard_id = self.pool.get("contract.validation.wizard").create(self._cr, self._uid, {'contract_id':self.id}, context=context)
        return {
            'name':_("Validation contrat"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'contract.validation.wizard',
            'res_id':wizard_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context,
            }

    @api.depends("name")
    def _compute_etat_facturation(self):
        invoice_obj = self.env["account.invoice"]
        for record in self:
            paid_invoice = invoice_obj.search(
                [("contract_id", "=", record.id), ("state", "=", "paid")]
            )
            open_invoice = invoice_obj.search(
                [("contract_id", "=", record.id), ("state", "=", "open")]
            )
            draft_invoice = invoice_obj.search(
                [("contract_id", "=", record.id), ("state", "=", "draft")]
            )

            if paid_invoice:
                record.etat_facturation = "paid"

            elif open_invoice:
                record.etat_facturation = "open"

            elif draft_invoice:
                record.etat_facturation = "draft"

            else:
                record.etat_facturation = "pas_de_facture"

    @api.depends("name")
    def _compute_etat_paiement(self):
        invoice_obj = self.env["account.voucher"]
        for record in self:
            posted_voucher = invoice_obj.search(
                [("contract_id", "=", record.id), ("state", "=", "posted")]
            )
            draft_voucher = invoice_obj.search(
                [("contract_id", "=", record.id), ("state", "=", "draft")]
            )

            if posted_voucher:
                record.etat_paiement = "posted"

            elif draft_voucher:
                record.etat_paiement = "draft"

            else:
                record.etat_paiement = "pas_de_paiement"

    @api.onchange("periodicity_id", "date_start")
    def _set_end_date(self):
        if self.periodicity_id and self.date_start:
            # self.date = (parser.parse(self.date_start) + relativedelta(months=self.periodicity_id.nb_months))- relativedelta(days=1)
            print "Method Commented to set date...."

    @api.onchange("template_id")
    def _onchange_template(self):
        if self.template_id:
            self.partner_id = False
            self.periodicity_id = self.template_id.periodicity_id
            self.currency_id = self.template_id.currency_id
            self.tacite = self.template_id.tacite
            self.product_category_id = self.template_id.product_category_id
            self.product_id = self.template_id.product_id
            # self.amount = self.template_id.amount
            self.partner_categ_id = self.template_id.partner_categ_id

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            # self.amount = self.product_id.list_price
            print "Method Commented to set amount...."

    @api.onchange("partner_categ_id")
    def onchage_partner_categ_id(self):
        if self.partner_categ_id:
            context = self._context
            if (
                context.get("default_type_contract")
                and context.get("default_is_template")
                and context["default_type_contract"] == "package"
                and context["default_is_template"] == True
            ):
                if (
                    self.partner_categ_id.code == "I"
                    or self.partner_categ_id.code == "BANQUES"
                ):
                    self.criteria_factures = "1"
                    self.parameter_decompte = "1"
                elif self.partner_categ_id.code == "T" :
                    self.criteria_factures = "3"
                    self.parameter_decompte = "3"
                else :
                    self.criteria_factures = "2"
                    self.parameter_decompte = "2"

    @api.onchange("date_start", "periodicity_id")
    def onchange_start_period(self):
        if self.date_start and self.periodicity_id:
            self.next_invoice_date = fields.Date.from_string(
                self.date_start
            ) + relativedelta(months=self.periodicity_id.nb_months)

    @api.onchange("next_invoice_date")
    def onchange_next_invoice_date(self):
        if self.next_invoice_date:
            self.anticipated_invoice_date = self.next_invoice_date

    @api.depends("name")
    def _compute_totals_for_packages(self):
        for record in self:
            package_ids = self.env["res.contract"].search(
                [
                    ("is_template", "=", False),
                    ("type_contract", "=", "package"),
                    ("template_id", "=", record.id),
                ]
            )
            expire_ids = package_ids.filtered(lambda a: a.state == "expire")
            encours_ids = package_ids.filtered(lambda a: a.state == "pending")
            suspend_ids = package_ids.filtered(lambda a: a.state == "suspend")
            # closed_ids = package_ids.filtered(lambda a: a.state == 'closed')

            record.total_subscription = len(package_ids)
            record.total_expire = len(expire_ids)
            record.total_encourse = len(encours_ids)
            record.total_suspended = len(suspend_ids)
            # record.total_subscription = len(closed_ids)

    @api.depends("transaction_no_limit", "add_balance")
    def _compute_totals(self):
        for record in self:
            record.total_autorise = record.transaction_no_limit + record.add_balance
            record.total_consomme = self.env["res.transaction"].search_count(
                [("contract_id", "=", record.id), ("state", "=", "valid")]
            )

            ### Total Restant
            total_res = record.total_autorise - record.total_consomme
            if total_res > 0:
                record.total_restant = total_res

            ### Total Dépassemement
            total_depa = record.total_consomme - record.total_autorise
            if total_depa > 0:
                record.total_depassement = total_depa

    @api.onchange("transaction_no")
    def onchange_transaction_no_limit(self):
        if self.transaction_no:
            if self.transaction_no != "transaction_limit":
                self.transaction_no_limit = 0

    @api.onchange("validate_package", "date_start")
    def onchange_validate_package(self):
        if self.validate_package and self.exercice != "PROCHAIN":
            if self.validate_package == "fin_dannee":
                self.date = fields.Date.from_string(fields.Date.today()).replace(
                    month=12, day=31
                )
            elif self.validate_package == "mansuelle" and self.date_start:
                self.date = fields.Date.from_string(self.date_start) + relativedelta(
                    months=1
                )
            elif self.validate_package == "trimestrielle" and self.date_start:
                self.date = fields.Date.from_string(self.date_start) + relativedelta(
                    months=3
                )
            elif self.validate_package == "semestrielle" and self.date_start:
                self.date = fields.Date.from_string(self.date_start) + relativedelta(
                    months=6
                )

    @api.onchange("debut_validate")
    def onchange_debut_validate(self):
        if self.debut_validate and self.exercice != "PROCHAIN":
            # if self.debut_validate == "debut_encourse":
            #     self.date_start = fields.Date.from_string(fields.Date.today()).replace(
            #         month=1, day=1
            #     )
            if self.debut_validate == "debut_venir":
                self.date_start = fields.Date.from_string(fields.Date.today()).replace(
                    month=1, day=1
                ) + relativedelta(years=1)
            # elif self.debut_validate == 'date_souscription':
            #     self.date = fields.Date.from_string(self.date_start) + relativedelta(months=3)
            # elif self.debut_validate == 'date_reglement':
            #     self.date = fields.Date.from_string(self.date_start) + relativedelta(months=6)

    def _get_sequence(self):
        for record in self:
            sequence = 1
            for line in record.type_service_line_ids:
                line.id_tranche = sequence
                sequence += 1

    def _update_tranche_de_last_line(self):
        for record in self:
            if record.type_service_line_ids:
                if record.type_service_line_ids.filtered(
                    lambda a: not a.tranche_a_no
                    and a.id
                    != sorted(
                        record.type_service_line_ids, key=lambda a: a.id, reverse=False
                    )[-1].id
                ):
                    raise ValidationError("Tranche à only be empty in last line.")

    def _voucher_sequence(self):
        self.name = self.env["ir.sequence"].next_by_code("package_sequence")

    def _subscription_validation(self):
        ResContract = self.env["res.contract"]
        subscription_id = ResContract.search(
            [
                ("partner_id", "=", self.partner_id.id),
                # ("template_id", "=", self.template_id.id),
                ("is_template", "=", False),
                ("type_contract", "=", "package"),
                ("id", "!=", self.id),
            ]
        )
        if subscription_id.filtered(lambda a: a.is_active_subscription and a.state == "pending") and self.is_active_subscription and self.state == "pending":
            raise ValidationError(
                    "You can not create multiple active subscriptions."
                )
        pending_subscriptions = subscription_id.filtered(lambda s: s.state == "pending" and s.is_active_subscription)
        if subscription_id and pending_subscriptions and self.is_active_subscription:
            for sub in pending_subscriptions:
                if sub.transaction_no != 'transaction_illimit':# and not sub._context.get('created_from_api'):
                    sub.write({
                            "state": "expire",
                        })
                    sub.message_post(body=_("Solde transferé à la nouvelle souscription"))
                    if self.transaction_no != 'transaction_illimit':	
                        self.write({ "add_balance": (self.add_balance + sub.total_restant) or 0.0,
                            })
                        sub.write({ "add_balance": (sub.add_balance - sub.total_restant) or 0.0,
                            })
                        self.message_post(body=_("Solde récuperé de la souscription "+str(sub.name)))
                    if not self._context.get('updated_from_api'):
                        sub.update_subscription_export()#action_sync_GU()
            #if self.transaction_no == 'transaction_illimit':
                else:
                    raise ValidationError(
                        "Vous avez une subscription illimitée."
                    )

        start_date = datetime.datetime.strptime(fields.Date.to_string(
            fields.Date.from_string(fields.Date.today()).replace(month=1, day=1)
        ), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(fields.Date.to_string(
            fields.Date.from_string(fields.Date.today()).replace(month=12, day=31)
        ), '%Y-%m-%d')
        exist_subscription_id = ResContract.search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("date_start", ">=", start_date),
                ("date_start", "<=", end_date),
                #("exercice", "=", self.exercice),
                ("is_template", "=", False),
                ("type_contract", "=", "package"),
                ("id", "!=", self.id),
                ("state", "!=", "draft"),
            ]
        )
        if exist_subscription_id:
            self.amount = 0
        return True

    def _check_type_paiment(self):
        if self.type_paiment == "prepaiement" and self.tacite == True:
            self.tacite = False
        return True

    @api.model
    def create(self, vals):
        res = super(ResContract, self).create(vals)

        #res._subscription_validation()
        res._check_type_paiment()

        if res and res.is_template and res.type_contract == "package":
            res._voucher_sequence()

        if vals.get("type_service_line_ids"):
            res._get_sequence()
            res._update_tranche_de_last_line()
        return res

    @api.multi
    def write(self, vals):
        res = super(ResContract, self).write(vals)
        self._check_type_paiment()
        if vals.get("type_service_line_ids"):
            self._get_sequence()
            self._update_tranche_de_last_line()
        return res

    @api.multi
    def action_disactive(self):
        return self.write({"active_package": "Actif"})

    @api.multi
    def action_active(self):
        return self.write({"active_package": "Inactif"})

    # @api.multi
    # def action_sync_GU(self):
    #     return True

    # @api.multi
    # def action_suspend(self):
    #     return self.write({'state': 'suspend'})

    # @api.multi
    # @api.constrains('type_paiment', 'tacite')
    # def _check_type_paiment(self):
    #     for package in self:
    #         if package.type_paiment in ('prepaiement') and package.tacite == True:
    #             raise ValidationError(_('Tacite de reconduction must be disable if Type paiement is set prepaiment.'))

    # @api.multi
    # def action_reactive(self):
    #     return True

    @api.multi
    def update_data(self):
        return True

    @api.onchange("template_id")
    def onchange_template_id(self):
        if self.template_id and self.template_id.type_contract == "package":
            self.criteria_factures = self.template_id.criteria_factures
            self.type_paiment = self.template_id.type_paiment
            self.debut_validate = self.template_id.debut_validate
            self.type_service = self.template_id.type_service
            self.service_fee = self.template_id.service_fee
            self.description_package = self.template_id.description_package
            self.parameter_decompte = self.template_id.parameter_decompte
            self.validate_package = self.template_id.validate_package
            self.transaction_no = self.template_id.transaction_no
            self.transaction_no_limit = self.template_id.transaction_no_limit
            # self.total_subscription = self.template_id.total_subscription
            # self.total_expire = self.template_id.total_expire
            # self.total_encourse = self.template_id.total_encourse
            # self.total_suspended = self.template_id.total_suspended
            self.total_autorise = self.template_id.total_autorise
            self.total_consomme = self.template_id.total_consomme
            self.total_restant = self.template_id.total_restant
            self.total_depassement = self.template_id.total_depassement
            self.amount = self.template_id.amount
            lis = []
            for line in self.template_id.type_service_line_ids:
                lis.append(
                    (
                        0,
                        0,
                        {
                            "id_tranche": line.id_tranche,
                            "tranche_de_no": line.tranche_de_no,
                            "tranche_a_no": line.tranche_a_no,
                            "frais_de_services": line.frais_de_services,
                        },
                    )
                )
            self.type_service_line_ids = lis

    def get_tranches_service_price(self):
        price = 0.0
        line_ids = self.type_service_line_ids.filtered(
            lambda l: float((l.tranche_de_no).replace(",", ""))
            <= float(self.total_consomme)
            and float((l.tranche_a_no).replace(",", "")) >= float(self.total_consomme)
        )
        price_unit = (
            float((line_ids[0].frais_de_services).replace(",", "")) if line_ids else 0.0
        )
        return price

    def get_product_unit_price(self):
        price_unit = 0.0
        if self.type_service == "fix":
            price_unit = (
                float((self.service_fee).replace(",", "")) if self.service_fee else 0.0
            ) + self.amount
        elif self.type_service == "tranches":
            price_unit = (
                self.get_tranches_service_price() * float(self.total_consomme)
                + self.amount
            )
        elif self.type_service == "aucun":
            price_unit = self.amount
        return price_unit

    @api.one
    def generate_subscription_invoice(self, date_invoice, renewal=False):
        # invoice gen for subscription

        if self.partner_id.property_payment_term:
            payment_term_id = self.partner_id.property_payment_term.id
        elif self.partner_id.categ_id and self.partner_id.categ_id.payment_term_id:
            payment_term_id = self.partner_id.categ_id.payment_term_id.id
        else:
            payment_term_id = False

        if self.partner_id.property_account_position:
            fiscal_position_id = self.partner_id.property_account_position.id
        elif self.partner_id.categ_id and self.partner_id.categ_id.fiscal_position_id:
            fiscal_position_id = self.partner_id.categ_id.fiscal_position_id.id
        else:
            fiscal_position_id = False

        vals = {
            "origin": self.name,
            "date_invoice": date_invoice,
            "user_id": self._uid,
            "partner_id": self.partner_id.id,
            "account_id": self.partner_id.property_account_receivable.id,
            "type": "out_invoice",
            "company_id": self.env.user.company_id.id,
            "currency_id": self.currency_id.id,
            "contract_id": self.id,
            "pricelist_id": self.pricelist_id and self.pricelist_id.id or False,
            "payment_term": payment_term_id,
            "fiscal_position": fiscal_position_id,
            "renewal": renewal,
            #'partner_bank_id':partner_bank and partner_bank[0].id or False,
            #'journal_id':journal and journal[0].id or False,
        }
        invoice_obj = self.env["account.invoice"]
        invoice = invoice_obj.create(vals)
        account_id = self.product_id.property_account_income.id
        if not account_id:
            account_id = self.product_id.categ_id.property_account_income_categ.id
        if not account_id:
            raise ValidationError(
                "Merci de définir un compte de revenues sur ce produit"
            )
        # taxes
        account = (
            self.product_id.property_account_income
            or self.product_id.categ_id.property_account_income_categ
        )
        taxes = self.product_id.taxes_id or account.tax_ids
        fpos = self.env["account.fiscal.position"].browse(False)
        fp_taxes = fpos.map_tax(taxes)
        # taxes
        final_amount = self.get_product_unit_price()
        line_vals = {
            "name": renewal
            and ("[REN]" + self.product_id.name)
            or self.product_id.name,
            "account_id": account_id,
            "product_id": self.product_id.id,
            #'product_category_id':self.product_category_id.id,
            "start_date": self.date_start,
            "end_date": self.date,
            "quantity": 1,
            "price_unit": final_amount,
            "uos_id": self.product_id.uom_id.id,
            "account_analytic_id": False,
            "invoice_id": invoice.id,
            "invoice_line_tax_id": [(6, 0, fp_taxes.ids)],
        }

        # Update account_id on line depending on fiscal position
        fpos = self.env["account.fiscal.position"].browse(fiscal_position_id)
        account = fpos.map_account(account)
        if account:
            account_id = account.id
            line_vals["account_id"] = account.id
        # Update account_id on line depending on fiscal position

        # Ligne budgétaire et compte analytique pour le calcul du budget
        fiscalyear_id = self.env["account.fiscalyear"].search(
            [("date_start", "<=", date_invoice), ("date_stop", ">=", date_invoice)]
        )
        if fiscalyear_id:
            domain = [
                ("product_id", "=", self.product_id.id),
                ("account_id", "=", account_id),
                ("fiscalyear_id", "=", fiscalyear_id[0].id),
            ]
            print "domain", domain, fiscal_position_id, account.code
            settings = self.env["budget.setting"].search(domain)

            if settings:
                line_vals["budget_item_id"] = settings[0].budget_line_id.id
                line_vals["account_analytic_id"] = settings[0].account_analytic_id.id
            else:
                raise ValidationError(
                    "Veuillez configurer un parametrage budget pour l'article "
                    + self.product_id.name
                )
        # Ligne budgétaire et compte analytique pour le calcul du budget

        invoice_obj.invoice_line.create(line_vals)
        invoice.button_reset_taxes()
        workflow.trg_validate(
            self._uid, "account.invoice", invoice.id, "invoice_open", self._cr
        )

        invoice.invoice_print_auto()
        # invoice.action_send_mail_auto()
        # invoice._gen_xml_file(9)

    @api.one
    def generate_subscription_draft_invoice(self, date_invoice, renewal=False):
        # invoice gen for subscription

        if self.partner_id.property_payment_term:
            payment_term_id = self.partner_id.property_payment_term.id
        elif self.partner_id.categ_id and self.partner_id.categ_id.payment_term_id:
            payment_term_id = self.partner_id.categ_id.payment_term_id.id
        else:
            payment_term_id = False

        if self.partner_id.property_account_position:
            fiscal_position_id = self.partner_id.property_account_position.id
        elif self.partner_id.categ_id and self.partner_id.categ_id.fiscal_position_id:
            fiscal_position_id = self.partner_id.categ_id.fiscal_position_id.id
        else:
            fiscal_position_id = False

        vals = {
            "origin": self.name,
            "date_invoice": date_invoice,
            "user_id": self._uid,
            "partner_id": self.partner_id.id,
            "account_id": self.partner_id.property_account_receivable.id,
            "type": "out_invoice",
            "company_id": self.env.user.company_id.id,
            "currency_id": self.currency_id.id,
            "contract_id": self.id,
            "pricelist_id": self.pricelist_id and self.pricelist_id.id or False,
            "payment_term": payment_term_id,
            "fiscal_position": fiscal_position_id,
            "renewal": renewal,
            #'partner_bank_id':partner_bank and partner_bank[0].id or False,
            #'journal_id':journal and journal[0].id or False,
        }
        invoice_obj = self.env["account.invoice"]
        invoice = invoice_obj.create(vals)
        account_id = self.product_id.property_account_income.id
        if not account_id:
            account_id = self.product_id.categ_id.property_account_income_categ.id
        if not account_id:
            raise ValidationError(
                "Merci de définir un compte de revenues sur ce produit"
            )
        # taxes
        account = (
            self.product_id.property_account_income
            or self.product_id.categ_id.property_account_income_categ
        )
        taxes = self.product_id.taxes_id or account.tax_ids
        fpos = self.env["account.fiscal.position"].browse(False)
        fp_taxes = fpos.map_tax(taxes)
        # taxes
        final_amount = self.get_product_unit_price()
        line_vals = {
            "name": renewal
            and ("[REN]" + self.product_id.name)
            or self.product_id.name,
            "account_id": account_id,
            "product_id": self.product_id.id,
            #'product_category_id':self.product_category_id.id,
            "start_date": self.date_start,
            "end_date": self.date,
            "quantity": 1,
            "price_unit": final_amount,
            "uos_id": self.product_id.uom_id.id,
            "account_analytic_id": False,
            "invoice_id": invoice.id,
            "invoice_line_tax_id": [(6, 0, fp_taxes.ids)],
        }

        # Update account_id on line depending on fiscal position
        fpos = self.env["account.fiscal.position"].browse(fiscal_position_id)
        account = fpos.map_account(account)
        if account:
            account_id = account.id
            line_vals["account_id"] = account.id
        # Update account_id on line depending on fiscal position

        # Ligne budgétaire et compte analytique pour le calcul du budget
        fiscalyear_id = self.env["account.fiscalyear"].search(
            [("date_start", "<=", date_invoice), ("date_stop", ">=", date_invoice)]
        )
        if fiscalyear_id:
            domain = [
                ("product_id", "=", self.product_id.id),
                ("account_id", "=", account_id),
                ("fiscalyear_id", "=", fiscalyear_id[0].id),
            ]
            print "domain", domain, fiscal_position_id, account.code
            settings = self.env["budget.setting"].search(domain)

            if settings:
                line_vals["budget_item_id"] = settings[0].budget_line_id.id
                line_vals["account_analytic_id"] = settings[0].account_analytic_id.id
            else:
                raise ValidationError(
                    "Veuillez configurer un parametrage budget pour l'article "
                    + self.product_id.name
                )
        # Ligne budgétaire et compte analytique pour le calcul du budget

        invoice_obj.invoice_line.create(line_vals)
        invoice.button_reset_taxes()

    def _check_open_paid_invoice_exist(self):
        invoice_id = self.env["account.invoice"].search(
            [("contract_id", "=", self.id), ("state", "in", ("open", "paid"))], limit=1
        )
        if invoice_id:
            return True
        else:
            return False

    def _check_draft_invoice_exist(self):
        invoice_id = self.env["account.invoice"].search(
            [("contract_id", "=", self.id), ("state", "=", "draft")], limit=1
        )
        return invoice_id

    def _get_open_invoice_for_voucher(self):
        invoice_id = self.env["account.invoice"].search(
            [("contract_id", "=", self.id), ("state", "=", "open")], limit=1
        )
        return invoice_id


class ContractServiceLine(models.Model):
    _name = "contract.service.line"
    _description = "Contract Service Lines"

    def _get_tranche_a(self):
        tranche_de_no = 0
        if self._context.get("contract_id"):
            contract_id = self.env["res.contract"].browse(
                self._context.get("contract_id", [])
            )
            if contract_id.type_service_line_ids:
                tranche_de_no = contract_id.type_service_line_ids[-1].tranche_a_no
                if tranche_de_no:
                    tranche_de_no = int(tranche_de_no) + 1
        return tranche_de_no

    contract_id = fields.Many2one("res.contract", string="Contract")
    id_tranche = fields.Integer(string="Id Tranche", readonly=True)
    tranche_de_no = fields.Char(string="Tranche de", default=_get_tranche_a)
    tranche_a_no = fields.Char(string="Tranche à")
    frais_de_services = fields.Char(string="Frais de service", required=True)

    @api.onchange("tranche_de_no", "tranche_a_no")
    def onchange_tranche_de_no_a_no(self):
        if self._context.get("transaction_no_limit"):
            if self.tranche_de_no and (
                int(self.tranche_de_no) > self._context.get("transaction_no_limit")
            ):
                raise ValidationError(
                    "Tranche de can not be greater than Nombre de transactions"
                )
            if self.tranche_a_no and (
                int(self.tranche_a_no) > self._context.get("transaction_no_limit")
            ):
                raise ValidationError(
                    "Tranche à can not be greater than Nombre de transactions"
                )
        if (
            self.tranche_de_no
            and self.tranche_a_no
            and int(self.tranche_de_no) > int(self.tranche_a_no)
        ):
            raise ValidationError("Tranche de can not be greater than Tranche à.")
        if self.tranche_de_no and not (self.tranche_de_no).isdigit():
            raise ValidationError("Tranche de can be in numbers.")
        if self.tranche_a_no and not (self.tranche_a_no).isdigit():
            raise ValidationError("Tranche à can be in numbers.")


# class AccountVoucher(models.Model):
#     _inherit = "account.voucher"

#     contract_id = fields.Many2one("res.contract", string="Contract")
#     reference = fields.Char(related="contract_id.name")

    # @api.multi
    # def write(self, values):
    #     if values.get('state') and values['state'] == 'posted' and self.contract_id:
    #         voucher_ids = self.search_count([('contract_id', '=', self.contract_id.id), ('state', '=', 'posted')])
    #         if voucher_ids >= 1:
    #             raise ValidationError("You already posted voucher against same subscription.")
    #     return super(AccountVoucher, self).write(values)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def write(self, values):
        if values.get("state") and self.contract_id:
            if values["state"] == "open":
                open_invoice_ids = self.search_count(
                    [("contract_id", "=", self.contract_id.id), ("state", "=", "open")]
                )
                if open_invoice_ids >= 1:
                    raise ValidationError(
                        "More than one invoice can not be set as open state with same subscription."
                    )
            elif values["state"] == "paid":
                paid_invoice_ids = self.search_count(
                    [("contract_id", "=", self.contract_id.id), ("state", "=", "paid")]
                )
                if paid_invoice_ids >= 1:
                    raise ValidationError(
                        "More than one invoice can not be set as paid state with same subscription."
                    )
        return super(AccountInvoice, self).write(values)
