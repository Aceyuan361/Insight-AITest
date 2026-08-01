

# Insight-AITest

<div align="center">

**Plataforma modular de pruebas y monitoreo impulsada por IA**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)](https://www.typescriptlang.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/Aceyuan361/Insight-AITest/releases)
[![Tests](https://img.shields.io/badge/tests-719%20passed-brightgreen.svg)](#testing)

**[中文文档](./README.zh-CN.md)** | Español

</div>

<p align="center">
  <img src="docs/screenshots/promo-1-en.png" width="100%" alt="Insight-AITest Promo">
</p>

---

## Introducción

Insight-AITest es una **plataforma modular de pruebas y monitoreo impulsada por IA**. La v2.0.0 la transforma de una simple herramienta de rendimiento a una plataforma basada en plugins donde cada capacidad se distribuye como un módulo impulsado por un `manifest.yaml`. El kernel de la plataforma (`platform/`) ensambla la aplicación explorando módulos y registrando rutas; un frontend tipo shell en React (`shell-frontend/`) renderiza la interfaz de usuario de cada módulo a partir del mismo manifiesto.

> **La v2.0.0 incluye seis módulos principales (A–F) más un módulo de base de conocimientos, todos completos:**
>
> | # | Módulo | Ruta | Propósito |
> |---|--------|-------|---------|
> | A | **Shell de Plataforma** | — | Kernel + sistema de módulos + shell frontend compartido |
> | B | **Rendimiento** | `/performance` | Monitoreo en tiempo real de rendimiento de dispositivos móviles (Android/iOS) |
> | C | **Asistente de IA** | `/ai` | Chat RAG sobre una base de conocimientos local |
> | D | **Generación de Casos de Prueba** | `/testcase` | Generación de casos de prueba impulsada por IA (analizar → seleccionar → generar → revisar) |
> | E | **Automatización de API** | `/api-runner` | Ejecución de casos de prueba de API (multietapa + aserciones + encadenamiento de variables) |
> | F | **Automatización de IU** | `/ui-runner` | Automatización de navegador impulsada por visión con Midscene |
> | — | **Base de Conocimientos** | `/kb` | Base de conocimientos del proyecto (carga de documentos, indexación RAG para C/D) |

### Características clave

- **Módulos enchufables**: cada capacidad es un módulo independiente — agrega uno con un `manifest.yaml`.
- **Monitoreo de rendimiento**: CPU / memoria / FPS / red / batería en tiempo real para Android (y CPU/memoria/red/batería para iOS — ver tabla de métricas) a través de WebSocket.
- **Asistente de IA**: chat fundamentado en tus propios documentos (embeddings locales + almacén vectorial, RAG).
- **Generación de casos de prueba**: la IA analiza escenarios y propone casos de prueba estructurados para revisión.
- **Automatización de API**: casos HTTP multietapa con aserciones, encadenamiento de variables (`{{var}}`) e historial.
- **Automatización de IU**: Midscene (LLM de visión) controla un navegador real — `aiAction` / `aiAssert` / `aiQuery` — con capturas de pantalla por paso.

### ¿Por qué Insight-AITest?

La mayoría de las herramientas de pruebas resuelven **un** problema a la vez. Insight-AITest es la única plataforma de código abierto que fusiona **monitoreo de rendimiento, agentes de IA, generación de pruebas y automatización de API/IU en un solo producto cohesivo** — para que tus datos, casos y resultados vivan en un solo lugar en lugar de estar dispersos entre Postman + JMeter + Selenium + un wiki.

| Capacidad | Insight-AITest | Postman | MeterSphere | Katalon | Selenium/Playwright |
|---|:---:|:---:|:---:|:---:|:---:|
| 🤖 Agente de IA (entiende documentos, planifica, ejecuta) | ✅ | ❌ | ❌ | ⚠️ Limitado | ❌ |
| 📊 Monitoreo de rendimiento móvil (Android/iOS) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 📝 Generación de casos de prueba con IA | ✅ | ❌ | ❌ | ⚠️ Limitado | ❌ |
| 🔗 Automatización de API (pasos + aserciones + suites) | ✅ | ✅ | ✅ | ✅ | ❌ |
| 🖥️ Automatización de IU impulsada por visión (sin selectores) | ✅ | ❌ | ❌ | ❌ | ⚠️ Solo código |
| 📚 Base de conocimientos RAG local (tus documentos) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 🔒 Los datos se quedan locales (sin bloqueo en la nube) | ✅ | ❌ | ⚠️ | ❌ | ✅ |
| 🧩 Arquitectura de módulos con plugins | ✅ | — | ⚠️ | ❌ | — |
| 💰 Costo | 🟢 Gratis / MIT | 🟡 Freemium | 🟢 Gratis | 🔴 De pago | 🟢 Gratis |

### 💎 Ventajas principales

| Forma tradicional | Insight-AITest | ¿Por qué importa? |
|---|---|---|
| Escribir scripts de API/IU a mano | Describe qué probar en lenguaje natural; el Agente planifica y ejecuta | Horas → minutos; sobrevive a cambios de IU/API sin reescribir scripts |
| Rendimiento = herramienta separada, informes a posteriori | Flujo WebSocket en tiempo real, en el momento en que inicias | Detecta regresiones en vivo, no después de la ejecución |
| Conocimiento disperso en wikis/documentos | Sube documentos → índice vectorial local → el Agente responde fundamentado en *tu* producto | La IA realmente "lee" tus documentos; las respuestas son trazables, no alucinadas |
| Seleccionar selector / XPath a mano | El LLM de visión encuentra el elemento desde una captura + descripción | Sin más pruebas rotas cuando la página se re-renderiza |
| Cambiar entre 4–5 herramientas | Una plataforma, un modelo de datos, extensible con plugins | Flujo de casos: generados → ejecutados como API → ejecutados como IU, todo en un solo lugar |

### Métricas de rendimiento admitidas

| Métricas | Android | iOS |
|---------|---------|-----|
| Uso de CPU | ✅ App/Sistema | ✅ App |
| Memoria | ✅ PSS/Native/Dalvik | ✅ physFootprint |
| Tasa de cuadros | ✅ FPS+detección de Jank | ⚠️ Marcador (iOS no expone FPS real de la app) |
| Red | ✅ Tráfico de subida/bajada | ✅ Tráfico del sistema |
| Batería | ✅ Nivel/Temp | ✅ Nivel/Temp |
| GPU | ✅ Soporte parcial | ❌ No soportado |
| Energía | ✅ GPU | ✅ CPU/GPU/Red |

### Capturas de pantalla

<p align="center">
  <img src="docs/screenshots/promo-2-en.png" width="100%" alt="Insight-AITest Capabilities">
</p>

<p align="center">
  <img src="docs/screenshots/home.png" width="80%" alt="Home"><br>
  <sub>Inicio / Panel de control</sub>
</p>

<table>
  <tr>
    <td width="50%" align="center"><img src="docs/screenshots/test-agent.png" alt="Test Agent"><br><sub>Agente de Pruebas (C)</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/knowledge-base.png" alt="Knowledge Base"><br><sub>Base de Conocimientos</sub></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="docs/screenshots/testcase-generation.png" alt="Test Case Generation"><br><sub>Generación de Casos de Prueba (D)</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/api-automation.png" alt="API Automation"><br><sub>Automatización de API (E)</sub></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="docs/screenshots/ui-automation.png" alt="UI Automation"><br><sub>Automatización de IU (F)</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/performance-monitoring.png" alt="Performance Monitoring"><br><sub>Monitoreo de Rendimiento (B)</sub></td>
  </tr>
</table>

---

## Inicio rápido

### Requisitos

- **Python**: 3.10+
- **Node.js**: 16+ y npm ⚠️ **Requerido** - Instalar desde [nodejs.org](https://nodejs.org/)
- **ADB** (Android Debug Bridge) - para dispositivos Android
- **pymobiledevice3** >= 7.0.0 - para dispositivos iOS (opcional)
- **Playwright Chromium** - para Automatización de IU (F): `playwright install chromium`

### Inicio con un clic (Windows) ✨

Para usuarios de Windows, simplemente **haz doble clic en `start.bat`** después de clonar. Detecta automáticamente Python/Node, instala las dependencias de Python en la primera ejecución y luego inicia la plataforma (backend + frontend + abre el navegador automáticamente). Las ejecuciones posteriores omiten el paso de instalación para un reinicio rápido.

### Instalación manual

```bash
# 1. Clonar el repositorio
git clone https://github.com/Aceyuan361/Insight-AITest.git
cd Insight-AITest

# 2. Instalar dependencias de Python
pip install -r requirements.txt

# 3. (Solo Automatización de IU) instalar el controlador del navegador
playwright install chromium

# 4. Iniciar la plataforma (inicia backend + servidor dev frontend, abre el navegador)
python -m insight_aitest

# Los servicios inician automáticamente:
# - API Backend:  http://localhost:8001
# - Frontend:     http://localhost:80
# - Documentación API:     http://localhost:8001/docs
```

> **Nota**: `python -m insight_aitest` inicia el backend FastAPI (puerto 8001), el servidor de desarrollo del frontend React (puerto 80) y abre un navegador. Si falta `node_modules`, ejecuta `npm install` primero.

### Configuración del LLM (módulos C / D / F)

Los módulos de IA leen las credenciales del LLM desde variables de entorno. Configura al menos el modelo de chat para C/D; la Automatización de IU (F) admite además un modelo de visión dedicado:

```bash
# Chat / razonamiento (módulos C, D)
export INSIGHT_EYE_AI_LLM_BASE_URL=https://api.example.com/v1
export INSIGHT_EYE_AI_LLM_API_KEY=sk-...
export INSIGHT_EYE_AI_CHAT_MODEL=gpt-4o-mini

# Visión (módulo F) — opcional; vuelve al modelo de chat si no se establece
export INSIGHT_EYE_AI_VISION_MODEL=gpt-4o
```

Consulta [`docs/`](./docs/) para la lista completa de variables (embeddings, ajuste de recuperación, tiempos de espera, etc.).

### Acceso de red

Por defecto, la aplicación se vincula a todas las interfaces de red (`0.0.0.0`), permitiendo el acceso desde otros dispositivos en la misma red.

1. Encuentra la dirección IP de tu computadora (`ipconfig` en Windows, `ifconfig`/`ip addr` en Linux/Mac).
2. Accede mediante `http://<tu-ip>:80` (frontend) o `http://<tu-ip>:8001` (backend/documentación API).

---

## Estructura del proyecto

```
Insight-AITest/
├── insight_aitest/
│   ├── __main__.py               # Punto de entrada: python -m insight_aitest
│   ├── platform/                 # Kernel de la plataforma + servicios compartidos (A)
│   │   ├── kernel.py             # Ensamblaje FastAPI (explorar módulos → registrar rutas)
│   │   ├── module_registry.py    # Exploración/validación/orden-topológico de manifiestos
│   │   ├── persistence/          # DatabaseManager (capa de DB compartida)
│   │   ├── services/             # Gestor de dispositivos, colectores (adb/android/ios), llm/
│   │   └── api/platform.py       # /api/platform/* (lista de módulos, estado)
│   ├── modules/                  # Módulos enchufables (cada uno tiene manifest.yaml)
│   │   ├── _registry/            # Contrato de módulo (esquema de manifiesto, clase base)
│   │   ├── performance/          # (B) Monitoreo de rendimiento en tiempo real
│   │   ├── ai/                   # (C) Asistente de base de conocimientos RAG
│   │   ├── testcase/             # (D) Generación de casos de prueba con IA
│   │   ├── api/                  # (E) Automatización de API
│   │   ├── ui/                   # (F) Automatización de IU (Midscene + Playwright)
│   │   └── example/              # Módulo marcador (verifica el sistema de módulos)
│   └── shell-frontend/           # Shell de plataforma en React
│       └── src/
│           ├── shell/            # AppShell, TopBar, SideNav, Dashboard, tema
│           ├── modules/          # Frontends por módulo (performance/ai/testcase/api/ui/)
│           ├── shared/           # cliente api, tipos, config, i18n
│           ├── module-map.ts     # Mapeo estático de entrada de módulo → componente
│           └── routing.tsx       # Ensamblaje de react-router impulsado por manifiesto
├── tests/                        # Suite pytest (719 aprobados, 1 omitido)
├── docs/                         # Documentación + especificaciones + notas de entrega
├── README.md / README.zh-CN.md
├── ROADMAP.md                    # Hoja de ruta y estado de los subsistemas A–F
├── pyproject.toml                # Configuración del paquete (v2.0.0)
└── requirements.txt              # Dependencias de Python
```

---

## Guía de módulos

### B — Monitoreo de rendimiento (`/performance`)

Métricas del dispositivo en tiempo real a través de WebSocket. Conecta un dispositivo Android (depuración USB) o iOS (confianza + Modo de desarrollador), selecciona una app (Android) o ID de paquete (iOS) y comienza el monitoreo. Configura umbrales de alerta (CPU / memoria / FPS / temp. batería) en el panel de configuración.

### C — Asistente de IA (`/ai`)

Sube documentos para construir una base de conocimientos local (embeddings almacenados localmente) y luego chatea con respuestas fundamentadas en tu contenido mediante RAG.

### D — Generación de casos de prueba (`/testcase`)

La IA analiza un escenario, selecciona puntos de prueba y genera casos de prueba estructurados que puedes revisar y editar antes de que sean consumidos por E o F.

### E — Automatización de API (`/api-runner`)

Compon casos HTTP multietapa con aserciones y encadenamiento de `{{variable}}` entre pasos. Ejecuta contra entornos (`base_url` configurable), navega por historial y estadísticas, y visualiza solicitudes/respuestas por paso.

### F — Automatización de IU (`/ui-runner`)

Escribe casos como pasos; el ejecutor normaliza cada paso y controla un navegador real con los métodos de visión de **Midscene**:

- `action` → `aiAction` (ejecutar)
- `assert` → `aiAssert` (verificar)
- `extract` → `aiQuery` (leer datos, encadenar vía `{{var}}`)

Cada paso registra una captura de pantalla (guardada en disco, no en la DB) y un registro de acciones; un `error` en un paso no aborta los pasos posteriores (similar a E). `base_url` puede sobrescribirse por ejecución.

> **Nota**: La Automatización de IU funciona sin conexión en cuanto a pruebas unitarias se refiere (el ejecutor acepta un `agent_factory` inyectable). Para una ejecución real de navegador **end-to-end**, debes configurar `INSIGHT_EYE_AI_VISION_MODEL` (o `CHAT_MODEL`) + una clave API válida y ejecutar `playwright install chromium`.

---

## Stack tecnológico

### Backend

- **FastAPI** + **uvicorn** — framework web / servidor ASGI
- **WebSocket** — transmisión de rendimiento en tiempo real
- **SQLAlchemy** + **SQLite** — bases de datos por módulo (modo WAL)
- **ADB** — comunicación con dispositivos Android
- **pymobiledevice3** — comunicación con dispositivos iOS
- **Playwright** + **PyMidscene** — automatización de navegador impulsada por visión (F)
- **jsonpath-ng** — aserciones de respuestas de API (E)

### Frontend

- **React 18** + **TypeScript** + **Vite**
- **react-router-dom** — enrutamiento impulsado por manifiestos de módulos
- **Zustand** — almacenes de estado por módulo
- **ECharts** — visualización de datos
- **TailwindCSS** — estilo (tema ciberpunk neón oscuro)
- **i18next** — internacionalización (zh / en)

---

## Documentación de la API

Después de iniciar el backend, visita `http://localhost:8001/docs` para la interfaz Swagger completa. Mapa de endpoints a alto nivel:

### Plataforma

| Endpoint | Método | Descripción |
|------|------|------|
| `/api/platform/modules` | GET | Lista de módulos montados (id, orden, ruta) |
| `/api/platform/health` | GET | Verificación de estado |

### Endpoints de módulos

| Módulo | Ruta base | Destacados |
|--------|-----------|-----------|
| Rendimiento (B) | `/api/devices`, `/api/monitoring/*`, `/ws/monitoring/{id}` | dispositivos, apps, iniciar/detener, flujo WS en vivo |
| Asistente IA (C) | `/api/modules/ai/...` | carga de base de conocimientos, chat |
| Casos de prueba (D) | `/api/modules/testcase/...` | generar, listar, editar (PUT) |
| Automatización API (E) | `/api/modules/api/runs/...` | ejecutar, historial, detalle, estadísticas, suites, entornos |
| Automatización IU (F) | `/api/modules/ui/runs/...` | ejecutar, historial, detalle, captura, estadísticas, eliminar |

---

## Pruebas

```bash
# Suite completa de Python
python -m pytest tests/ -q        # → 719 aprobados, 1 omitido

# Por subsistema
python -m pytest tests/ui/ -q     # Automatización de IU (F): 30 pruebas
python -m pytest tests/api/ -q    # Automatización de API (E)
# ... rendimiento / ia / testcase / plataforma

# Verificación de tipos + compilación del frontend
cd insight_aitest/shell-frontend
npm run build                     # tsc -b && vite build

# E2E del frontend (Playwright)
npm run test:e2e
```

> El ejecutor de cada módulo está probado unitariamente con falsos inyectables (no se requiere navegador real / LLM / dispositivo), por lo que la suite se ejecuta completamente sin conexión.

---

## Preguntas frecuentes

### P: ¿El dispositivo iOS no se conecta?
Asegúrate de que el dispositivo confíe en la computadora, que el Modo de desarrollador esté habilitado, que uses `pymobiledevice3 >= 7.0.0` y que iOS sea 11.0 – 16.x (iOS 17+ no es compatible).

### P: ¿El dispositivo Android no se detecta?
Asegúrate de que ADB esté instalado, que la depuración USB esté habilitada y que la computadora esté autorizada para depurar.

### P: ¿La Automatización de IU no hace nada / genera errores?
La Automatización de IU (F) necesita un LLM con capacidad de visión. Configura `INSIGHT_EYE_AI_VISION_MODEL` (o vuelve a `INSIGHT_EYE_AI_CHAT_MODEL`) junto con una `INSIGHT_EYE_AI_LLM_API_KEY` válida, y ejecuta `playwright install chromium` una vez. Las pruebas unitarias cubren la lógica del ejecutor sin conexión; una ejecución real de navegador requiere esto.

### P: ¿Por qué iOS no admite el monitoreo de GPU?
Las restricciones de la API del sistema iOS impiden que las aplicaciones de terceros accedan a los datos de uso de GPU.

---

## Contribuir

¡Los Issues y Pull Requests son bienvenidos!

1. Haz un fork del repositorio
2. Crea tu rama de funcionalidad (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Agregar alguna AmazingFeature'`)
4. Haz push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## Licencia

Este proyecto está licenciado bajo la [Licencia MIT](LICENSE).

---

## Agradecimientos

Este proyecto no sería posible sin la inspiración y el apoyo de estos excelentes proyectos de código abierto:

- **[solox](https://github.com/smart-test-ti/SoloX)** - Herramienta de pruebas automatizadas de rendimiento móvil, proporcionó conceptos centrales para el monitoreo de rendimiento de dispositivos móviles
- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - Biblioteca de comunicación con dispositivos iOS, haciendo posible el monitoreo de iOS
- **[py-ios-device](https://github.com/YueChen-C/py-ios-device)** - Soporte subyacente para la gestión y comunicación de dispositivos iOS
- **[Midscene.js](https://midscenejs.com/)** - Automatización de IU impulsada por visión, potencia el módulo de Automatización de IU

---

## Contacto

- **Autor**: Aceyuan361
- **Issues**: [GitHub Issues](https://github.com/Aceyuan361/Insight-AITest/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/Aceyuan361/Insight-AITest/discussions)

---

<div align="center">

Si este proyecto te ayuda, ¡por favor dale una ⭐️ Estrella!

</div>
