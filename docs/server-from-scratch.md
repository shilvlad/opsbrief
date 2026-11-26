# OpsBrief: подготовка VPS с нуля

Первый этап автоматизации — **безопасный Bootstrap** для выделенной Ubuntu 24.04.
Подготовлены две команды: проверка сервера без изменений и установка базовых компонентов.
Production-деплой, nginx, TLS, firewall, бэкапы и CD будут добавлены отдельными PR.

## Что важно

- Целевой тестовый домен: `opsbrief.chat.su`. Имя нужно проверить по DNS **до** выпуска TLS.
- Рабочий `opsbrief.iteko.su` не изменять.
- Приватные ключи и секреты **не** передавать через GitHub Actions, командную строку или репозиторий.
- Bootstrap не меняет конфигурацию SSH, не отключает парольный вход и не включает firewall.
- Существующие `/opt/opsbrief`, nginx, Docker и занятые порты сначала проверить.
- Группа `docker` предоставляет права уровня root. Пользователю `deploy` выдавать ключ только доверенного администратора.

## Подготовка управляющей машины (Mac)

Нужен Ansible и SSH-доступ к чистому VPS. Пример:

```bash
python3 -m pip install ansible
ansible-galaxy collection install -r infra/ansible/requirements.yml
```

Создать **локальный**, не коммитящийся в Git файл `/tmp/opsbrief-inventory.ini`:

```ini
[opsbrief]
TARGET_IP ansible_user=root ansible_ssh_private_key_file=~/.ssh/opsbrief_ed25519
```

Подставить реальный IP тестового VPS. Убедиться, что домен указывает на этот IP.
Прежде чем запускать Bootstrap, выполнить read-only проверку:

```bash
ansible-playbook -i /tmp/opsbrief-inventory.ini infra/ansible/preflight.yml
```

Если preflight подтвердил, что целевой сервер правильный, подготовить локальный файл переменных
`/tmp/opsbrief-bootstrap-vars.yml` (не коммитить):

```yaml
opsbrief_deploy_public_key: "ssh-ed25519 AAAA... opsbrief-vps"
```

Здесь **только публичный** ключ из `~/.ssh/opsbrief_ed25519.pub`.

Сначала dry-run, затем Bootstrap:

```bash
ansible-playbook -i /tmp/opsbrief-inventory.ini \
  -e @/tmp/opsbrief-bootstrap-vars.yml \
  infra/ansible/bootstrap.yml --check --diff

ansible-playbook -i /tmp/opsbrief-inventory.ini \
  -e @/tmp/opsbrief-bootstrap-vars.yml \
  infra/ansible/bootstrap.yml
```

Проверить отдельный вход `deploy` и Docker Compose. Повторный запуск Bootstrap должен
не менять состояние, кроме возможных штатных обновлений индекса apt.

## Границы первого PR

Этот Bootstrap **не запускает OpsBrief** и не считается законченным развёртыванием.
В следующих этапах: production Compose с зафиксированным образом GHCR, безопасная
поставка секретов, Nginx и Let's Encrypt, бэкапы SQLite, CI/CD и smoke/e2e проверки.

**Не запускать автоматически Bootstrap на существующем рабочем сервере:** у скрипта
пока нет проверки совместимости всех установленных сервисов.
