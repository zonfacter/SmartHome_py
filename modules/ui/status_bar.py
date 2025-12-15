"""
Status Bar Module v2.1.0
Erweiterte Statusleiste mit Fehler-Anzeige

📁 SPEICHERORT: modules/ui/status_bar.py

🆕 v2.1.0:
- Besserer PLC-Status (zeigt Timeouts/Fehler)
- MQTT-Status
- Error-Warning bei Netzwerk-Problemen
- Visuelles Feedback

Features:
- PLC-Verbindungsstatus mit Error-Details
- MQTT-Status
- Datum & Uhrzeit (Live)
- Sonnenauf-/untergang
- Mondphase
- Auto-Update jede Sekunde
"""

from module_manager import BaseModule
from typing import Any
import tkinter as tk
from datetime import datetime, timedelta
import math


class StatusBar(BaseModule):
    """
    Status-Leiste v2.1.0
    
    ⭐ NEU: Error-Warnings!
    - Zeigt PLC-Timeouts
    - Zeigt Fehler-Count
    - Visuelles Warning
    
    Features:
    - PLC-Verbindungsstatus mit Details
    - MQTT-Status
    - Datum & Uhrzeit
    - Sonnenauf-/untergang
    - Mondphase
    """
    
    NAME = "status_bar"
    VERSION = "2.1.0"
    DESCRIPTION = "Erweiterte Statusleiste mit Error-Anzeige"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'plc_communication']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.plc = None
        self.mqtt = None
        self.status_frame = None
        self.labels = {}
        self.update_job = None
        
        # Standort (Neuenkirchen, NRW)
        self.latitude = 52.0
        self.longitude = 7.4
    
    def initialize(self, app_context: Any):
        """Initialisiert Status-Leiste"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.plc = app_context.module_manager.get_module('plc_communication')
        self.mqtt = app_context.module_manager.get_module('mqtt_integration')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_status_bar(self, parent: tk.Widget) -> tk.Frame:
        """Erstellt Status-Leiste"""
        # Haupt-Frame
        self.status_frame = self.gui.create_frame(
            parent,
            bg=self.gui.colors['primary'],
            relief=tk.FLAT
        )
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ⭐ Links: PLC & MQTT Status
        left_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        # PLC-Status
        self.labels['plc_indicator'] = tk.Label(
            left_frame,
            text="●",
            font=('Segoe UI', 14),
            bg=self.gui.colors['primary'],
            fg='red'
        )
        self.labels['plc_indicator'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.labels['plc_status'] = tk.Label(
            left_frame,
            text="PLC: Getrennt",
            font=('Segoe UI', 10),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['plc_status'].pack(side=tk.LEFT, padx=5)
        
        # ⭐ Error-Warning (nur bei Problemen)
        self.labels['error_warning'] = tk.Label(
            left_frame,
            text="",
            font=('Segoe UI', 10, 'bold'),
            bg=self.gui.colors['primary'],
            fg='#FF5722'
        )
        self.labels['error_warning'].pack(side=tk.LEFT, padx=10)
        
        # Separator
        tk.Label(
            left_frame,
            text="|",
            font=('Segoe UI', 10),
            bg=self.gui.colors['primary'],
            fg='white'
        ).pack(side=tk.LEFT, padx=5)
        
        # MQTT-Status
        self.labels['mqtt_indicator'] = tk.Label(
            left_frame,
            text="●",
            font=('Segoe UI', 14),
            bg=self.gui.colors['primary'],
            fg='gray'
        )
        self.labels['mqtt_indicator'].pack(side=tk.LEFT, padx=(5, 5))
        
        self.labels['mqtt_status'] = tk.Label(
            left_frame,
            text="MQTT: --",
            font=('Segoe UI', 10),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['mqtt_status'].pack(side=tk.LEFT, padx=5)
        
        # ⭐ Mitte: Datum & Uhrzeit (GRÖẞER!)
        center_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        center_frame.pack(side=tk.LEFT, expand=True)
        
        self.labels['datetime'] = tk.Label(
            center_frame,
            text="",
            font=('Segoe UI', 12, 'bold'),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['datetime'].pack()
        
        # ⭐ Rechts: Sonnen- & Mond-Info
        right_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Sonnenzeiten
        self.labels['sun'] = tk.Label(
            right_frame,
            text="☀️ --:-- / --:--",
            font=('Segoe UI', 10),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['sun'].pack(side=tk.LEFT, padx=10)
        
        # Mondphase
        self.labels['moon'] = tk.Label(
            right_frame,
            text="🌑",
            font=('Segoe UI', 14),
            bg=self.gui.colors['primary']
        )
        self.labels['moon'].pack(side=tk.LEFT, padx=5)
        
        return self.status_frame
    
    def start_updates(self):
        """Startet Auto-Updates (jede Sekunde)"""
        self.update_status()
    
    def update_status(self):
        """Aktualisiert alle Status-Anzeigen"""
        if not self.status_frame:
            return
        
        try:
            # ⭐ PLC-Status mit Error-Details
            self._update_plc_status()
            
            # ⭐ MQTT-Status
            self._update_mqtt_status()
            
            # Datum & Uhrzeit
            self._update_datetime()
            
            # Sonnenzeiten (alle 10 Minuten)
            if datetime.now().minute % 10 == 0:
                self._update_sun_times()
            
            # Mondphase (täglich)
            if datetime.now().hour == 0 and datetime.now().minute == 0:
                self._update_moon_phase()
        
        except Exception as e:
            print(f"  ⚠️  Status-Bar Update-Fehler: {e}")
        
        # Nächster Update in 1 Sekunde
        self.update_job = self.status_frame.after(1000, self.update_status)
    
    def _update_plc_status(self):
        """⭐ v2.1.0: PLC-Status mit Error-Details"""
        if not self.plc:
            return
        
        status = self.plc.get_connection_status()
        connected = status.get('connected', False)
        ams_net_id = status.get('ams_net_id', 'N/A')
        errors = status.get('consecutive_errors', 0)
        max_errors = status.get('max_errors', 20)
        
        if connected:
            # Verbunden
            self.labels['plc_indicator'].config(fg='#4CAF50')  # Grün
            
            # ⭐ Zeige Fehler-Count wenn vorhanden
            if errors > 0:
                # Warning
                self.labels['plc_status'].config(
                    text=f"PLC: {ams_net_id}",
                    fg='#FF9800'  # Orange
                )
                self.labels['error_warning'].config(
                    text=f"⚠️ {errors}/{max_errors} Fehler"
                )
            else:
                # Alles OK
                self.labels['plc_status'].config(
                    text=f"PLC: {ams_net_id}",
                    fg='white'
                )
                self.labels['error_warning'].config(text="")
        else:
            # Getrennt
            self.labels['plc_indicator'].config(fg='#FF5722')  # Rot
            self.labels['plc_status'].config(
                text="PLC: Getrennt",
                fg='#FF5722'
            )
            self.labels['error_warning'].config(
                text="❌ Keine Verbindung!"
            )
    
    def _update_mqtt_status(self):
        """⭐ v2.1.0: MQTT-Status"""
        if not self.mqtt:
            self.labels['mqtt_indicator'].config(fg='gray')
            self.labels['mqtt_status'].config(text="MQTT: N/A")
            return
        
        if self.mqtt.connected:
            broker = self.mqtt.config.get('broker', 'N/A')
            self.labels['mqtt_indicator'].config(fg='#4CAF50')  # Grün
            self.labels['mqtt_status'].config(
                text=f"MQTT: {broker}",
                fg='white'
            )
        else:
            self.labels['mqtt_indicator'].config(fg='#FF5722')  # Rot
            self.labels['mqtt_status'].config(
                text="MQTT: Getrennt",
                fg='#FF5722'
            )
    
    def _update_datetime(self):
        """Aktualisiert Datum & Uhrzeit"""
        now = datetime.now()
        
        # Wochentag auf Deutsch
        weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        weekday = weekdays[now.weekday()]
        
        # Format: Mo, 15.12.2025  20:30:45
        datetime_str = f"{weekday}, {now.strftime('%d.%m.%Y')}  {now.strftime('%H:%M:%S')}"
        
        self.labels['datetime'].config(text=datetime_str)
    
    def _update_sun_times(self):
        """Aktualisiert Sonnenzeiten"""
        sunrise, sunset = self.calculate_sun_times(datetime.now())
        self.labels['sun'].config(text=f"☀️ {sunrise} / {sunset}")
    
    def _update_moon_phase(self):
        """Aktualisiert Mondphase"""
        moon_emoji = self.get_moon_phase(datetime.now())
        self.labels['moon'].config(text=moon_emoji)
    
    def calculate_sun_times(self, date: datetime) -> tuple:
        """
        Berechnet Sonnenauf- und -untergang
        
        Vereinfachte Berechnung für Mitteleuropa
        """
        # Tag im Jahr
        day_of_year = date.timetuple().tm_yday
        
        # Sonnendeklination (approximiert)
        declination = 23.45 * math.sin(math.radians((360/365) * (day_of_year - 81)))
        
        # Stundenwinkel für Sonnenauf-/untergang
        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        
        cos_hour_angle = (-math.tan(lat_rad) * math.tan(dec_rad))
        
        # Prüfe ob Sonne auf-/untergeht
        if cos_hour_angle < -1:
            # Polartag
            return "Polartag", "Polartag"
        elif cos_hour_angle > 1:
            # Polarnacht
            return "Polarnacht", "Polarnacht"
        
        hour_angle = math.degrees(math.acos(cos_hour_angle))
        
        # Sonnenaufgang/-untergang (in Dezimalstunden)
        sunrise_decimal = 12 - (hour_angle / 15) - (self.longitude / 15)
        sunset_decimal = 12 + (hour_angle / 15) - (self.longitude / 15)
        
        # Sommerzeit-Korrektur (März-Oktober)
        if 3 <= date.month <= 10:
            sunrise_decimal += 1
            sunset_decimal += 1
        
        # Zu Stunden:Minuten
        sunrise_h = int(sunrise_decimal)
        sunrise_m = int((sunrise_decimal - sunrise_h) * 60)
        
        sunset_h = int(sunset_decimal)
        sunset_m = int((sunset_decimal - sunset_h) * 60)
        
        sunrise_str = f"{sunrise_h:02d}:{sunrise_m:02d}"
        sunset_str = f"{sunset_h:02d}:{sunset_m:02d}"
        
        return sunrise_str, sunset_str
    
    def get_moon_phase(self, date: datetime) -> str:
        """Berechnet Mondphase"""
        # Vereinfachte Berechnung
        known_new_moon = datetime(2000, 1, 6, 18, 14)
        days_since = (date - known_new_moon).days
        moon_age = days_since % 29.53
        
        # Mondphasen
        if moon_age < 1.85:
            return "🌑"  # Neumond
        elif moon_age < 7.38:
            return "🌒"  # Zunehmend
        elif moon_age < 9.23:
            return "🌓"  # Erstes Viertel
        elif moon_age < 14.77:
            return "🌔"  # Zunehmend
        elif moon_age < 16.61:
            return "🌕"  # Vollmond
        elif moon_age < 22.15:
            return "🌖"  # Abnehmend
        elif moon_age < 23.99:
            return "🌗"  # Letztes Viertel
        else:
            return "🌘"  # Abnehmend
    
    def shutdown(self):
        """Stoppt Updates"""
        if self.update_job:
            try:
                self.status_frame.after_cancel(self.update_job)
            except:
                pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        StatusBar.NAME,
        StatusBar.VERSION,
        StatusBar.DESCRIPTION,
        StatusBar,
        author=StatusBar.AUTHOR,
        dependencies=StatusBar.DEPENDENCIES
    )
