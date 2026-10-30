# =====================================================================
#  Focus! - configuracion comun de los scripts de despliegue
#  Cambia $Sufijo por algo tuyo (minusculas y numeros, max. 10 caracteres):
#  los nombres de SQL Server, Storage y App Service deben ser unicos en Azure.
# =====================================================================
$Sufijo        = "luisbb27"
$Ubicacion     = "centralus"     # Azure for Students solo permite algunas regiones
$UbicacionSql  = $Ubicacion      # si Azure SQL marca "region no disponible", prueba westus2, eastus2 o southcentralus

$Grupo         = "rg-focus"
$SqlServidor   = "focus-sql-$Sufijo"
$SqlBase       = "focusdb"
$SqlUsuario    = "focusadmin"
$Storage       = "focusst$Sufijo"           # 3-24 caracteres, solo minusculas y numeros
$Contenedor    = "fotos"
$PlanApp       = "plan-focus"
$SkuApp        = "B1"                        # F1 es gratis pero se apaga si no se usa; B1 usa creditos
$WebApp        = "focus-api-$Sufijo"
$FuncApp       = "focus-func-$Sufijo"
$SitioWeb      = "focus-web-$Sufijo"         # Azure Static Web Apps (portal web)
$UbicacionWeb  = $Ubicacion                 # Static Web Apps: centralus, eastus2, westus2, westeurope o eastasia

$RaizRepo      = Split-Path -Parent $PSScriptRoot
$ArchivoSalida = Join-Path $PSScriptRoot "salida.env"   # se genera con datos sensibles; esta en .gitignore
