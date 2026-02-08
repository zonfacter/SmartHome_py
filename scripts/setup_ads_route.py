#!/usr/bin/env python3
"""
ADS Route Setup Script
Richtet die ADS-Verbindung zwischen diesem Linux-System und der CX8090 PLC ein.

Konfiguration:
  Lokal (VM):   192.168.2.123 / AMS 192.168.2.123.1.1
  PLC (CX8090): 192.168.2.162 / AMS 192.168.2.162.1.1
  TwinCAT 2, Port 801
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyads

# ── Konfiguration ──────────────────────────────────────────────
LOCAL_AMS_NET_ID = "192.168.2.123.1.1"
LOCAL_IP = "192.168.2.123"

PLC_AMS_NET_ID = "192.168.2.162.1.1"
PLC_IP = "192.168.2.162"
PLC_AMS_PORT = pyads.PORT_TC2PLC1  # 801 (TwinCAT 2)

PLC_USERNAME = "Administrator"
PLC_PASSWORD = "1"
ROUTE_NAME = "SmartHomeVM"
# ───────────────────────────────────────────────────────────────


def setup_ads_route():
    print("=" * 60)
    print("  ADS Route Setup - SmartHome VM -> CX8090")
    print("=" * 60)
    print()

    # ── Schritt 1: Lokale AMS Net ID + Route setzen ──
    print("[1/3] Setze lokale AMS Net ID und Route...")
    try:
        pyads.open_port()
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        pyads.add_route(PLC_AMS_NET_ID, PLC_IP)
        print(f"  OK  Lokal: {LOCAL_AMS_NET_ID}")
        print(f"  OK  Route: {PLC_AMS_NET_ID} -> {PLC_IP}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  OK  Route existiert bereits")
        else:
            print(f"  FEHLER: {e}")
            return False

    # ── Schritt 2: Route auf PLC anlegen ──
    print()
    print("[2/3] Lege Route auf der CX8090 an...")
    try:
        pyads.add_route_to_plc(
            sending_net_id=LOCAL_AMS_NET_ID,
            adding_host_name=LOCAL_IP,
            ip_address=PLC_IP,
            username=PLC_USERNAME,
            password=PLC_PASSWORD,
            route_name=ROUTE_NAME
        )
        print(f"  OK  Route '{ROUTE_NAME}' auf PLC angelegt")
    except Exception as e:
        err = str(e)
        if "already exists" in err.lower():
            print(f"  OK  Route existiert bereits auf der PLC")
        else:
            print(f"  INFO: {e} (Route manuell pruefen)")

    pyads.close_port()

    # CX8090 braucht Pause zwischen Verbindungen
    print()
    print("[3/3] Teste Verbindung zur CX8090...")
    print("       Warte 5s (CX8090 Connection-Cooldown)...")
    time.sleep(5)

    try:
        plc = pyads.Connection(PLC_AMS_NET_ID, PLC_AMS_PORT, PLC_IP)
        plc.set_timeout(10000)
        plc.open()
        time.sleep(2)

        # Device Info (zuverlaessiger als read_state auf CX8090)
        name, version = plc.read_device_info()
        print(f"  OK  Verbindung hergestellt!")
        print(f"       PLC:     {name} v{version.version}.{version.revision}.{version.build}")

        # Symbole zaehlen
        try:
            symbols = plc.get_all_symbols()
            print(f"       Symbole: {len(symbols)}")
        except Exception:
            pass

        plc.close()

    except Exception as e:
        print(f"  FEHLER: {e}")
        return False

    print()
    print("=" * 60)
    print("  ADS Route Setup ERFOLGREICH!")
    print(f"  {LOCAL_AMS_NET_ID} <-> {PLC_AMS_NET_ID}")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = setup_ads_route()
    sys.exit(0 if success else 1)
