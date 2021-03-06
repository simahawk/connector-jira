# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job

from ...unit.backend_adapter import JiraAdapter
from ...unit.importer import (
    BatchImporter,
)
from ...backend import jira


class JiraIssueType(models.Model):
    _name = 'jira.issue.type'
    _inherit = 'jira.binding'
    _description = 'Jira Issue Type'

    name = fields.Char(required=True, readonly=True)
    description = fields.Char(readonly=True)

    @api.multi
    def is_sync_for_project(self, project_binding):
        self.ensure_one()
        if not project_binding:
            return False
        return self in project_binding.sync_issue_type_ids

    @job(default_channel='root.connector_jira.import')
    def import_batch(self, backend, from_date=None, to_date=None):
        """ Prepare a batch import of issue types from Jira

        from_date and to_date are ignored for issue types
        """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(BatchImporter)
            importer.run()


@jira
class IssueTypeAdapter(JiraAdapter):
    _model_name = 'jira.issue.type'

    def read(self, id_):
        return self.client.issue_type(id_).raw

    def search(self):
        issues = self.client.issue_types()
        return [issue.id for issue in issues]
