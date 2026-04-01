from __future__ import annotations

from flask import render_template_string


LOGIN_TEMPLATE = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LemonBI | Acceso</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/assets/styles.css">
  </head>
  <body class="login-body">
    <div class="login-shell">
      <div class="login-backdrop login-backdrop-a"></div>
      <div class="login-backdrop login-backdrop-b"></div>

      <section class="login-panel login-brand-panel">
        <div class="login-brand-chip">Demo Agro SaaS</div>
        <div class="login-brand-title">LemonBI</div>
        <div class="login-brand-subtitle">
          Plataforma de inteligencia de negocios para producción, empaque, comercial y finanzas del negocio citrícola.
        </div>

        <div class="login-value-card">
          <div class="login-value-title">Visión operativa integrada</div>
          <div class="login-value-text">
            Una sola experiencia para seguir cosecha, rendimiento de empaque, ventas, caja y rentabilidad por campaña.
          </div>
        </div>

        <div class="login-metric-strip">
          <div class="login-metric">
            <span class="login-metric-value">7</span>
            <span class="login-metric-label">módulos conectados</span>
          </div>
          <div class="login-metric">
            <span class="login-metric-value">2023-2024</span>
            <span class="login-metric-label">campañas demo</span>
          </div>
          <div class="login-metric">
            <span class="login-metric-value">FastAPI + Dash</span>
            <span class="login-metric-label">arquitectura base</span>
          </div>
        </div>
      </section>

      <section class="login-panel login-form-panel">
        <div class="login-form-header">
          <div class="login-form-kicker">Acceso al sistema</div>
          <h1>Ingresar a la demo</h1>
          <p>Accedé al entorno de business intelligence agroindustrial con sesión local protegida.</p>
        </div>

        {% if error %}
        <div class="login-error">
          <div class="login-error-title">No fue posible iniciar sesión</div>
          <div class="login-error-text">Verificá usuario y contraseña e intentá nuevamente.</div>
        </div>
        {% endif %}

        <form method="post" action="/login" class="login-form">
          <input type="hidden" name="next" value="{{ next_path }}" />

          <label class="login-field">
            <span>Usuario</span>
            <input type="text" name="username" autocomplete="username" placeholder="Tomás" required />
          </label>

          <label class="login-field">
            <span>Contraseña</span>
            <input type="password" name="password" autocomplete="current-password" placeholder="••••" required />
          </label>

          <button type="submit" class="login-submit">Ingresar</button>
        </form>

        <div class="login-demo-hint">
          <span>Credenciales demo</span>
          <strong>Usuario: Tomás</strong>
          <strong>Contraseña: 1234</strong>
        </div>
      </section>
    </div>
  </body>
</html>
"""


def render_login_page(error: bool = False, next_path: str = "/") -> str:
    return render_template_string(LOGIN_TEMPLATE, error=error, next_path=next_path)
