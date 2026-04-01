from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.routes import resumen, campo, empaque, comercial, finanzas, costos, contexto, filtros, drilldown

app = FastAPI(
    title="LemonBI API",
    description="API de Business Intelligence para empresa agroindustrial citrícola - Tucumán, Argentina",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1200)

app.include_router(resumen.router, prefix="/api/resumen", tags=["Resumen"])
app.include_router(campo.router, prefix="/api/campo", tags=["Campo"])
app.include_router(empaque.router, prefix="/api/empaque", tags=["Empaque"])
app.include_router(comercial.router, prefix="/api/comercial", tags=["Comercial"])
app.include_router(finanzas.router, prefix="/api/finanzas", tags=["Finanzas"])
app.include_router(costos.router, prefix="/api/costos", tags=["Costos"])
app.include_router(contexto.router, prefix="/api/contexto", tags=["Contexto"])
app.include_router(filtros.router, prefix="/api/filtros", tags=["Filtros"])
app.include_router(drilldown.router, prefix="/api/drilldown", tags=["Drill-down"])


@app.get("/")
def root():
    return {"status": "ok", "message": "LemonBI API corriendo"}


@app.get("/health")
def health():
    return {"status": "healthy"}
