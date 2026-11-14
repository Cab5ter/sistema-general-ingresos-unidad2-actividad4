import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from .config import Settings
from .db import Base, database
from .schema import schema
from .access import initialize


def cors_origins():
    """Orígenes permitidos para el dashboard (solo desarrollo local por defecto)."""
    raw = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5500,http://localhost:5500')
    return [origin.strip() for origin in raw.split(',') if origin.strip()]


def create_app(settings: Settings):
    app = FastAPI(title='Sistema General de Ingresos: roles y permisos', debug=False)
    # Unidad III · Actividad 1: el dashboard corre en otro puerto que el API.
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins(),
                       allow_methods=['GET', 'POST', 'OPTIONS'],
                       allow_headers=['Authorization', 'Content-Type'])
    engine, sessions = database(settings.database_url)
    initialize(engine, sessions)
    from .migrate_activity7 import verify_storage
    verify_storage(engine)
    app.state.engine, app.state.sessions, app.state.settings = engine, sessions, settings
    app.include_router(GraphQLRouter(schema, graphql_ide='graphiql'), prefix='/graphql')
    return app