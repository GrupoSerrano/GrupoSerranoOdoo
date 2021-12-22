# -*- encoding: utf-8 -*-
# Coded by German Ponce Dominguez 
#     ▬▬▬▬▬.◙.▬▬▬▬▬  
#       ▂▄▄▓▄▄▂  
#    ◢◤█▀▀████▄▄▄▄▄▄ ◢◤  
#    █▄ █ █▄ ███▀▀▀▀▀▀▀ ╬  
#    ◥ █████ ◤  
#     ══╩══╩═  
#       ╬═╬  
#       ╬═╬ Dream big and start with something small!!!  
#       ╬═╬  
#       ╬═╬ You can do it!  
#       ╬═╬   Let's go...
#    ☻/ ╬═╬   
#   /▌  ╬═╬   
#   / \
# Cherman Seingalt - german.ponce@outlook.com

from odoo import api, fields, models, _, tools
from datetime import datetime, date
import time
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv import osv, expression


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit ='res.partner'

    partner_insurance_number = fields.Char('No. Póliza Seguro')
    
    insurance_policy = fields.Char(string="No. Póliza Seguro",
                                                help="Atributo: PolizaRespCivil", size=50)

    ambiental_insurance_policy = fields.Char(string="No. Póliza Seguro Medio Amb.",
                                                help="Atributo: PolizaMedAmbiente", size=50)

    transport_insurance_policy = fields.Char(string="No. Póliza Carga",
                                                help="Atributo: PolizaCarga", size=50)

    cp_driver_license = fields.Char('Numero de Licencia')

    #### Automatización ####
    idorigen = fields.Char(string="ID Origen", default="OR")

    iddestino = fields.Char(string="ID Destino", default="DE")

    figure_type_id = fields.Many2one('waybill.figura.transporte', 'Tipo Figura',
                                         help="Atributo: Tipo TipoFigura")

    transport_part_ids = fields.Many2many('waybill.parte.transporte', 'partner_figure_part_rel',
                                         'transport_id', 'parte_id', 'Tipos Parte Transporte')
