# LemonBI

Demo completa de una plataforma de inteligencia de negocios agroindustrial para un productor de limón con empaque en Tucumán, Argentina.

Arquitectura:

- `backend/`: FastAPI + pandas
- `frontend/`: Dash + Plotly + dash-bootstrap-components
- `backend/data/`: datasets mock realistas y coherentes entre módulos

## Módulos disponibles

- Resumen Ejecutivo
- Campo
- Empaque
- Comercial
- Finanzas
- Costos y Rentabilidad
- Contexto Externo

## Requisitos

- Python 3.11+ recomendado
- `pip`

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Regenerar datos mock

Los CSV incluidos ya están listos para usar. Si querés regenerarlos:

```bash
python3 backend/generate_data.py
```

## Ejecutar backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

## Ejecutar frontend

Con el backend ya levantado:

```bash
python3 app.py
```

Frontend disponible en:

- `http://127.0.0.1:8050`

## Acceso demo

La app requiere autenticación local para acceder a los paneles.

- Usuario: `Tomás`
- Contraseña: `1234`

## Variables útiles

- `LEMON_API_BASE`: base URL del backend para Dash.
- `LEMON_DEMO_SECRET_KEY`: secret key opcional para la sesión Flask del frontend.

Ejemplo:

```bash
LEMON_API_BASE=http://127.0.0.1:8000 python3 app.py
```

## Estructura

```text
.
├── app.py
├── backend/
│   ├── data/
│   ├── routes/
│   ├── services/
│   └── main.py
├── frontend/
│   ├── assets/
│   ├── components/
│   ├── pages/
│   └── utils.py
├── requirements.txt
└── README.md
```

## Notas

- El frontend consume exclusivamente la API; no lee CSV directamente.
- Los datasets mock incluyen campaña, campo, empaque, comercial, costos, finanzas y contexto externo.
- Los indicadores financieros están calculados sobre la fecha de campaña filtrada, no sobre la fecha del sistema.
