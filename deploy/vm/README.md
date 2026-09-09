# VM Deployment Kit

Основная инструкция для IT: [`../../VM_IT_DIRECTOR.md`](../../VM_IT_DIRECTOR.md).

Быстрый запуск после установки Docker/Git/curl/OpenSSL:

```bash
MGC_VM_HOST=<VM_IP_OR_DNS> bash deploy/vm/install_vm.sh
```

Команды эксплуатации:

```bash
bash deploy/vm/check_vm.sh
bash deploy/vm/backup_vm.sh
bash deploy/vm/update_vm.sh
bash deploy/vm/start_vm.sh
bash deploy/vm/stop_vm.sh
```

Runtime secrets, TLS keys и initial admin credentials находятся в `deploy/vm/runtime/` и не должны попадать в Git.
