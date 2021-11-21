# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
import math



class Document(models.Model):
    _inherit = 'document.document'

    
    code = fields.Char(string='Code')
    book = fields.Binary(string='File Excel')
    book_filename = fields.Char(string='File Name')

