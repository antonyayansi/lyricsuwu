# 🎤 Karaoke Console Player

![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python&logoColor=white)

## ✨ Características

- 🔤 **ASCII Art palabra por palabra** — cada palabra se revela en arte ASCII y se acumula
- 🎵 **Sincronización precisa** — basada en timestamps del archivo `.lrc`
- 🎨 **Colores dinámicos** — paleta rotativa por cada línea de la canción
- 📊 **Barra de progreso** — muestra tiempo transcurrido y total
- 👀 **Preview de próximas líneas** — anticipa lo que viene
- 🍎 **Sin dependencias pesadas** — usa `afplay` en macOS (nativo)

## 📦 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/antonyayansi/lyricsuwu
cd lyricsuwu

# Instalar dependencias de Python
pip install -r requirements.txt
```

## 🚀 Uso

```bash
# Con argumentos
python3 karaoke.py <archivo.lrc> <archivo.mp3>

# Auto-detecta archivos .lrc y .mp3 en el directorio
python3 karaoke.py
```

### Ejemplo

```bash
python3 karaoke.py doma.mp3.lrc doma.mp3
```

**Controles:** `Ctrl+C` para salir.

---

## 🔧 Generar archivo .lrc con Whisper

Si no tienes un archivo `.lrc`, puedes generarlo automáticamente con [whisper.cpp](https://github.com/ggerganov/whisper.cpp):

### 1. Compilar whisper.cpp

```bash
cd whisper.cpp

# Descargar modelo
bash ./models/download-ggml-model.sh medium

# Compilar
cmake -B build
cmake --build build -j --config Release
```

### 2. Generar .lrc desde el audio

```bash
./build/bin/whisper-cli \
  -m models/ggml-medium.bin \
  -f ../tu_cancion.mp3 \
  -l es \
  -olrc
```

Esto genera un archivo `.lrc` con timestamps sincronizados.

---

## 🎶 Formato .lrc

El archivo `.lrc` tiene el siguiente formato:

```
[00:12.88] Que fatalidad
[00:17.18] Eres mi héroe y mi villana
[00:20.72] Podría enloquecer
```
