# MGC Engineering AI Local v3.6.0 — Release Notes

## Главное изменение

v3.6 добавляет штатный **CPU/GPU Dual Runtime**. Сервис больше не требует NVIDIA GPU для запуска.

## Режимы

- `make up` — автоматический выбор доступного runtime;
- `make cpu` — llama.cpp + локальный GGUF, без GPU;
- `make cpu-vision` — CPU + отдельный multimodal llama.cpp server;
- `make gpu` — прежний vLLM/NVIDIA профиль.

## Что работает на CPU

RAG/Engineering Copilot, локальные embeddings/reranker, Docling/OCR, vector PDF, STEP/STP/DXF/OCCT, КОМПАС/T-FLEX gateway derivatives, Drawing↔3D, geometry similarity, revision comparison, BOM validation, Design Review, engineer-only SSO и Drawing Activity Timeline.

CPU Standard отключает только VLM-анализ изображения. Для него существует отдельный `cpu-vision` профиль, чтобы обычный CPU-сервер не тратил ресурсы на тяжёлую multimodal модель.

## Модельный контур

CPU LLM обслуживается через `llama.cpp` OpenAI-compatible API. Базовый staging-профиль использует Qwen3-4B GGUF Q4_K_M, но конкретный GGUF заменяем и должен пройти корпоративное согласование. Модель и SHA-256 фиксируются в отдельном CPU manifest.

## Hardware-aware запуск

Добавлен `make cpu-check`: перед первым запуском IT получает консервативные рекомендации по threads/context/worker concurrency на основе CPU и RAM. Настройки не переписываются автоматически.

## Air-gap

Добавлены отдельные `bundle-cpu` и `bundle-gpu`. CPU bundle не обязан содержать GPU generative weights.

## Security

CPU model-server не публикует порт на host, отключает WebUI, требует API key, работает read-only/non-privileged и находится только во внутренней Docker-сети. Engineer-only SSO/API authorization не изменены.
