# -*- coding: utf-8 -*-
{
    "name": "Gestion de la nouvelle tarification PORTNET",
    "author": "TECH-IT sarl",
    "description": """
        Ce module permet de rajouter des fonctionnalités spécifiques au Nouvelles Tarification PORTNET
----------------------------------------------------------
""",
    "website": "https://www.tech-it.ma",
    "summary": """Nouvelle Tarification""",
    "version": "4.7",
    "support": "contact@tech-it.ma",
    "category": "Autre",
    "depends": ["portnet_subscription", "portnet_invoicing", "sale"],
    "data": [
        "data/package_sequence.xml",
        "security/ir.model.access.csv",
        "views/share.xml",
        "views/contract_view.xml",
        "views/res_transaction_view.xml",
        "views/res_partner_view.xml",
        "views/account_view.xml",
        "views/bureau_douanier_view.xml",
        "views/code_port_view.xml",
        "wizard/contract_validation_view.xml",
    ],
    "installable": True,
    "application": False,
}
