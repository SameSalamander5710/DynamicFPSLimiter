import os
import sys
import subprocess

TASK_NAME = "DynamicFPSLimiter"

class AutoStartManager:
    def __init__(self, app_path=None, task_name=TASK_NAME):
        self.app_path = app_path or self.get_current_app_path()
        self.task_name = task_name

    @staticmethod
    def get_current_app_path():
        return os.path.abspath(sys.argv[0])

    def task_exists(self):
        result = subprocess.run(f'schtasks /Query /TN "{self.task_name}"',
                                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0

    def create(self):
        cmd = [
            "schtasks",
            "/Create",
            "/SC", "ONLOGON",
            "/TN", self.task_name,
            "/TR", f'"{self.app_path}"',
            "/RL", "HIGHEST",
            "/F"
        ]
        subprocess.run(" ".join(cmd), shell=True)

    def delete(self):
        if self.task_exists():
            subprocess.run(f'schtasks /Delete /TN "{self.task_name}" /F', shell=True)


    def update_if_needed(self):
        if self.task_exists():
            result = subprocess.run(f'schtasks /Query /TN "{self.task_name}" /XML',
                                    shell=True, stdout=subprocess.PIPE, text=True)
            if self.app_path.lower() not in result.stdout.lower():
                self.delete()
                self.create()
        else:
            self.create()





