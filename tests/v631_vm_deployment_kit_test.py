from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VMDeploymentKitTest(unittest.TestCase):
    def text(self, rel: str) -> str:
        path = ROOT / rel
        self.assertTrue(path.is_file(), f"missing {rel}")
        return path.read_text(encoding="utf-8")

    def test_required_handoff_files_exist(self):
        required = [
            "VM_IT_DIRECTOR.md",
            ".env.vm.example",
            "docker-compose.vm.prod.yml",
            "deploy/nginx/vm-https.conf",
            "deploy/vm/common.sh",
            "deploy/vm/setup_vm.sh",
            "deploy/vm/install_vm.sh",
            "deploy/vm/check_vm.sh",
            "deploy/vm/backup_vm.sh",
            "deploy/vm/restore_vm.sh",
            "deploy/vm/update_vm.sh",
            "deploy/vm/start_vm.sh",
            "deploy/vm/stop_vm.sh",
        ]
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_vm_compose_is_https_only_at_host_edge(self):
        compose = self.text("docker-compose.vm.prod.yml")
        self.assertIn('MGC_HTTPS_PORT:-443}:8443', compose)
        self.assertIn('COOKIE_SECURE: "true"', compose)
        self.assertIn('READY_REQUIRE_SECURE_COOKIE: "true"', compose)
        self.assertIn('internal: true', compose)
        self.assertIn('./deploy/nginx/vm-https.conf', compose)
        db_block = compose.split("  db:\n", 1)[1].split("\n  app:\n", 1)[0]
        app_block = compose.split("  app:\n", 1)[1].split("\n  nginx:\n", 1)[0]
        self.assertNotIn("ports:", db_block)
        self.assertNotIn("ports:", app_block)
        self.assertNotIn('"5432:5432"', compose)
        self.assertNotIn('"8000:8000"', compose)

    def test_nginx_tls_and_forwarding_contract(self):
        nginx = self.text("deploy/nginx/vm-https.conf")
        self.assertIn("listen 8443 ssl;", nginx)
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", nginx)
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", nginx)
        self.assertIn("server_tokens off;", nginx)
        self.assertIn("Strict-Transport-Security", nginx)
        self.assertIn("proxy_pass http://mgc_vm_app;", nginx)

    def test_env_template_contains_no_real_secret(self):
        env = self.text(".env.vm.example")
        for marker in (
            "CHANGE_ME_DB_PASSWORD",
            "CHANGE_ME_OIDC_SECRET",
            "CHANGE_ME_ADMIN_PASSWORD",
            "CHANGE_ME_METRICS_TOKEN",
            "CHANGE_ME_VM_IP_OR_DNS",
        ):
            self.assertIn(marker, env)
        self.assertIn("MGC_HTTPS_PORT=443", env)
        self.assertIn("COOKIE_SECURE=true", env)

    def test_scripts_cover_install_health_backup_restore_update(self):
        install = self.text("deploy/vm/install_vm.sh")
        check = self.text("deploy/vm/check_vm.sh")
        backup = self.text("deploy/vm/backup_vm.sh")
        restore = self.text("deploy/vm/restore_vm.sh")
        update = self.text("deploy/vm/update_vm.sh")
        stop = self.text("deploy/vm/stop_vm.sh")
        self.assertIn("compose build --pull app", install)
        self.assertIn("wait_ready", install)
        self.assertIn("/health/ready", check)
        self.assertIn("pg_isready", check)
        self.assertIn("pg_dump", backup)
        self.assertIn("sha256sum", backup)
        self.assertIn("psql -v ON_ERROR_STOP=1", restore)
        self.assertIn("merge --ff-only origin/main", update)
        self.assertRegex(stop, r"(?m)^compose down --remove-orphans$")
        self.assertNotRegex(stop, r"(?m)^\s*compose\s+down\s+.*-v")

    def test_setup_generates_secrets_and_tls_locally(self):
        setup = self.text("deploy/vm/setup_vm.sh")
        self.assertIn("openssl rand -hex 32", setup)
        self.assertIn("openssl req -x509", setup)
        self.assertIn("MGC_TLS_CERT_SOURCE", setup)
        self.assertIn("MGC_TLS_KEY_SOURCE", setup)
        self.assertIn("chmod 600", setup)
        self.assertNotIn("curl http", setup)
        self.assertNotIn("wget http", setup)

    def test_handoff_doc_has_operational_controls(self):
        doc = self.text("VM_IT_DIRECTOR.md")
        for phrase in (
            "4 vCPU",
            "8 GB RAM",
            "TCP 443",
            "5432",
            "8000",
            "backup_vm.sh",
            "restore_vm.sh",
            "update_vm.sh",
            "check_vm.sh",
            "корпоративного CA",
        ):
            self.assertIn(phrase, doc)

    def test_deployment_layer_does_not_own_game_scoring(self):
        paths = [
            "docker-compose.vm.prod.yml",
            "deploy/nginx/vm-https.conf",
            "deploy/vm/common.sh",
            "deploy/vm/setup_vm.sh",
            "deploy/vm/install_vm.sh",
            "deploy/vm/check_vm.sh",
            "deploy/vm/backup_vm.sh",
            "deploy/vm/restore_vm.sh",
            "deploy/vm/update_vm.sh",
        ]
        joined = "\n".join(self.text(p) for p in paths)
        for forbidden in ("/api/games/", "submitAnswer(", "awarded_xp", "MAX_GAME_ANSWERS ="):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
