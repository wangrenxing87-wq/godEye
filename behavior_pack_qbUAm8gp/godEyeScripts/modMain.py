# -*- coding: utf-8 -*-
from mod.common.mod import Mod
import mod.server.extraServerApi as serverApi
import mod.client.extraClientApi as clientApi
from godEyeScripts import config


@Mod.Binding(name=config.NAMESPACE, version=config.VERSION)
class GodEyeMod(object):
    @Mod.InitServer()
    def init_server(self):
        serverApi.RegisterSystem(config.NAMESPACE, config.SERVER_SYSTEM,
                                 "godEyeScripts.server_system.GodEyeServer")

    @Mod.InitClient()
    def init_client(self):
        clientApi.RegisterSystem(config.NAMESPACE, config.CLIENT_SYSTEM,
                                 "godEyeScripts.client_system.GodEyeClient")

    @Mod.DestroyServer()
    def destroy_server(self):
        pass  # System.Destroy owns listeners, caches and effects.

    @Mod.DestroyClient()
    def destroy_client(self):
        pass
