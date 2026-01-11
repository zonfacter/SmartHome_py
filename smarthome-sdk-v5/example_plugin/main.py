from base_plugin import BasePlugin
import random
import time

class ExampleSensorPlugin(BasePlugin):
    """
    Referenz-Plugin zur Demonstration des v5.1 SDKs.
    Simuliert einen Sensor, um das Routing zu testen.
    """
    def initialize(self):
        self.log.info("🚀 Beispiel-Plugin startet...")
        self.sensor_name = self.config.get("name", "Demo-Sensor")

    def execute(self):
        """Hauptschleife des Plugins - wird vom System überwacht"""
        while self.is_running:
            # 1. Daten generieren/lesen
            simulated_val = round(random.uniform(18.0, 26.0), 2)
            
            # 2. Daten an den Router senden (inkl. Spam-Schutz Check)
            # Tag-Struktur: plugin_id/path
            self.publish(f"sensors/{self.sensor_name}/temp", simulated_val)
            
            # 3. CPU-Schonung: Das System erwartet ein kooperatives Verhalten
            time.sleep(self.config.get("poll_interval", 5.0))

    def on_data(self, tag, value, source):
        """Wird aufgerufen, wenn abonnierte Daten im Router eintreffen"""
        if "command/restart" in tag:
            self.log.warning("Restart-Signal von extern empfangen!")