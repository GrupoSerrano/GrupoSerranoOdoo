# -*- encoding: utf-8 -*-


from odoo import api, fields, models, _, tools, release
from datetime import datetime
from datetime import datetime, date
from odoo.exceptions import UserError, RedirectWarning, ValidationError

## Manejo de Fechas y Horas ##
from pytz import timezone
import pytz
import base64

from xml.dom import minidom

import re

import logging
_logger = logging.getLogger(__name__)

import re

class AccountInvoice(models.Model):
    _inherit = 'account.move'

