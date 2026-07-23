from collections.abc import Awaitable
from typing import Any

import aiohttp
from aiohttp.resolver import AsyncResolver

CLOUDFLARE_DNS_SERVERS = ("1.1.1.1", "1.0.0.1")
DNS_CACHE_TTL_SECONDS = 300


class CloudflareDNSConnector(aiohttp.TCPConnector):
    """Cloudflare DNS를 사용하고 세션 종료 시 resolver도 함께 닫는 커넥터."""

    def __init__(self, **kwargs: Any) -> None:
        self._cloudflare_resolver = AsyncResolver(nameservers=list(CLOUDFLARE_DNS_SERVERS))
        self._cloudflare_resolver_closed = False
        super().__init__(
            resolver=self._cloudflare_resolver,
            ttl_dns_cache=DNS_CACHE_TTL_SECONDS,
            **kwargs,
        )

    @property
    def dns_resolver(self) -> AsyncResolver:
        return self._cloudflare_resolver

    def close(self) -> Awaitable[None]:
        connector_close = super().close()
        if self._cloudflare_resolver_closed:
            return connector_close

        self._cloudflare_resolver_closed = True

        async def close_connector_and_resolver() -> None:
            try:
                await connector_close
            finally:
                await self._cloudflare_resolver.close()

        return close_connector_and_resolver()


def create_http_session(**kwargs: Any) -> aiohttp.ClientSession:
    """Cloudflare DNS를 사용하는 aiohttp 세션을 생성한다."""
    return aiohttp.ClientSession(connector=CloudflareDNSConnector(), **kwargs)
