from mpf.core.config_player import ConfigPlayer


class BcpPlayer(ConfigPlayer):

    config_file_section = 'bcp_player'
    show_section = 'bcp'

player_cls = BcpPlayer
