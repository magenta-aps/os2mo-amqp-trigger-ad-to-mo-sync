# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""AD Connection handling."""
from ssl import CERT_NONE
from ssl import CERT_REQUIRED
from typing import cast
from typing import ContextManager

from fastramqpi.context import Context
from ldap3 import Connection
from ldap3 import NTLM
from ldap3 import RANDOM
from ldap3 import RESTARTABLE
from ldap3 import Server
from ldap3 import ServerPool
from ldap3 import Tls

from .config import ServerConfig
from .config import Settings


def construct_server(server_config: ServerConfig) -> Server:
    """Construct an LDAP3 server from settings.

    Args:
        server_config: The settings to construct the server instance from.

    Returns:
        The constructed server instance used for LDAP connections.
    """
    tls_configuration = Tls(
        validate=CERT_NONE if server_config.insecure else CERT_REQUIRED
    )
    return Server(
        host=server_config.host,
        port=server_config.port,
        use_ssl=server_config.use_ssl,
        tls=tls_configuration,
        connect_timeout=server_config.timeout,
    )


def configure_ad_connection(settings: Settings) -> ContextManager:
    """Configure an AD connection.

    Args:
        settings: The Settings instance to configure our ad connection with.

    Returns:
        ContextManager that can be opened to establish an AD connection.
    """
    servers = list(map(construct_server, settings.ad_controllers))
    # Pick the next server to use at random, discard non-active servers
    server_pool = ServerPool(servers, RANDOM, active=True, exhaust=True)
    connection = Connection(
        server=server_pool,
        # We always authenticate via NTLM
        user=settings.ad_domain + "\\" + settings.ad_user,
        password=settings.ad_password.get_secret_value(),
        authentication=NTLM,
        # Restartable means the operation is retries in case of failure
        client_strategy=RESTARTABLE,
        # We only need to read ADGUIDs, not write anything
        read_only=True,
    )
    return cast(ContextManager, connection)


async def ad_healthcheck(context: Context) -> bool:
    """AD connection Healthcheck.

    Args:
        context: To lookup ad_connection in.

    Returns:
        Whether the AMQPSystem is OK.
    """
    ad_connection = context["user_context"]["ad_connection"]
    return cast(bool, ad_connection.bound)
