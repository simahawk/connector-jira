# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, exceptions, _

from ...unit.backend_adapter import JiraAdapter
from ...backend import jira


class JiraProjectTask(models.Model):
    _name = 'jira.project.task'
    _inherit = 'jira.binding'
    _inherits = {'project.task': 'odoo_id'}
    _description = 'Jira Tasks'

    odoo_id = fields.Many2one(comodel_name='project.task',
                              string='Task',
                              required=True,
                              index=True,
                              ondelete='restrict')
    jira_key = fields.Char(
        string='Key',
        readonly=True,
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name='jira.issue.type',
        string='Issue Type',
        readonly=True,
    )
    jira_epic_link_id = fields.Many2one(
        comodel_name='jira.project.task',
        string='Epic',
        readonly=True,
    )
    jira_parent_id = fields.Many2one(
        comodel_name='jira.project.task',
        string='Parent Issue',
        readonly=True,
        help="Parent issue when the issue is a subtask. "
             "Empty if the type of parent is filtered out "
             "of the synchronizations.",
    )

    @api.multi
    def unlink(self):
        if any(self.mapped('external_id')):
            raise exceptions.UserError(
                _('A Jira task cannot be deleted.')
            )
        return super(JiraProjectTask, self).unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.project.task',
        inverse_name='odoo_id',
        copy=False,
        string='Task Bindings',
        context={'active_test': False},
    )
    jira_issue_type = fields.Char(
        compute='_compute_jira_issue_type',
        string='JIRA Issue Type',
        store=True,
    )
    jira_compound_key = fields.Char(
        compute='_compute_jira_compound_key',
        string='JIRA Key',
        store=True,
    )
    jira_epic_link_task_id = fields.Many2one(
        comodel_name='project.task',
        compute='_compute_jira_epic_link_task_id',
        string='JIRA Epic',
        store=True,
    )
    jira_parent_task_id = fields.Many2one(
        comodel_name='project.task',
        compute='_compute_jira_parent_task_id',
        string='JIRA Parent',
        store=True,
    )

    @api.depends('jira_bind_ids.jira_issue_type_id.name')
    def _compute_jira_issue_type(self):
        for record in self:
            types = record.mapped('jira_bind_ids.jira_issue_type_id.name')
            record.jira_issue_type = ','.join([t for t in types if t])

    @api.depends('jira_bind_ids.jira_key')
    def _compute_jira_compound_key(self):
        for record in self:
            keys = record.mapped('jira_bind_ids.jira_key')
            record.jira_compound_key = ','.join([k for k in keys if k])

    @api.depends('jira_bind_ids.jira_epic_link_id.odoo_id')
    def _compute_jira_epic_link_task_id(self):
        for record in self:
            tasks = record.mapped(
                'jira_bind_ids.jira_epic_link_id.odoo_id'
            )
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks

    @api.depends('jira_bind_ids.jira_parent_id.odoo_id')
    def _compute_jira_parent_task_id(self):
        for record in self:
            tasks = record.mapped(
                'jira_bind_ids.jira_parent_id.odoo_id'
            )
            if len(tasks) == 1:
                record.jira_parent_task_id = tasks

    @api.multi
    def name_get(self):
        names = []
        for task in self:
            task_id, name = super(ProjectTask, task).name_get()[0]
            if task.jira_compound_key:
                name = '[%s] %s' % (task.jira_compound_key, name)
            names.append((task_id, name))
        return names


@jira
class TaskAdapter(JiraAdapter):
    _model_name = 'jira.project.task'

    def read(self, id_, fields=None):
        return self.client.issue(id_, fields=fields).raw

    def search(self, jql):
        # we need to have at least one field which is not 'id' or 'key'
        # due to this bug: https://github.com/pycontribs/jira/pull/289
        fields = 'id,updated'
        issues = self.client.search_issues(jql, fields=fields, maxResults=None)
        return [issue.id for issue in issues]
