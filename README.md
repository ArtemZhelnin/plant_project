# Plant Project: Segmentatsiya i Izmereniya Rasteniy

Проект для автоматического анализа изображений рукколы и пшеницы:
- сегментация классов `leaf`, `root`, `stem`;
- расчет длин и площадей в миллиметрах;
- веб-интерфейс с выбором модели (`UNet`/`YOLO`);
- модуль калибровки масштаба (`mm_per_pixel`) по шахматке.

## 1. Что уже реализовано

- Backend на FastAPI: `backend/app`.
- Frontend на React + TypeScript: `frontend/src`.
- Inference-пайплайн и постобработка: `inference/*`.
- Обучение сегментации (бинарное и мультиклассовое): `train/*`.
- Калибровка масштаба по шахматке 5x8 (внутренние углы 4x7): `calibration/*`.
- Переключение модели в UI: `UNet` или `YOLO`.

## 2. Архитектура проекта

```text
plant_project/
├─ backend/
│  ├─ app/
│  │  ├─ main.py          # FastAPI app + CORS + /health
│  │  ├─ routes.py        # POST /api/predict (unet/yolo)
│  │  └─ schemas.py       # Pydantic-схемы ответа
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
│  ├─ model_loader.py     # загрузка SMP-моделей
│  ├─ predict.py          # инференс UNet/FPN/DeepLabV3+
│  ├─ yolo_predict.py     # инференс YOLO-seg
│  ├─ preprocessing.py
│  └─ postprocessing.py   # overlay + метрики + skeleton length
├─ train/
│  ├─ train_max.py        # основной high-quality train (multiclass)
│  ├─ multiclass_dataset.py
│  ├─ multiclass_loss.py
│  ├─ multiclass_metrics.py
│  └─ model.py
├─ calibration/
│  ├─ detect_corners.py
│  ├─ compute_scale.py
│  ├─ stats.py
│  └─ run_calibration.py
├─ training/              # train/valid/test + _annotations.coco.json
├─ weights/               # веса SMP-моделей
└─ weightsYOLO/           # YOLO-веса (best.pt)
```

## 3. Данные и классы

Текущий training pipeline работает с COCO-экспортом в структуре:

```text
training/
├─ train/_annotations.coco.json
├─ valid/_annotations.coco.json
└─ test/_annotations.coco.json
```

Классы в проекте (фиксированный порядок):
- `0`: background
- `1`: leaf
- `2`: root
- `3`: stem

Важно:
- в датасете Roboflow может присутствовать категория `custom` (id=0);
- при обучении используется маппинг по имени категории (`leaf/root/stem`).

## 4. Калибровка масштаба (шахматка)

Для доски `5x8` клеток используются **внутренние углы `4x7`**.

Команда:

```powershell
py -3.11 -m calibration.run_calibration --input_glob "data/calib/calib_*.jpg" --pattern 4x7 --square_mm 10 --out calibration/results.json
```

Алгоритм:
1. Детекция углов `cv2.findChessboardCorners`.
2. Уточнение `cv2.cornerSubPix`.
3. Для каждого фото: расстояния между соседними углами по горизонтали и вертикали.
4. `pixel_mean = mean(distances_px)`.
5. `mm_per_pixel_i = square_mm / pixel_mean`.
6. По всем фото: `mean`, `std`, `relative_std = std / mean * 100%`.
7. Отсев выбросов по правилу `|x - mean| > z * std` (по умолчанию `z=2`).

Критерий качества:
- `< 1%`: ideal
- `1-3%`: normal
- `3-5%`: acceptable
- `> 5%`: problem

Результат сохраняется в `calibration/results.json` и используется в API автоматически.

## 5. Модели сегментации

### 5.1 SMP-модель (кнопка `UNet` в UI)

Технически это не только U-Net: loader читает архитектуру из чекпоинта:
- `unet`
- `fpn`
- `deeplabv3plus`

Текущий основной чекпоинт по умолчанию:
- `weights/segmentation_multiclass_max_gpu/best.pt`

Fallback:
- `weights/segmentation_multiclass_max/best.pt`
- `weights/segmentation/best.pt` (бинарная модель)

### 5.2 YOLO-сегментация (кнопка `YOLO` в UI)

Путь по умолчанию:
- `weightsYOLO/best.pt`

Особенность:
- классы YOLO маппятся по подстрокам в именах (`leaf/root/stem`);
- при перекрытии масок побеждает предсказание с большей `confidence`.

## 6. Математика измерений

Пусть `s = mm_per_pixel`.

### 6.1 Площади

- `leaf_area_mm2 = N_leaf_px * s^2`
- `root_area_mm2 = N_root_px * s^2`
- `stem_area_mm2 = N_stem_px * s^2`

### 6.2 Длины корня и стебля

1. Для класса строится скелет (skeletonize).
2. Длина в пикселях:
   - ортогональные связи: вес `1`;
   - диагональные связи: вес `sqrt(2)`.

Формула:

`length_px = N_orth + N_diag * sqrt(2)`

Далее:

- `root_length_mm = root_length_px * s`
- `stem_length_mm = stem_length_px * s`

## 7. Обучение (high-quality режим)

Основной скрипт: `train/train_max.py`.

Что внутри:
- мультиклассовый COCO dataset;
- аугментации (flip/rotate/brightness/contrast/gamma/blur/noise);
- loss: `0.6 * CrossEntropy + 0.4 * SoftDice`;
- class weights: `1/sqrt(freq)` + downweight background;
- optimizer: `AdamW`;
- scheduler: `OneCycleLR`;
- AMP на GPU;
- early stopping по `val_mIoU_fg`.

Пример запуска на GPU:

```powershell
py -3.11 -m train.train_max --data_root training --output_dir weights/segmentation_multiclass_max_gpu --image_size 768 --epochs 140 --batch_size 2 --architecture deeplabv3plus --encoder resnet50 --tta_val --patience 35 --device cuda
```

Resume:

```powershell
py -3.11 -m train.train_max --data_root training --output_dir weights/segmentation_multiclass_max_gpu --resume weights/segmentation_multiclass_max_gpu/last.pt --device cuda
```

### Текущие зафиксированные метрики (из `weights/segmentation_multiclass_max_gpu/training_summary.json`)

- Best `val_mIoU_fg`: `0.6738` (epoch `88`)
- Test `mIoU_fg`: `0.6212`
- Test `mDice_fg`: `0.7640`
- Test IoU по классам:
  - leaf: `0.6364`
  - root: `0.5842`
  - stem: `0.6430`

## 8. Backend API

Endpoint:
- `POST /api/predict`

Form-data:
- `image`: файл изображения
- `model_type`: `unet` или `yolo` (default: `unet`)

Ответ:

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

Проверка здоровья:
- `GET /health` -> `{"status":"healthy"}`

## 9. Frontend

Frontend умеет:
- загрузка изображения;
- просмотр `Оригинал / Сегментация / Сравнение`;
- zoom/pan;
- легенда классов;
- переключатель модели `UNet / YOLO`;
- экспорт JSON результата.

Ключевой API-клиент: `frontend/src/api/client.ts`.

Переменная окружения:
- `REACT_APP_API_URL` (по умолчанию `http://localhost:8000`).

## 10. Быстрый запуск (Windows PowerShell)

### 10.1 Backend

```powershell
cd C:\CascadeProjects\plant_project\backend
py -3.11 -m pip install -r requirements.txt
py -3.11 -m uvicorn "app.main:app" --host 0.0.0.0 --port 8000 --reload
```

### 10.2 Frontend

```powershell
cd C:\CascadeProjects\plant_project\frontend
npm install
npm start
```

Frontend откроется обычно на `http://localhost:3000`.

## 11. Переменные окружения backend

- `PLANT_MODEL_PATH` — путь к SMP-чекпоинту.
- `PLANT_YOLO_MODEL_PATH` — путь к YOLO-чекпоинту.
- `PLANT_MODEL_DEVICE` — `auto|cpu|cuda`.
- `PLANT_MODEL_THRESHOLD` — порог бинарной модели (для single-class).

## 12. GPU (RTX 3060 Ti и аналогичные)

Если нужен PyTorch с CUDA 12.1:

```powershell
py -3.11 -m pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu121
```

Проверка:

```powershell
py -3.11 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 13. Частые проблемы

### `422 Unprocessable Entity` на `/api/predict`

Причина: не передано поле `image` в `multipart/form-data`.

### `Model file not found`

Проверьте пути:
- `weights/segmentation_multiclass_max_gpu/best.pt`
- `weightsYOLO/best.pt`

или задайте env-переменные `PLANT_MODEL_PATH` / `PLANT_YOLO_MODEL_PATH`.

### На UI нет разделения классов

Скорее всего загружена бинарная модель (`loaded_num_classes=1`).
Нужен мультиклассовый чекпоинт с `class_names = ["background","leaf","root","stem"]`.

## 14. Статус чат-бота

Файл `bot/bot.py` присутствует как заготовка.
Полноценная реализация бота (Telegram/Discord/Web chat) пока не добавлена.

## 15. Ограничения и рекомендации

- Масштаб (`mm_per_pixel`) корректен только при той же камере/высоте/оптике, что и на калибровке.
- Измерения выполнять на исходном разрешении изображения.
- Тонкие корни и тяжелые пересечения классов остаются самой сложной зоной.
- Для роста качества:
  - расширять датасет;
  - чистить и унифицировать полигонные разметки;
  - делать class-balanced sampling и hard-example mining;
  - проверять качество отдельно по Wheat/Arugula.

## 16. Deploy на домен plants1.mooo.com через Docker Compose

Добавлены файлы:
- `docker-compose.yml`
- `docker/Caddyfile`
- `docker/frontend.Dockerfile`
- `docker/backend.Dockerfile`
- `docker/frontend-nginx.conf`
- `.env.example`

### 16.1 Режим с отдельным backend-сервером (ваш кейс)

1. Создайте `.env` из `.env.example`.
2. Укажите:
   - `SITE_DOMAIN=plants1.mooo.com`
   - `BACKEND_UPSTREAM=https://<адрес-вашего-backend>`
   - `PUBLIC_API_URL=/api`
3. Запустите:

```powershell
docker compose up -d --build
```

Что происходит:
- `frontend` отдается как статический сайт;
- `caddy` поднимает HTTPS для `plants1.mooo.com`;
- запросы `https://plants1.mooo.com/api/*` проксируются на `BACKEND_UPSTREAM`.

### 16.2 Полный стек в одном compose (опционально)

Если хотите временно поднять backend рядом:

```powershell
$env:BACKEND_UPSTREAM="http://backend:8000"
docker compose --profile fullstack up -d --build
```

В этом режиме сервис `backend` стартует в контейнере, веса и calibration монтируются из локальных папок:
- `./weights -> /app/weights`
- `./weightsYOLO -> /app/weightsYOLO`
- `./calibration -> /app/calibration`

### 16.3 DNS и порт-форвардинг

Для `plants1.mooo.com` на вашей машине должны быть доступны извне:
- TCP `80`
- TCP `443`

И домен должен указывать на публичный IP сервера с docker.
