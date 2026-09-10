from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ThreeDColdStartDeploymentTest(unittest.TestCase):
    def text(self, rel: str) -> str:
        path = ROOT / rel
        self.assertTrue(path.is_file(), f"missing {rel}")
        return path.read_text(encoding="utf-8")

    def test_startup_shell_is_large_enough_to_exercise_burst_regression(self):
        index = self.text("static/index.html")
        assets = re.findall(r'(?:src|href)="(/[^"#?]+)', index)
        self.assertGreater(len(set(assets)), 72)

    def test_root_shell_is_not_request_rate_limited(self):
        nginx = self.text("deploy/nginx/vm-https.conf")
        self.assertIn("zone=mgc_vm_api_rate:10m rate=12r/s", nginx)
        api_block = nginx.split("    location /api/ {", 1)[1].split("\n    }", 1)[0]
        root_block = nginx.split("    location / {", 1)[1].split("\n    }", 1)[0]
        self.assertIn("limit_req zone=mgc_vm_api_rate burst=72 nodelay;", api_block)
        self.assertNotIn("limit_req ", root_block)
        self.assertIn("limit_conn mgc_vm_conn 40;", root_block)

    def test_critical_3d_assets_exist_and_are_checked_by_vm_acceptance(self):
        critical = [
            "static/digital_vehicle_3d_v630.css",
            "static/assembly_builder_v630.css",
            "static/powertrain_builder_v630.css",
            "static/factory_digital_thread_v630.css",
            "static/frontend/digital_vehicle_3d_v630.js",
            "static/frontend/digital_truck_3d_v630.js",
            "static/frontend/assembly_builder_v630.js",
            "static/frontend/powertrain_builder_v630.js",
            "static/frontend/factory_digital_thread_v630.js",
            "static/frontend/production_motion_v630.js",
            "static/frontend/factory_process_simulator_v630.js",
            "static/frontend/factory_simulator_stage2_v630.js",
            "static/frontend/factory_training_intelligence_v631.js",
        ]
        check = self.text("deploy/vm/check_vm.sh")
        for rel in critical:
            self.assertTrue((ROOT / rel).is_file(), rel)
            public_path = "/" + rel.removeprefix("static/")
            self.assertIn(public_path, check)

    def test_factory_optional_assets_remain_wired_from_boot(self):
        boot = self.text("static/frontend/boot.js")
        for asset in (
            "/production_motion_v630.css",
            "/factory_process_simulator_v630.css",
            "/factory_simulator_stage2_v630.css",
            "/factory_training_intelligence_v631.css",
            "/frontend/production_motion_v630.js",
            "/frontend/factory_process_simulator_v630.js",
            "/frontend/factory_simulator_stage2_v630.js",
            "/frontend/factory_training_intelligence_v631.js",
        ):
            self.assertIn(asset, boot)

    def test_browser_like_parallel_asset_smoke_is_in_ci(self):
        workflow = self.text(".github/workflows/ci-v631-vm-deployment-kit.yml")
        self.assertIn("Browser-like cold-start asset burst", workflow)
        self.assertIn("ThreadPoolExecutor(max_workers=32)", workflow)
        self.assertIn("assert len(paths) > 72", workflow)
        self.assertIn("Cold-start asset failures:", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
