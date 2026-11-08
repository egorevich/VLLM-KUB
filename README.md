# Инференс LLM на CPU с использованием vLLM и Kubernetes

Проект разворачивает сервис инференса языковой модели с помощью vLLM в локальном Kubernetes-кластере. Дополнительно реализован Benchmark API для измерения производительности генерации.

## Требования

Для запуска необходимы:

- Docker Desktop с включённым Kubernetes;
- Docker Buildx;
- kubectl;
- OpenSSL;
- токен доступа Hugging Face.

Решение настроено для Docker Desktop Kubernetes.

## Запуск

1. Запустить Docker Desktop и включить Kubernetes.

2. Запустить скрипт развёртывания:

   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

Скрипт автоматически:

- собирает Docker-образы vLLM и Benchmark API;
- загружает образы в Kubernetes;
- создаёт Namespace;
- создаёт Kubernetes Secret, если он ещё не существует;
- применяет ConfigMap, PVC, Services и Deployments;
- ожидает готовности приложений.

При первом запуске потребуется ввести токен Hugging Face. API Bearer token генерируется автоматически и сохраняется в Kubernetes Secret.

## Модель и хранение данных

Используемая модель: `Qwen/Qwen2.5-0.5B-Instruct`.

Инференс выполняется исключительно на CPU.

Для хранения весов модели используется PersistentVolumeClaim (PVC), подключённый к `/models/huggingface`. Это позволяет сохранять загруженные файлы между перезапусками Pod.

## Benchmark API

Для доступа к Benchmark API выполнить:

```bash
kubectl port-forward service/benchmark-service 8002:8001 -n vllm-project
```

Документация API доступна по адресу:

http://localhost:8002/docs

Пример запроса из другого терминала:

```bash
curl -X POST http://localhost:8002/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "prompt": "Объясни что такое Kubernetes кратко.",
    "max_tokens": 40
  }'
```

API возвращает количество входных и выходных токенов, TTFT, ITL, скорость генерации и общее время выполнения запроса.

## Безопасность и логирование

- Контейнеры запускаются от непривилегированного пользователя (UID 10001).
- Логирование запросов vLLM отключено.
- Используется собственная конфигурация логирования.
- Тексты пользовательских запросов и ответы модели не записываются в прикладные логи.
- Токены передаются через Kubernetes Secret.
- Веса модели хранятся в PersistentVolumeClaim.

## Удаление ресурсов

Для удаления всех ресурсов проекта:

```bash
kubectl delete namespace vllm-project
```