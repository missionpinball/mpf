# mpf
__version_info__ = ('0', '30', '0', 'dev10')
__version__ = '.'.join(__version_info__)

__bcp_version_info__ = ('1', '0')
__bcp_version__ = '.'.join(__bcp_version_info__)

__config_version_info__ = '3'
__config_version__ = '.'.join(__config_version_info__)
__config_version_url__ = "https://missionpinball.com/docs/configuration-file-reference/config-version-3/"


version_str = "MPF v{} (config_version={}, BCP v{})".format(__version__,
                                                           __config_version__,
                                                           __bcp_version__)
