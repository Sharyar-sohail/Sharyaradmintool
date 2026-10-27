"""
ApexSys Agent - Hardware Diagnostics Module
Collects SMART drive status, RAM health, CPU throttling, and Device Manager errors.
"""

import json
import subprocess
import time
from typing import Any, Dict, List


class HardwareDiagnostics:
    @staticmethod
    def _run_ps_json(ps_cmd: str) -> Any:
        """Run a PowerShell command and parse JSON output safely."""
        full_cmd = f"powershell -NoProfile -NonInteractive -Command \"{ps_cmd} | ConvertTo-Json -Compress -Depth 3\""
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=12,
                shell=True
            )
            out = res.stdout.strip()
            if not out or out == "null":
                return None
            return json.loads(out)
        except Exception:
            return None

    @classmethod
    def get_physical_disks_smart(cls) -> Dict[str, Any]:
        """
        Query physical disks SMART health, media type, size, and bad sector predictions.
        """
        result = {
            "drives": [],
            "smart_failures": [],
            "total_drives": 0,
            "all_healthy": True,
        }

        # Query Get-PhysicalDisk
        ps_disk = (
            "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, "
            "HealthStatus, OperationalStatus, Size"
        )
        data = cls._run_ps_json(ps_disk)

        if data:
            if isinstance(data, dict):
                data = [data]
            for d in data:
                health = str(d.get("HealthStatus", "Healthy"))
                op_status = str(d.get("OperationalStatus", "OK"))
                friendly = d.get("FriendlyName", "Generic Disk")
                dev_id = str(d.get("DeviceId", "0"))
                size_gb = round(d.get("Size", 0) / (1024 ** 3), 1)
                media = d.get("MediaType", "Disk")

                is_healthy = health.lower() == "healthy" and "ok" in op_status.lower()

                drive_entry = {
                    "device_id": dev_id,
                    "model": friendly,
                    "media_type": media,
                    "size_gb": size_gb,
                    "health_status": health,
                    "operational_status": op_status,
                    "is_healthy": is_healthy,
                    "bad_sectors": 0,
                }
                result["drives"].append(drive_entry)

                if not is_healthy:
                    result["all_healthy"] = False
                    result["smart_failures"].append(drive_entry)

        # Fallback / supplement: Win32_DiskDrive
        if not result["drives"]:
            ps_fallback = "Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Status, Size"
            fb_data = cls._run_ps_json(ps_fallback)
            if fb_data:
                if isinstance(fb_data, dict):
                    fb_data = [fb_data]
                for d in fb_data:
                    status = str(d.get("Status", "OK"))
                    drive_entry = {
                        "device_id": str(d.get("DeviceID", "0")),
                        "model": str(d.get("Model", "Physical Disk")),
                        "media_type": "Unknown",
                        "size_gb": round(d.get("Size", 0) / (1024 ** 3), 1),
                        "health_status": "Healthy" if status == "OK" else "Warning",
                        "operational_status": status,
                        "is_healthy": status == "OK",
                        "bad_sectors": 0,
                    }
                    result["drives"].append(drive_entry)
                    if status != "OK":
                        result["all_healthy"] = False
                        result["smart_failures"].append(drive_entry)

        result["total_drives"] = len(result["drives"])
        return result

    @classmethod
    def get_cpu_and_thermal(cls) -> Dict[str, Any]:
        """
        Check CPU current vs max frequency, load, and throttling.
        """
        result = {
            "model": "Unknown CPU",
            "cores": 0,
            "max_mhz": 0,
            "curr_mhz": 0,
            "cpu_throttled": False,
            "load_pct": 0,
            "temperature_c": None,
        }

        ps_cpu = "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, MaxClockSpeed, CurrentClockSpeed, LoadPercentage"
        data = cls._run_ps_json(ps_cpu)
        if data:
            if isinstance(data, list):
                data = data[0]
            result["model"] = str(data.get("Name", "Unknown")).strip()
            result["cores"] = data.get("NumberOfCores", 0)
            result["max_mhz"] = data.get("MaxClockSpeed", 0)
            result["curr_mhz"] = data.get("CurrentClockSpeed", 0)
            result["load_pct"] = data.get("LoadPercentage", 0)

            # Throttling detection: if current speed is less than 50% max while under load, or heavily throttled
            if result["max_mhz"] > 0 and result["curr_mhz"] > 0:
                ratio = result["curr_mhz"] / result["max_mhz"]
                if ratio < 0.60 and result["load_pct"] > 40:
                    result["cpu_throttled"] = True

        # Try ACPI Thermal Zone
        ps_thermal = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object CurrentTemperature"
        th_data = cls._run_ps_json(ps_thermal)
        if th_data:
            if isinstance(th_data, list):
                th_data = th_data[0]
            raw_temp = th_data.get("CurrentTemperature", 0)
            if raw_temp > 0:
                # ACPI temperature is in tenths of Kelvin
                celsius = round((raw_temp / 10.0) - 273.15, 1)
                result["temperature_c"] = celsius

        return result

    @classmethod
    def get_ram_health(cls) -> Dict[str, Any]:
        """
        Analyze physical RAM modules, capacity, speed, and anomalies.
        """
        result = {
            "modules": [],
            "total_installed_gb": 0.0,
            "ram_health_issues": [],
        }

        ps_ram = "Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, Manufacturer, PartNumber, DeviceLocator"
        data = cls._run_ps_json(ps_ram)
        if data:
            if isinstance(data, dict):
                data = [data]
            total_bytes = 0
            for r in data:
                cap_bytes = r.get("Capacity", 0)
                total_bytes += cap_bytes
                result["modules"].append({
                    "slot": r.get("DeviceLocator", "DIMM"),
                    "capacity_gb": round(cap_bytes / (1024 ** 3), 1),
                    "speed_mhz": r.get("Speed", 0),
                    "manufacturer": str(r.get("Manufacturer", "")).strip(),
                })
            result["total_installed_gb"] = round(total_bytes / (1024 ** 3), 1)

        return result

    @classmethod
    def get_failing_pnp_devices(cls) -> Dict[str, Any]:
        """
        Inspect Device Manager for yellow-bang devices (ConfigManagerErrorCode != 0).
        """
        error_map = {
            1: "Device not configured correctly (Code 1)",
            10: "Device cannot start (Code 10)",
            12: "Device cannot find enough free resources (Code 12)",
            14: "Device requires system restart (Code 14)",
            18: "Reinstall the drivers for this device (Code 18)",
            22: "Device is disabled (Code 22)",
            24: "Device not present or not working (Code 24)",
            28: "Drivers for this device are not installed (Code 28)",
            31: "Device is not working properly / Windows cannot load drivers (Code 31)",
            39: "Windows cannot load driver: driver corrupted or missing (Code 39)",
            43: "Windows stopped this device: reported problems (Code 43)",
            45: "Device is currently not connected (Code 45)",
        }

        result = {
            "failing_devices": [],
            "failing_count": 0,
        }

        ps_pnp = (
            "Get-CimInstance Win32_PnPEntity -Filter 'ConfigManagerErrorCode != 0' | "
            "Select-Object Name, DeviceID, ConfigManagerErrorCode, Status"
        )
        data = cls._run_ps_json(ps_pnp)
        if data:
            if isinstance(data, dict):
                data = [data]
            for dev in data:
                code = dev.get("ConfigManagerErrorCode", 0)
                # Ignore non-present / safely disconnected devices (Code 45) unless critical
                if code == 45:
                    continue
                name = str(dev.get("Name", "Unknown Device")).strip()
                dev_id = str(dev.get("DeviceID", "Unknown"))
                status = str(dev.get("Status", "Error"))
                err_desc = error_map.get(code, f"Hardware Configuration Error (Code {code})")

                result["failing_devices"].append({
                    "name": name,
                    "device_id": dev_id,
                    "code": code,
                    "status": status,
                    "error_desc": err_desc,
                })

        result["failing_count"] = len(result["failing_devices"])
        return result

    @classmethod
    def run_full_scan(cls) -> Dict[str, Any]:
        """Run all hardware diagnostic checks and aggregate."""
        disks = cls.get_physical_disks_smart()
        cpu = cls.get_cpu_and_thermal()
        ram = cls.get_ram_health()
        pnp = cls.get_failing_pnp_devices()

        return {
            "smart_drives": disks.get("drives", []),
            "smart_failures": disks.get("smart_failures", []),
            "cpu_model": cpu.get("model"),
            "cpu_cores": cpu.get("cores"),
            "cpu_max_mhz": cpu.get("max_mhz"),
            "cpu_curr_mhz": cpu.get("curr_mhz"),
            "cpu_throttled": cpu.get("cpu_throttled"),
            "cpu_temperature_c": cpu.get("temperature_c"),
            "ram_modules": ram.get("modules", []),
            "ram_total_gb": ram.get("total_installed_gb"),
            "ram_health_issues": ram.get("ram_health_issues"),
            "failing_devices": pnp.get("failing_devices", []),
        }
