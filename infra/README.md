# Local Infra

Compose file in this folder starts Pixel SC custom services:

- `integration-service` on `8090`
- `pixel-backend` on `8000`
- `bot`

Run:

```bash
docker compose -f infra/docker-compose.local.yml up -d --build
```
