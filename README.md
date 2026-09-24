# ⚡ EvoFlash

Sistema de **aprendizaje evolutivo** que convierte tus apuntes de Obsidian en flashcards inteligentes evaluadas por **Google Gemini**.

Piensa en Anki, pero con un **Game Master de IA** que califica tus respuestas con argumentación (no solo definiciones), evoluciona las preguntas según tu nivel (N1→N4), detecta cuál áreas te cuestan más y genera **Boss Battles** (escenarios tipo troubleshooting) cuando ya dominas un tema.

---

## 🏗️ Arquitectura

| Módulo | Qué hace |
|--------|----------|
| `vault_manager/` | Lee/escribe tus `.md` Obsidian con frontmatter YAML (nivel, estado, próximo repaso). Sin romper tu vault. |
| `core_engine/` | La lógica pura: Flashcard, SM-2 (espaciado), Evolución de preguntas. |
| `llm_interface/` | Comunicación con `google-genai`. Tiene **fallback automático** entre modelos si uno está saturado. |
| `ingestion/` | Lee tus apuntes reales en Obsidian y genera nuevas flashcards (auto-contenidas, sin "según el apunte"). |
| `ui_cli/` | Interfaz de línea de comandos (Rich). Para juegos por CMD. |
| `web_dashboard/` | **Interfaz web PWA-ready**: menú, juegos interactivos, Skill Tree D3, stats y gestión de exámenes. |
| `ui_cli/` & `web_dashboard/` | No se mezclan. Cada uno habla con su propio backend. |

## ⚙️ Setup (1 minuto)

1. Clona o descarga el repo
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Copia `.env.example` → `.env` y edítalo:
   ```
   GEMINI_API_KEY=TU_KEY_AQUÍ
   LLM_MODEL=gemini-3.1-flash-lite
   VAULT_PATH=C:/Users/Quest/Documents/Obsidian Vault
   EVOFLASH_FOLDER=Questions
   ```
4. Seco todo:
   ```bash
   venv\Scripts\python.exe ingestion\seed_demo.py   # (si no tienes apuntes creados, genera demo)
   ```

---

## 🎮 Cómo jugar

| Comando | Qué abre |
|---------|----------|
| `evoflash_web.bat` | **Menú Web principal** → enlace a todos los juegos |
| `evoflash.bat` | CLI RPG (nickname tradicional) |
| `evoflash_skilltree.bat` | Skill Tree (D3.js, click en nodos) |
| `evoflash_examen.bat` | Examen N1→N4 más estricto |
| `evoflash_examenes.bat` | Configurar tus exámenes (fecha + temas) |
| `evoflash_temas.bat` | Pausar/activar carpetas del vault |
| `evoflash_stats.bat` | Estadísticas por área |

---

## Web Dashboard (http://127.0.0.1:8766) — ¡Nuevo! ✨

**Ya no necesitas el CMD**:

| Sección | Qué hace en la web |
|---------|-------------------|
| 🗺️ **Skill Tree** | Mapa visual: nodos por nivel. Click información, doble-click → abre `.md` en Obsidian, drag para reordenar visualmente. |
| 📊 **Stats** | Tabla por área: tarjetas totales, aciertos, resurrección Boss Battles. |
| ⏸️ **Temas** | Activa/pausa carpetas de Obsidian (elige número, no "TODOS" automo). |
| 📋 **Exámenes** | Configura fecha, temas, nivel máximo, notas. Guarda en `config/examenes.json`. |
| 🎮 **Jugar** | Ir al juego interactivo (si está habilitado). |

---

## 🧠 Cómo funciona el aprendizaje

1. **Une respuesta** → Gemini la evalúa con rigor (✅ Aciertos / ❌ Vacíos / 🎯 Exige más / ⚡ Reto)
2. **Si aciertas**:
   - Evoluciona la tarjeta al siguiente nivel (N1 → N2 → ...)
   - Te sugiere tarjetas hermanas que podrías crear (plantar directamente en tu Obsidian)
   - Si ya estás en N4 y contestas otra del **mismo tema**: se crea un **COMBO** (Nivel 5 — fusión de conceptos)
3. **Si fallas**: reinicia al Nivel 1 (SM-2 simplificado) — reaparecerá mañana.
4. **Boss Battles (Nivel 4)**: Cuando ya controlas una área, la tarjeta se convierte en un **escenario de diagnóstico** (problemas reales de IT, no definiciones).

---

## 🔧 Configurar tu Obsidian (exclusión por seguridad)

Asegúrate de tener tu carpeta de Preguntas en:
```
C:\Users\usuario\Documents\Obsidian Vault\Questions
```

Las tarjetas leídas del diccionario principal (tema=/concepto/nivel_actual) tener persistencia en si mismos.

> **Importante**: ⚔️ No edites `obsidian://` (volcado en `escribir_evolucion`) mientras está en uso — hacer esto puede no guardar cambios correctamente.

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

Deben pasar 6/6 (unitarios + CLI mocking).

---

## 🛠️ Customización avanzada

| ¿Qué quieres? | Edita |
|---------------|-------|
| Añadir más modelos (failover) | `llm_interface/judge.py` (línea 8) |
| Cambiar XP a por nivel | `ui_cli/play.py` (XP dict) |
| Cambiar intervalos SM-2 (1/3/7/14 días) | `core_engine/flashcard.py` (marcar_acierto) |
| Añadir 4 nuevos idiomas para usar en app | No recomendado — gemini no es multilingüe |
| Añadir nuevos endpoints web | `web_dashboard/servidor.py` (clase Handler, añade `/api/nueva_cosa`) |

---

## 📂 Estructura del repositorio (archivos que sí/no se suben)

```
evoflash/
├── .gitignore               ← ignora .env, venv/, data.json
├── README.md                ← esta página
├── requirements.txt
├── LICENSE                  ← MIT
├── evoflash.py              ← jurásico, se va eliminando con progreso
├── venv/                    ← (no subir)
├── config/                  ← settings.py, examenes.json, temas_estudio.json
├── core_engine/             ← modelos SM-2, schemas Pydantic
├── llm_interface/           ← Gemini client + fallback multi-modelo
├── vault_manager/           ← leer y escribir .md Markdown
├── ingestion/               ← nuevas tarjetas generadas por IA
├── ui_cli/                  ← juego por CMD (play.py, examenes.py, temas.py...)
├── web_dashboard/           ← menú web, skill tree, servidor API
│   ├── skill_tree.html      ← D3.js fijo (sin tick bug)
│   ├── export_data.py       ← convierte .md → data.json
│   └── servidor.py          ← http.server en 127.0.0.1:8766
└── tests/                   ← 6 tests unitarios
```

---

## ⚡ Cosas pendientes que añadiré luego
- **Captura por voz** (Web Speech API directo en el navegador)
- **Sincronización bidireccional Obsidian** (cambios en .md se reflejan instantáneamente en web)
- **Alertas por correo** cuando un examen está próximo
- **Deck "Combos"** automático (si detecta N4+N4 mismo tema → genera N5 automáticamente)
- **Feature mobile-first** (modo PWA con IndexedDB local)

---

Arquitectura en una frase: *Apunta a principios → aplicas el Graph → guarda → evoluciona* en markdown, resten peritable y use-la directamente.
