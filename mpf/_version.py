__version__ = '0.30.0.dev434'
__bcp_version__ = '1.0'
__config_version__ = '3'

version = "MPF v{} (config_version={}, BCP v{})".format(__version__,
                                                        __config_version__,
                                                        __bcp_version__)

try:
    from mpf.mc._version import (__version__ as __mc_version__,
                                 __bcp_version__ as __mc_bcp_version__,
                                 __config_version__ as __mc_config_version__)

    version += "\nMPF-MC v{} (config_version={}, BCP v{})".format(
        __mc_version__, __mc_config_version__, __mc_bcp_version__)

except ImportError:
    pass
