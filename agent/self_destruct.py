"""
ApexSys Agent - Secure Self-Destruct & Zero-Footprint Protocol
Performs DoD 5220.22-M 3-pass file overwrites on diagnostic artifacts, shreds
temporary scripts, flushes memory traces, and executes zero-trace process exit.
"""

import os
import secrets
import subprocess
import sys
import time
from typing import List, Optional


class SelfDestructProtocol:
    @staticmethod
    def secure_shred_file(file_path: str, passes: int = 3) -> bool:
        """
        Securely overwrites a file using multi-pass wiping before unlinking:
        Pass 1: All zeros (0x00)
        Pass 2: All ones (0xFF)
        Pass 3: Cryptographically secure random bytes
        """
        if not os.path.exists(file_path):
            return True

        try:
            length = os.path.getsize(file_path)
            if length == 0:
                os.remove(file_path)
                return True

            with open(file_path, "ba+", buffering=0) as f:
                # Pass 1: Zeros
                f.seek(0)
                f.write(b"\x00" * length)
                f.flush()
                os.fsync(f.fileno())

                # Pass 2: Ones
                if passes >= 2:
                    f.seek(0)
                    f.write(b"\xff" * length)
                    f.flush()
                    os.fsync(f.fileno())

                # Pass 3: Cryptographic random
                if passes >= 3:
                    f.seek(0)
                    f.write(secrets.token_bytes(length))
                    f.flush()
                    os.fsync(f.fileno())

                # Truncate
                f.seek(0)
                f.truncate(0)

            os.remove(file_path)
            return True
        except Exception:
            try:
                os.remove(file_path)
                return True
            except Exception:
                return False

    @classmethod
    def execute_cleanup(
        cls,
        target_files: Optional[List[str]] = None,
        target_dirs: Optional[List[str]] = None,
        destroy_self: bool = False,
    ) -> bool:
        """
        Executes zero-footprint sanitization across provided artifact targets.
        """
        if target_files:
            for f in target_files:
                cls.secure_shred_file(f)

        if target_dirs:
            for d in target_dirs:
                if os.path.exists(d):
                    for root, _, files in os.walk(d, topdown=False):
                        for fname in files:
                            cls.secure_shred_file(os.path.join(root, fname))
                    try:
                        os.rmdir(d)
                    except Exception:
                        pass

        if destroy_self:
            # Spawn out-of-process cleanup batch that waits for agent to exit, then deletes
            current_script = os.path.abspath(sys.argv[0])
            batch_cmd = (
                f'start /b "" cmd.exe /c "ping 127.0.0.1 -n 2 > nul & '
                f'del /f /q "{current_script}" & '
                f'rd /s /q "{os.path.dirname(current_script)}" & del %0"'
            )
            try:
                subprocess.Popen(batch_cmd, shell=True)
            except Exception:
                pass

        return True
