# =====================================================================
#  Focus! - Paso 5: publicar el portal web (web/) en Azure Static Web Apps
#    - Compila el portal con Vite apuntando a la API de App Service
#    - Crea la Static Web App (plan Free) si no existe
#    - Sube web/dist con la CLI de Static Web Apps
#
#  Requiere Node.js 18+ y haber corrido antes 01 y 02 (la API debe existir).
#  Uso (PowerShell, desde la carpeta del repo):
#    .\deploy\05_desplegar_web.ps1
# =====================================================================
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

function Paso($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Revisar($accion) { if ($LASTEXITCODE -ne 0) { throw "Fallo: $accion (revisa el mensaje de arriba)" } }

$carpetaWeb = Join-Path $RaizRepo "web"
$urlApi = "https://$WebApp.azurewebsites.net"

Paso "Compilando el portal (VITE_API_URL=$urlApi)"
Push-Location $carpetaWeb
try {
    if (-not (Test-Path "node_modules")) { npm ci --no-audit --no-fund; Revisar "npm ci" }
    # La variable de entorno tiene prioridad sobre web/.env, que suele apuntar a la API local
    $env:VITE_API_URL = $urlApi
    npx vite build; Revisar "vite build"
} finally {
    Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue
    Pop-Location
}

Paso "Static Web App $SitioWeb ($UbicacionWeb, plan Free)"
$existe = az staticwebapp list -g $Grupo --query "[?name=='$SitioWeb'].name" -o tsv
if (-not $existe) {
    az staticwebapp create -g $Grupo -n $SitioWeb -l $UbicacionWeb --sku Free -o none; Revisar "crear Static Web App"
}
$token = az staticwebapp secrets list -g $Grupo -n $SitioWeb --query "properties.apiKey" -o tsv; Revisar "leer token de despliegue"

Paso "Subiendo web/dist"
# El token va por variable de entorno para que npx no lo imprima en pantalla
$env:SWA_CLI_DEPLOYMENT_TOKEN = $token
try {
    npx --yes @azure/static-web-apps-cli@2.0.10 deploy (Join-Path $carpetaWeb "dist") --env production
    Revisar "despliegue del portal"
} finally {
    Remove-Item Env:SWA_CLI_DEPLOYMENT_TOKEN -ErrorAction SilentlyContinue
}

$host_ = az staticwebapp show -g $Grupo -n $SitioWeb --query "defaultHostname" -o tsv
Write-Host "`nPortal: https://$host_" -ForegroundColor Green
Write-Host "API:    $urlApi (si cambias CORS_ORIGINS en App Service, incluye la URL del portal)"
