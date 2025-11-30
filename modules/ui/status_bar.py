"""
Status Bar Module
Version: 2.0.0
Erweiterte Statusleiste mit PLC-Status, Uhrzeit, Sonnen-/Mondinfo

📁 SPEICHERORT: modules/ui/status_bar.py

Features:
- PLC-Verbindungsstatus (● grün/rot, AMS Net ID)
- Datum & Uhrzeit (Wochentag, DD.MM.YYYY, HH:MM:SS)
- Sonnenauf-/untergang (astronomische Berechnung)
- Mondphase (8 Phasen: 🌑🌒🌓🌔🌕🌖🌗🌘)
- Auto-Update jede Sekunde
- Zeitzonen-Handling (MEZ/MESZ)
"""

from module_manager import BaseModule
from typing import Any
import tkinter as tk
from datetime import datetime, timedelta
import math


class StatusBar(BaseModule):
    """
    Status-Leiste
    
    Features:
    - PLC-Verbindungsstatus
    - Datum & Uhrzeit
    - Sonnenauf-/untergang
    - Mondphase
    """
    
    NAME = "status_bar"
    VERSION = "2.0.0"
    DESCRIPTION = "Erweiterte Statusleiste"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'plc_communication']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.plc = None
        self.status_frame = None
        self.labels = {}
        self.update_job = None
        
        # Standort (Haltern am See)
        self.latitude = 51.7453
        self.longitude = 7.1836
    
    def initialize(self, app_context: Any):
        """Initialisiert Status-Leiste"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.plc = app_context.module_manager.get_module('plc_communication')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_status_bar(self, parent: tk.Widget) -> tk.Frame:
        """Erstellt Status-Leiste"""
        # Haupt-Frame
        self.status_frame = self.gui.create_frame(
            parent,
            bg=self.gui.colors['primary'],
            relief=tk.FLAT
        )
        
        # Links - PLC-Status
        left_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        left_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        self.labels['plc_status'] = tk.Label(
            left_frame,
            text="●",
            font=('Segoe UI', 14, 'bold'),
            bg=self.gui.colors['primary'],
            fg='lime'
        )
        self.labels['plc_status'].pack(side=tk.LEFT)
        
        self.labels['plc_text'] = tk.Label(
            left_frame,
            text="Verbunden: 192.168.2.162.1.1",
            font=('Segoe UI', 9),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['plc_text'].pack(side=tk.LEFT, padx=5)
        
        # Mitte - Datum & Uhrzeit
        middle_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        middle_frame.pack(side=tk.LEFT, expand=True)
        
        self.labels['date'] = tk.Label(
            middle_frame,
            text="",
            font=('Segoe UI', 10, 'bold'),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['date'].pack(side=tk.LEFT, padx=5)
        
        self.labels['time'] = tk.Label(
            middle_frame,
            text="",
            font=('Segoe UI', 12, 'bold'),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['time'].pack(side=tk.LEFT, padx=10)
        
        # Rechts - Sonne & Mond
        right_frame = tk.Frame(self.status_frame, bg=self.gui.colors['primary'])
        right_frame.pack(side=tk.RIGHT, padx=15, pady=8)
        
        self.labels['sun'] = tk.Label(
            right_frame,
            text="☀️ --:-- / --:--",
            font=('Segoe UI', 9),
            bg=self.gui.colors['primary'],
            fg='white'
        )
        self.labels['sun'].pack(side=tk.LEFT, padx=10)
        
        self.labels['moon'] = tk.Label(
            right_frame,
            text="🌙",
            font=('Segoe UI', 14),
            bg=self.gui.colors['primary']
        )
        self.labels['moon'].pack(side=tk.LEFT)
        
        # Start Updates
        self.start_updates()
        
        return self.status_frame
    
    def start_updates(self):
        """Startet regelmäßige Updates"""
        self.update_datetime()
        self.update_sun_moon()
        self.update_plc_status()
        
        # Update jede Sekunde
        if self.status_frame:
            self.update_job = self.status_frame.after(1000, self.start_updates)
    
    def update_datetime(self):
        """Aktualisiert Datum & Uhrzeit"""
        now = datetime.now()
        
        # Datum
        weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        weekday = weekdays[now.weekday()]
        date_str = f"{weekday}, {now.strftime('%d.%m.%Y')}"
        
        if 'date' in self.labels:
            self.labels['date'].config(text=date_str)
        
        # Uhrzeit
        time_str = now.strftime('%H:%M:%S')
        if 'time' in self.labels:
            self.labels['time'].config(text=time_str)
    
    def update_plc_status(self):
        """Aktualisiert PLC-Status"""
        if not self.plc:
            return
        
        status = self.plc.get_connection_status()
        
        if status['connected']:
            color = 'lime'
            text = f"Verbunden: {status['ams_net_id']}"
        else:
            color = 'red'
            text = f"Getrennt: {status['ams_net_id']}"
        
        if 'plc_status' in self.labels:
            self.labels['plc_status'].config(fg=color)
        
        if 'plc_text' in self.labels:
            self.labels['plc_text'].config(text=text)
    
    def update_sun_moon(self):
        """Aktualisiert Sonnen- und Mondinfo"""
        now = datetime.now()
        
        # Nur alle 10 Minuten neu berechnen
        if not hasattr(self, '_last_sun_update') or \
           (now - self._last_sun_update).seconds > 600:
            
            # Sonnenzeiten berechnen
            sunrise, sunset = self.calculate_sun_times(now)
            
            sun_text = f"☀️ {sunrise} / {sunset}"
            if 'sun' in self.labels:
                self.labels['sun'].config(text=sun_text)
            
            # Mondphase
            moon_phase = self.get_moon_phase(now)
            if 'moon' in self.labels:
                self.labels['moon'].config(text=moon_phase)
            
            self._last_sun_update = now
    
    def calculate_sun_times(self, date: datetime) -> tuple:
        """
        Berechnet Sonnenauf- und -untergang (vereinfacht)
        Basiert auf astronomischen Formeln
        """
        # Tag des Jahres
        day_of_year = date.timetuple().tm_yday
        
        # Deklination der Sonne
        declination = -23.45 * math.cos(math.radians(360/365 * (day_of_year + 10)))
        
        # Stundenwinkel
        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        
        try:
            cos_hour_angle = (-math.tan(lat_rad) * math.tan(dec_rad))
            cos_hour_angle = max(-1, min(1, cos_hour_angle))  # Clamp
            hour_angle = math.degrees(math.acos(cos_hour_angle))
        except:
            hour_angle = 90
        
        # Sonnenaufgang und -untergang in Dezimalstunden
        sunrise_decimal = 12 - hour_angle / 15 - self.longitude / 15
        sunset_decimal = 12 + hour_angle / 15 - self.longitude / 15
        
        # Zeitzone +1 (MEZ)
        sunrise_decimal += 1
        sunset_decimal += 1
        
        # Sommerzeit berücksichtigen (März-Oktober)
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
        year = date.year
        month = date.month
        day = date.day
        
        # Mondzyklus: ~29.53 Tage
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
