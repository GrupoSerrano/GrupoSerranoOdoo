# -*- coding: utf-8 -*-

{
    "name"      : "Complemento de Carta Porte - EE",
    "version"   : "14.0",
    "author"    : "Argil Consulting & German Ponce Dominguez",
    "website"   : "https://www.argil.mx",
    "license"   : "OEEL-1",
    "category"  : "Localization/Mexico",
    "description": """

Comprobante Traslado
====================

Este modulo permite incorporar el CFDI de Traslado para la Facturación Electronica 3.3 con Complemento de Carta Porte.

""",
    
    "depends": [
        "hr",
        "l10n_mx_edi",
        "product_unspsc",
        "l10n_mx_einvoice_waybill_base",
        "l10n_mx_einvoice_waybill_base_address_data",
        ],
    "data"    : [

                'security/ir.model.access.csv',
                'wizard/update_lines_wizard_view.xml',
                'wizard/sat_catalogos_wizard_view.xml',
                'views/account_view.xml',
                'views/product_view.xml',
                'views/hr_view.xml',
                'views/res_partner_view.xml',
                'data/waybill_complement.xml',
                'reports/invoice_facturae.xml',
    ],
        "installable": True,
}
