# Analisis de modelos de plasticidad sinaptica

## Descripcion

Este repositorio contiene los scripts de simulacion y analisis desarrollados como parte del Trabajo de Fin de Grado. Su proposito es validar el correcto funcionamiento de dos modelos de plasticidad sinaptica implementados:

- **Modelo de Linsker** (1986)
- **Modelo de STDP** (Spike-Timing-Dependent Plasticity, 2000)

Las simulaciones se ejecutan sobre dos simuladores neuronales distintos, Neun y NEURON, y se incluyen herramientas para la comparacion cruzada de resultados entre ambos.

## Requisitos previos

### Software necesario

- **Python 3**: interprete para la ejecucion de los scripts de simulacion y generacion de graficas.
- **Make**: sistema de construccion utilizado para compilar el simulador Neun.
- **Compilador de C++**: necesario para la compilacion del codigo fuente de Neun (g++ o equivalente).

### Dependencias de Python

Se recomienda utilizar un entorno virtual para aislar las dependencias del proyecto:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuracion del simulador Neun

Para ejecutar cualquier script que no pertenezca a la carpeta `Neuron`, es imprescindible disponer del simulador Neun compilado. El repositorio de Neun debe clonarse **al mismo nivel de directorio** que este proyecto, es decir, como un directorio hermano:

```bash
git clone git@github.com:GonzaloJCC/Neun.git
```

Una vez clonado, compilar el proyecto:

```bash
cd Neun
mkdir build && cd build
cmake ..
make
```

## Estructura del proyecto

El repositorio esta organizado en tres modulos, cada uno orientado a un aspecto distinto del analisis:

```
.
├── Neun/           # Simulaciones ejecutadas sobre el simulador Neun
├── Neuron/         # Simulaciones ejecutadas sobre el simulador NEURON
├── Comparacion/    # Analisis comparativo entre ambos simuladores
├── README.md
└── requirements.txt
```

- **Neun**: scripts para la ejecucion de los modelos de plasticidad sinaptica utilizando el simulador Neun como backend.
- **Neuron**: scripts para la ejecucion de los mismos modelos utilizando el simulador NEURON.
- **Comparacion**: scripts para el contraste y validacion cruzada de los resultados obtenidos con ambos simuladores.

## Ejecucion

Cada modulo se ejecuta de forma independiente desde su directorio correspondiente. Los scripts generan como salida un archivo `.txt` con los datos numericos de la simulacion y tanto un archivo `.pdf` como un archivo `.html` con las graficas resultantes.

### Simulaciones con Neun

- Linsker
```bash
python3 Neun_simulacion/linsker.py
```

- STDP
```bash
python3 Neun_simulacion/STDP/stdp.py
```

### Simulaciones con NEURON

- Linsker
```bash
make -C Neuron_simulacion/Linsker all
```

- STDP
```bash
# Para simulación larga
make -C Neuron_simulacion/STDP all1
```

```bash
# Para simulación corta
make -C Neuron_simulacion/STDP all2
```

### Comparacion entre simuladores

```bash
python3 Comparacion/stdp_comparacion.py
```
