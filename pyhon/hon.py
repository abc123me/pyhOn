import asyncio
import copy
from typing import List, Optional, Dict, Any
from typing_extensions import Self

from aiohttp import ClientSession

from pyhon import HonAPI, exceptions
from pyhon.appliance import HonAppliance


class Hon:
    def __init__(self, email: str, password: str, session: ClientSession | None = None):
        self._email: str = email
        self._password: str = password
        self._session: ClientSession | None = session
        self._appliances: List[HonAppliance] = []
        self._api: Optional[HonAPI] = None

    async def __aenter__(self):
        return await self.create()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def api(self) -> HonAPI:
        if self._api is None:
            raise exceptions.NoAuthenticationException
        return self._api

    async def create(self) -> Self:
        self._api = await HonAPI(
            self._email, self._password, session=self._session
        ).create()
        await self.setup()
        return self

    @property
    def appliances(self) -> List[HonAppliance]:
        return self._appliances

    async def _create_appliance(self, appliance_data: Dict[str, Any], zone=0) -> None:
        appliance = HonAppliance(self._api, appliance_data, zone=zone)
        if appliance.mac_address is None:
            return
        await asyncio.gather(
            *[
                appliance.load_attributes(),
                appliance.load_commands(),
                appliance.load_statistics(),
            ]
        )
        self._appliances.append(appliance)

    async def setup(self):
        appliance: Dict
        for appliance in (await self._api.load_appliances())["payload"]["appliances"]:
            for zone in range(int(appliance.get("zone", "0"))):
                await self._create_appliance(appliance.copy(), zone=zone + 1)
            await self._create_appliance(appliance)

    async def close(self):
        await self._api.close()