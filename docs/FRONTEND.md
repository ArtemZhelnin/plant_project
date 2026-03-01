# Frontend Documentation – Plant Analysis Web Interface

> **Цель документа** — дать полное понимание устройства фронтенда для бэкенд‑разработчиков и будущих итераторов.  
> **Статус** — UI финализирован, работает с mock‑API, готов к подключению реального бэкенда.

---

## 1️⃣ Технологический стек

| Технология | Версия | Назначение |
|------------|----------|--------------|
| **React** | 18.x | UI‑фреймворк, функциональные компоненты, хуки |
| **TypeScript** | ^5.x | Статическая типизация, строгий код |
| **Vite** | ^5.x | Сборка, dev‑сервер, HMR |
| **Tailwind CSS** | ^3.x | Utility‑first стили, кастомные CSS‑классы |
| **Framer Motion** | ^11.x | Анимации (fade‑in, scale, transitions) |
| **Lucide React** | ^0.400+ | Иконки (Upload, Zoom, Eye, RotateCw, Download) |
| **Axios** | ^1.x | HTTP‑клиент, запросы к бэкенду |
| **React Router v6** | ^6.x | Клиентский роутинг (только `/analysis`) |
| **Zustand** | ^4.x | Лёгкий state‑менеджер (analysisStore) |

---

## 2️⃣ Структура проекта

```
frontend/
├─ public/
│   └─ index.html
├─ src/
│   ├─ api/
│   │   └─ client.ts          # HTTP‑клиент, типы ответа
│   ├─ app/
│   │   ├─ App.tsx            # Корневой компонент + Toaster
│   │   └─ router.tsx         # Роутинг (все пути → /analysis)
│   ├─ components/
│   │   ├─ upload/
│   │   │   └─ UploadZone.tsx   # Drag&Drop, выбор файла
│   │   ├─ viewer/
│   │   │   └─ ImageViewer.tsx # Просмотр изображений, zoom, pan, режимы
│   │   ├─ metrics/
│   │   │   └─ MetricsPanel.tsx # Аналитический блок, моноширинный стиль
│   │   └─ ui/
│   │       └─ Toaster.tsx       # Уведомления (showToast)
│   ├─ pages/
│   │   └─ Analysis.tsx        # Единственная страница приложения
│   ├─ store/
│   │   └─ analysisStore.ts   # Zustand store (текущий анализ)
│   ├─ styles/
│   │   └─ globals.css         # Глобальные стили, CSS‑переменные
│   └─ main.tsx               # Точка входа, рендер App
├─ tailwind.config.js           # Конфиг Tailwind
└─ package.json               # Зависимости, скрипты
```

---

## 3️⃣ Архитектура UI

### 3.1 Единственная страница: `/analysis`

- **Загрузка**: `UploadZone` (drag&drop, кнопка выбора)
- **Результат**:
  1. `ImageViewer` — изображение + оверлей, zoom/pan, переключатель режимов
  2. `MetricsPanel` — моноширинный блок метрик + confidence
  3. Toolbar — кнопки «Новый анализ», zoom, reset

### 3.2 Flow

1. Пользователь открывает `/analysis` → видит `UploadZone`.
2. Загружает изображение → `handleUpload(file)` → `setOriginalImage`.
3. Вызывается `analyzeImage(file)` (API) → `setIsAnalyzing(true)`.
4. После ответа:
   - `setAnalysisData(response)`
   - `setCurrentAnalysis(response)` (store)
   - `setIsAnalyzing(false)`
5. UI показывает `ImageViewer` + `MetricsPanel`.

### 3.3 State‑менеджмент

- **Локальный стейт** (`useState`): `originalImage`, `analysisData`, `isAnalyzing`.
- **Глобальный стейт** (`useAnalysisStore`): `currentAnalysis` (для future‑фич типа History).

---

## 4️⃣ Ключевые компоненты

### 4.1 UploadZone

- **Drag&Drop**: стабилизирован через `dragDepthRef` + `isFileDrag()`.
- **Валидация**: `file.type.startsWith('image/')`.
- **Ограничения**: UI показывает “Максимум: 10MB”, но на фронтенде нет реального лимита — можно добавить `file.size > 10_000_000`.
- **Локализация**: весь текст на русском.

**Параметры**: `onUpload(file: File) => void`.

### 4.2 ImageViewer

- **Режимы**: `'original' | 'overlay'`.
- **Zoom**: колесо мыши + кнопки (0.5x–4x).
- **Pan**: drag с ограничением (`clampOffsetToBounds`) — нельзя увести изображение полностью за границы.
- **Высота**: `640px`.
- **Toolbar**: переключатель режимов, zoom‑кнопки, сброс.
- **События**: `viewer:zoomIn`, `viewer:zoomOut`, `viewer:reset` (window.CustomEvent).

**Параметры**:
```tsx
interface ImageViewerProps {
  originalImage: string;
  overlayImage?: string;
  isAnalyzing?: boolean;
}
```

### 4.3 MetricsPanel

- **Моноширинный стиль**: `font-family: ui-monospace, ...`.
- **Строки**: `label ... value` с точками (`analysis-metrics__dots`).
- **Confidence**: `Достоверность: XX%` + подзаголовок (высокая/средняя/низкая).
- **Skeleton**: во время анализа.

**Параметры**:
```tsx
interface MetricsPanelProps {
  metrics?: Metrics;
  confidence?: number;
  isAnalyzing?: boolean;
}
```

### 4.4 API Client (`client.ts`)

```ts
export interface AnalysisResponse {
  metrics: {
    root_length_mm: number;
    stem_length_mm: number;
    leaf_area_mm2: number;
    root_area_mm2: number;
  };
  overlay: string; // base64 PNG (без data:... префикса)
  confidence: number; // 0–1
}

export const analyzeImage = async (file: File): Promise<AnalysisResponse> => {
  const formData = new FormData();
  formData.append('image', file);
  const response = await apiClient.post('/api/predict', formData);
  return response.data;
};
```

---

## 5️⃣ Стили и визуальная тема

### 5.1 CSS‑переменные (`globals.css`)

```css
:root {
  --bg-primary: #0F1117;
  --bg-secondary: #111420;
  --accent-green: #7FD3B8;
  --accent-blue: #8FA8C7;
  --card-bg: rgba(255, 255, 255, 0.04);
  --text-primary: rgba(255, 255, 255, 0.92);
  --text-secondary: rgba(255, 255, 255, 0.62);
  --border: rgba(255, 255, 255, 0.10);
}
```

### 5.2 Особенности

- **Тёмная “лабораторная” тема**: глубокий фон, тонкая сетка (`body::before`), минимум теней.
- **Glass‑эффект**: `backdrop-filter: blur(10px)`.
- **Моноширинный блок**: `analysis-metrics` с `font-variant-numeric: tabular-nums`.
- **Responsive**: Tailwind utilities, breakpoints `md`, `lg`.
- **Анимации**: Framer Motion (`fade-in`, `scale`, `y` transitions).

---

## 6️⃣ API‑контракт (ожидания от бэкенда)

| Метод | URL | Body | Ответ | Ошибки |
|-------|------|------|----------|
| `POST` | `/api/predict` | `multipart/form-data` с полем `image` (File) | `400` — не изображение / слишком большой / некорректный; `500` — ошибка сервера |
| `GET` | `/health` | — | `200` — `{"status": "healthy"}` |

### Ответ (`AnalysisResponse`)

```json
{
  "metrics": {
    "root_length_mm": 45.2,
    "stem_length_mm": 28.7,
    "leaf_area_mm2": 342.1,
    "root_area_mm2": 125.4
  },
  "overlay": "iVBORw0KGgoAAAANSUhEUgAA...", // base64 PNG, без data:... префикса
  "confidence": 0.94
}
```

**Примечание**: фронт сам добавляет `data:image/png;base64,` перед отображением.

---

## 7️⃣ Локализация (i18n)

- **Текущий подход**: строки на русском прямо в JSX.
- **Будущее**: можно вынести в `src/locales/ru.json` и использовать `react-i18next` или кастомный хук.
- **Ключи**: `Анализ растения`, `Загрузите изображение`, `Длина корня`, `Достоверность`, `Высокая достоверность сегментации` и т.д.

---

## 8️⃣ Сборка и запуск

### 8.1 Dev‑сервер

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 8.2 Production‑сборка

```bash
npm run build
# → build/ (статика)
```

### 8.3 Environment

- `REACT_APP_API_URL` — базовый URL бэкенда (по умолчанию `http://localhost:8000`).

---

## 9️⃣ Советы для бэкенд‑разработчиков

### 9.1 CORS

- **Разрешённые origins**: `http://localhost:3000`, `http://127.0.0.1:3000` (или через env).
- **Headers**: `allow_credentials`, `allow_methods=["*"]`, `allow_headers=["*"]`.

### 9.2 Загрузка файлов

- **Поле**: `image` (FormData).
- **MIME**: `image/*`.
- **Макс. размер**: 10 MB (рекомендуется, UI показывает это).

### 9.3 Base64 overlay

- **Формат**: PNG base64 **без** `data:image/png;base64,`.
- **Почему**: фронт сам подставляет префикс; это позволяет легко менять MIME в будущем.

### 9.4 Ошибки

- **JSON**: `{"detail": "Файл должен быть изображением"}`.
- **Коды**: `400`, `500`.
- **Логи**: желательно с `request_id` для отладки.

### 9.5 Производительность

- **Таймаут**: 30 с на инференс.
- **Асинхронность**: можно сделать очередь (Celery/RQ) и вернуть `analysis_id` + polling.
- **Размеры изображений**: ограничить до 4096×4096 (ресайз на бэкенде).

---

## 10️⃣ Возможные будущие улучшения (Roadmap)

| Фича | Что нужно на бэкенде | Что на фронтенде |
|-------|----------------------|-------------------|
| **История анализов** | `GET /api/analyses`, `DELETE /api/analyses/{id}` | страница `/history` (уже удалена, можно вернуть) |
| **Асинхронная обработка** | очередь, `POST /api/predict` → `{analysis_id}` | polling `/api/analyses/{id}` |
| **Калибровка (мм/пиксель)** | поле `scale` в запросе/ответе | UI‑поле “мм/пиксель” |
| **Многоклассовая сегментация** | `mask_classes` в overlay (PNG с палитрой) | отображение легенды |
| **Экспорт PDF/CSV** | эндпоинт `/api/analyses/{id}/export` | кнопка “Экспорт” |
| **Аутентификация** | JWT/Session | логин/регистрация, личный кабинет |

---

## 11️⃣ Полезные команды

```bash
# Установка зависимостей
npm install

# Dev
npm run dev

# Build
npm run build

# Preview (serve build)
npm install -g serve
serve -s build

# Линтинг/типы (при необходимости)
npm run lint
npm run type-check
```

---

## 12️⃣ Контакты/владельцы

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) — ожидает реальной модели и эндпоинтов выше
- **Repo**: `ArtemZhelnin/plant_project`
- **Ветка**: `main` (актуальная)

---

> **Если нужно что‑то уточнить или добавить — пишите в Issues или напрямую.**
