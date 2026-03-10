# Plant Analysis Platform

Платформа для сегментации растений (руккола/пшеница) и морфометрических измерений:
- сегментация классов `leaf`, `root`, `stem`;
- вычисление длин и площадей в физических единицах;
- веб-интерфейс с выбором модели (`UNet`/`YOLO`);
- калибровка масштаба по шахматной доске.

## 1. Структура проекта

```text
plant_project/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ routes.py
│  │  └─ schemas.py
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ pages/Analysis.tsx
│  │  ├─ components/viewer/ImageViewer.tsx
│  │  ├─ components/metrics/MetricsPanel.tsx
│  │  ├─ components/upload/UploadZone.tsx
│  │  ├─ api/client.ts
│  │  └─ styles/globals.css
│  └─ package.json
├─ inference/
│  ├─ model_loader.py
│  ├─ predict.py
│  ├─ yolo_predict.py
│  ├─ preprocessing.py
│  └─ postprocessing.py
├─ train/
│  ├─ train_max.py
│  ├─ multiclass_dataset.py
│  ├─ multiclass_loss.py
│  ├─ multiclass_metrics.py
│  └─ model.py
├─ calibration/
│  ├─ detect_corners.py
│  ├─ compute_scale.py
│  ├─ stats.py
│  ├─ run_calibration.py
│  └─ results.json
├─ training/
│  ├─ train/_annotations.coco.json
│  ├─ valid/_annotations.coco.json
│  └─ test/_annotations.coco.json
├─ weights/
├─ weightsYOLO/
├─ docker-compose.yml
└─ docker/
```

## 2. Данные и классы

Формат разметки: COCO polygons.

Целевые классы:
- `0` — background
- `1` — leaf
- `2` — root
- `3` — stem

В обучающем пайплайне используется маппинг по именам категорий (`leaf`, `root`, `stem`) в `train/multiclass_dataset.py`.

## 3. Калибровка масштаба

Для шахматки `5x8` клеток применяются внутренние углы `4x7`.

Команда:

```powershell
py -3.11 -m calibration.run_calibration --input_glob "data/calib/calib_*.jpg" --pattern 4x7 --square_mm 10 --out calibration/results.json
```

Алгоритм:
1. Поиск углов: `cv2.findChessboardCorners`.
2. Уточнение углов: `cv2.cornerSubPix`.
3. Расчет расстояний между соседними углами (горизонт/вертикаль).
4. Для изображения: `mm_per_pixel_i = square_mm / mean(distance_px)`.
5. Статистика по набору изображений: `mean`, `std`, `relative_std`.
6. Отсев выбросов по правилу `|x - mean| > z * std`.

Итог сохраняется в `calibration/results.json` и используется backend при расчете метрик.

## 4. Модели сегментации

### 4.1 SMP (UI: `UNet`)

Фактическая архитектура определяется чекпоинтом:
- `unet`
- `fpn`
- `deeplabv3plus`

Порядок загрузки по умолчанию:
1. `weights/segmentation_multiclass_max_gpu/best.pt`
2. `weights/segmentation_multiclass_max/best.pt`
3. `weights/segmentation/best.pt`

### 4.2 YOLO Segmentation (UI: `YOLO`)

Путь по умолчанию:
- `weightsYOLO/best.pt`

Логика сопоставления классов реализована в `inference/yolo_predict.py`.

## 5. Математика измерений

Обозначение: `s = mm_per_pixel`.

Площади:
- `leaf_area_mm2 = N_leaf_px * s^2`
- `root_area_mm2 = N_root_px * s^2`
- `stem_area_mm2 = N_stem_px * s^2`

Длины корня и стебля:
1. Скелетизация бинарной маски класса.
2. Расчет длины:
   - ортогональные связи: вес `1`;
   - диагональные связи: вес `sqrt(2)`.

Формула:

`length_px = N_orth + N_diag * sqrt(2)`

Перевод в миллиметры:
- `root_length_mm = root_length_px * s`
- `stem_length_mm = stem_length_px * s`

## 6. Обучение (multiclass)

Основной скрипт: `train/train_max.py`.

Текущая конфигурация:
- loss: `CrossEntropy + SoftDice`;
- optimizer: `AdamW`;
- scheduler: `OneCycleLR`;
- AMP на CUDA;
- early stopping по `val_mIoU_fg`;
- метрики по классам: IoU и Dice.

Пример запуска:

```powershell
py -3.11 -m train.train_max --data_root training --output_dir weights/segmentation_multiclass_max_gpu --image_size 768 --epochs 140 --batch_size 2 --architecture deeplabv3plus --encoder resnet50 --tta_val --patience 35 --device cuda
```

Возобновление:

```powershell
py -3.11 -m train.train_max --data_root training --output_dir weights/segmentation_multiclass_max_gpu --resume weights/segmentation_multiclass_max_gpu/last.pt --device cuda
```

## 7. API

### 7.1 Endpoint

- `POST /api/predict`

`multipart/form-data`:
- `image` — входное изображение;
- `model_type` — `unet` или `yolo` (по умолчанию `unet`).

### 7.2 Ответ

```json
{
  "metrics": {
    "root_length_mm": 78.4,
    "stem_length_mm": 58.7,
    "leaf_area_mm2": 837.8,
    "root_area_mm2": 0.0,
    "stem_area_mm2": 0.0
  },
  "overlay": "data:image/png;base64,...",
  "confidence": 0.99,
  "loaded_num_classes": 4,
  "class_names": ["background", "leaf", "root", "stem"],
  "loaded_model_type": "unet"
}
```

### 7.3 Healthcheck

- `GET /health` -> `{"status":"healthy"}`

## 8. Локальный запуск

### 8.1 Backend

```powershell
cd ...\plant_project\backend
py -3.11 -m pip install -r requirements.txt
py -3.11 -m uvicorn "app.main:app" --host 0.0.0.0 --port 8000 --reload
```

### 8.2 Frontend

```powershell
cd ...\plant_project\frontend
npm install
npm start
```

## 9. Переменные окружения backend

- `PLANT_MODEL_PATH`
- `PLANT_YOLO_MODEL_PATH`
- `PLANT_MODEL_DEVICE` (`auto|cpu|cuda`)
- `PLANT_MODEL_THRESHOLD`

## 10. Docker Compose и домен plants1.mooo.com

Файлы деплоя:
- `docker-compose.yml`
- `docker/Caddyfile`
- `docker/frontend.Dockerfile`
- `docker/backend.Dockerfile`
- `docker/frontend-nginx.conf`
- `.env.example`

### 10.1 Вариант: frontend на домене, backend отдельно

1. Создается `.env` на основе `.env.example`.
2. Указываются параметры:
   - `SITE_DOMAIN=plants1.mooo.com`
   - `BACKEND_UPSTREAM=https://api.plants1.mooo.com` (или другой backend URL)
   - `PUBLIC_API_URL=/api`
3. Выполняется запуск:

```powershell
docker compose up -d --build
```

Маршрутизация:
- `https://plants1.mooo.com` -> frontend;
- `https://plants1.mooo.com/api/*` -> `BACKEND_UPSTREAM`.

### 10.2 Вариант: полный стек в одном compose

```powershell
$env:BACKEND_UPSTREAM="http://backend:8000"
docker compose --profile fullstack up -d --build
```

В этом режиме backend поднимается как отдельный сервис `backend` внутри compose.

### 10.3 Сетевые требования

- Домен `plants1.mooo.com` должен указывать на публичный IP сервера.
- На сервере должны быть доступны входящие TCP-порты `80` и `443`.

## 11. Обученная модель в репозитории

Финальный чекпоинт:
- `weights/segmentation_multiclass_max_gpu/best.pt`

Файл хранится через Git LFS. После `clone` требуется:

```powershell
git lfs pull
```

## 12. Типовые проблемы

### 12.1 `422 Unprocessable Entity` на `/api/predict`

Причина: отсутствует поле `image` в `multipart/form-data`.

### 12.2 `Model file not found`

Проверяются пути:
- `weights/segmentation_multiclass_max_gpu/best.pt`
- `weightsYOLO/best.pt`

При необходимости задаются переменные `PLANT_MODEL_PATH` и `PLANT_YOLO_MODEL_PATH`.

### 12.3 Нет разделения классов в UI

Загружена бинарная модель (`loaded_num_classes=1`).
Для мультиклассовой сегментации требуется checkpoint с `class_names = ["background","leaf","root","stem"]`.

## 13. Ограничения

- Масштаб `mm_per_pixel` валиден только для условий съемки, соответствующих калибровке.
- Метрики чувствительны к качеству масок на тонких корнях и в зонах пересечения классов.
- Для роста качества сегментации требуется расширение и выравнивание датасета по классам.
