# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from ...custom import (config_create,
                       config_delete,
                       config_bind,
                       config_unbind)

import unittest
from argparse import Namespace
from azure.cli.core.azclierror import InvalidArgumentValueError, ArgumentUsageError
from ..._validators_enterprise import validate_refresh_interval
try:
    import unittest.mock as mock
except ImportError:
    from unittest import mock

from azure.cli.core.mock import DummyCli
from azure.cli.core import AzCommandsLoader
from azure.cli.core.commands import AzCliCommand

from knack.log import get_logger
from knack.util import CLIError

logger = get_logger(__name__)
free_mock_client = mock.MagicMock()


def _get_test_cmd():
    cli_ctx = DummyCli()
    cli_ctx.data['subscription_id'] = '00000000-0000-0000-0000-000000000000'
    loader = AzCommandsLoader(cli_ctx, resource_type='Microsoft.AppPlatform')
    cmd = AzCliCommand(loader, 'test', None)
    cmd.command_kwargs = {'resource_type': 'Microsoft.AppPlatform'}
    cmd.cli_ctx = cli_ctx
    return cmd


def _cf_resource_group(cli_ctx, subscription_id=None):
    client = mock.MagicMock()
    rg = mock.MagicMock()
    rg.location = 'east us'
    client.resource_groups.get.return_value = rg
    return client


def _get_basic_mock_client(*_):
    return mock.MagicMock()


class BasicTest(unittest.TestCase):
    def __init__(self, methodName: str = ...):
        super().__init__(methodName=methodName)
        self.created_resource = None

    def setUp(self):
        resp = super().setUp()
        free_mock_client.reset_mock()
        return resp

    @mock.patch('azext_spring._utils.cf_resource_groups', _cf_resource_group)
    def _execute(self, resource_group, **kwargs):
        client = kwargs.pop('client', None) or _get_basic_mock_client()
        config_create(_get_test_cmd(), client, 'myasa', resource_group)
        call_args = client.config_servers.begin_create_or_update.call_args_list
        self.assertEqual(1, len(call_args))
        self.assertEqual(4, len(call_args[0][0]))
        self.assertEqual((resource_group),
                         (call_args[0][0][0]))
        self.created_resource = call_args[0][0][3]

class ConfigCreateCommandTest(BasicTest):
    def test_config_create_resource_exists(self, mock_models):
        cmd = _get_test_cmd()
        client = _cf_resource_group(cmd.cli_ctx)
        service = "my-service"
        resource_group = "my-resource-group"

        client.config_servers.get.return_value = "existing_resource"

        with self.assertRaises(CLIError) as cm:
            self._execute(resource_group, client=client)
        
        self.assertEqual(str(cm.exception), "Config server 'default' already exists.")
        client.config_servers.get.assert_called_once_with(resource_group, service, "default")
        client.config_servers.begin_create_or_update.assert_not_called()

    def test_config_create_resource_not_exists(self, mock_models):
        cmd = _get_test_cmd()
        client = _cf_resource_group(cmd.cli_ctx)
        service = "my-service"
        resource_group = "my-resource-group"

        mock_models.ConfigServerProperties.return_value = "mock_properties"
        mock_models.ConfigServerResource.return_value = "mock_resource"

        client.config_servers.get.return_value = None

        self._execute(resource_group, client=client)

        resource = self.created_resource
        self.assertIsNotNone(resource.properties)
        client.config_servers.begin_create_or_update.assert_called_once_with(resource_group, service, "default", "mock_resource")

class ConfigDeleteCommandTest(BasicTest):
    def test_config_delete(self):
        cmd = _get_test_cmd()
        client = _cf_resource_group(cmd.cli_ctx)
        service = "my-service"
        resource_group = "my-resource-group"

        self._execute(cmd, client, service, resource_group)

        client.config_servers.begin_delete.assert_called_once_with(resource_group, service, "default")

