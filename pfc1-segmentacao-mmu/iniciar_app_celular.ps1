param([int]$Porta=8787,[switch]$RedeLocal,[switch]$Usb)
$entry=Join-Path (Split-Path $PSScriptRoot) 'reconhecedor-iris/iniciar_app_celular.ps1'
& $entry @PSBoundParameters
