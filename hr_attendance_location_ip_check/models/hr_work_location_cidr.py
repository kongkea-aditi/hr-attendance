import ipaddress

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrWorkLocationCidr(models.Model):
    _name = "hr.work.location.cidr"
    _description = "Work Location CIDR Network"
    _order = "sequence, id"

    sequence = fields.Integer(default=10, index=True)
    work_location_id = fields.Many2one(
        "hr.work.location",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(
        string="Network Name",
        required=True,
        help="Descriptive name for this network range",
    )
    cidr = fields.Char(
        string="Network CIDR",
        required=True,
        help="e.g. 192.168.1.0/24",
    )
    active = fields.Boolean(default=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        related="work_location_id.company_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_location_cidr",
            "unique(work_location_id, cidr, company_id)",
            "CIDR must be unique per work location and company",
        ),
    ]

    @api.constrains("cidr")
    def _check_cidr_validity(self):
        """Validate CIDR format and check for overlaps."""
        for record in self:
            try:
                network = ipaddress.ip_network(record.cidr)

                domain = [
                    ("id", "!=", record.id),
                    ("work_location_id", "=", record.work_location_id.id),
                ]
                for existing in self.search(domain):
                    existing_net = ipaddress.ip_network(existing.cidr)
                    if (
                        network.overlaps(existing_net)
                        and existing.active
                        and record.active
                    ):
                        raise ValidationError(
                            _("CIDR %(new)s overlaps with existing %(old)s")
                            % {
                                "new": record.cidr,
                                "old": existing.cidr,
                            }
                        )

            except ValueError as e:
                raise ValidationError(
                    _("Invalid CIDR for %(location)s: %(cidr)s\n%(error)s")
                    % {
                        "location": record.work_location_id.name or "",
                        "cidr": record.cidr,
                        "error": str(e),
                    }
                ) from e
