#!/usr/bin/env python3

# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


"""
 ****************************************************************************
 Description:       Provide cental configuration.
 ****************************************************************************
"""

from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf

from ha import const
from ha.util.consul_kv_store import ConsulKvStore
from ha.const import _DELIM
from ha.core.error import HAInvalidNode

class ConfigManager:
    """
    HA configuration to provide central ha configuration
    """

    _conf = []
    _cluster_confstore = None

    @staticmethod
    def init(log_name, log_path=None, level="INFO",
            backup_count=5, file_size_in_mb=10, syslog_server=None,
            syslog_port=None, console_output=True, config_file=None):
        """
        Initialize ha conf and log
        Args:
            log_name (str): service_name for log init.
        """
        # log_path will be piked from cluster config only
        # log_path can be updated for testing only
        ConfigManager._conf_init(config_file)
        if log_name:
            if not log_path:
                log_path = Conf.get(const.HA_GLOBAL_INDEX, f"LOG{_DELIM}path")
            level = Conf.get(const.HA_GLOBAL_INDEX, f"LOG{_DELIM}level")
            # console_output=True will redirect all log to console and log file both
            # TODO: CORTX-28795 filter redirect log for console and file
            Log.init(service_name=log_name, log_path=log_path, level=level,
                    backup_count=backup_count, file_size_in_mb=file_size_in_mb,
                    syslog_server=syslog_server, syslog_port=syslog_port,
                    console_output=console_output)
            Log.info(f"Started logging for service {log_name}")

    @staticmethod
    def _conf_init(config_file):
        """
        Init Conf
        """
        if not config_file:
            config_file = f"yaml://{const.HA_CONFIG_FILE}"
        ConfigManager._safe_load(const.HA_GLOBAL_INDEX, config_file)

    @staticmethod
    def get_confstore(kv_enable_batch = False):
        """
        Initialize and get confstore if _cluster_confstore is None.
        Used by config manager methods to check and initialize confstore if needed.
        """
        if ConfigManager._cluster_confstore is None:
            consul_endpoint = Conf.get(const.HA_GLOBAL_INDEX, f'consul_config{_DELIM}endpoint')
            consul_host = consul_endpoint.split(":")[1].strip("//")
            consul_port = consul_endpoint.split(":")[-1]
            ConfigManager._cluster_confstore = ConsulKvStore(prefix=const.CLUSTER_CONFSTORE_PREFIX,
                                                             host=consul_host, port=consul_port,
                                                             enable_batch=kv_enable_batch)
        return ConfigManager._cluster_confstore

    @staticmethod
    def load_controller_schema():
        """
        Load controller interface schema for cluster management.
        """
        ConfigManager._safe_load(const.CM_CONTROLLER_INDEX, f"json://{const.CM_CONTROLLER_SCHEMA}")

    @staticmethod
    def load_filter_rules():
        """
        Loads alert filter rules.
        """
        ConfigManager._safe_load(const.ALERT_FILTER_INDEX, f"json://{const.ALERT_FILTER_RULES_FILE}")

    @staticmethod
    def load_alert_events_rules():
        """
        Loads alert event rules.
        """
        ConfigManager._safe_load(const.ALERT_EVENT_INDEX, f"json://{const.ALERT_EVENT_RULES_FILE}")

    @staticmethod
    def _safe_load(index: str, url: str):
        """
        Load config if not loaded
        """
        if index not in ConfigManager._conf:
            Conf.load(index, url)
            ConfigManager._conf.append(index)

    @staticmethod
    def get_major_version():
        """
        Get product version

        Returns:
            [int]: Return version
        """
        version = Conf.get(const.HA_GLOBAL_INDEX, f"VERSION{_DELIM}version")
        major_version = version.split('.')
        return major_version[0]

    @staticmethod
    def get_local_node() -> str:
        """
        Get local node name.
        """
        return Conf.get(const.HA_GLOBAL_INDEX, f"CLUSTER_MANAGER{_DELIM}local_node")

    @staticmethod
    def get_hw_env() -> str:
        """
        Get if system is running on VM or actual h/w.
        """
        return Conf.get(const.HA_GLOBAL_INDEX, f"CLUSTER_MANAGER{_DELIM}env")

    @staticmethod
    def get_node_name(node_id: str) -> str:
        """
        Get node_name(pvtfqdn) from node_id
        Args:
            node_id (str): Node ID from cluster nodes.
        Returns: str
        """
        confstore = ConfigManager.get_confstore()
        nodeid_dict = confstore.get(f"{const.PVTFQDN_TO_NODEID_KEY}")
        for key, nodeid in nodeid_dict.items():
            if nodeid == node_id:
                node_name = key.split('/')[-1]
                return node_name
        raise HAInvalidNode(f"node_id {node_id} is not valid.")

    @staticmethod
    def get_node_id(node_name: str) -> str:
        """
        Get node_id from node_name
        Args:
            node_name (str): Node name from cluster nodes.
        Returns: str
            node_id (str): Node ID from cluster nodes.
        """
        confstore = ConfigManager.get_confstore()
        key_val = confstore.get(f"{const.PVTFQDN_TO_NODEID_KEY}/{node_name}")
        _, node_id = key_val.popitem()
        return node_id
