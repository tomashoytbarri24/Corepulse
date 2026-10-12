$body = @{
  model = 'Qwen/Qwen3-4B-GGUF:Q4_K_M'
  messages = @(
    @{ role = 'system'; content = 'Responde en español y en una sola frase.' },
    @{ role = 'user'; content = 'Di: CorePulse AI generativo está funcionando.' }
  )
  temperature = 0.1
  max_tokens = 80
} | ConvertTo-Json -Depth 8

try {
  $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8766/v1/chat/completions' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
  Write-Host ''
  Write-Host '[OK] Respuesta del modelo:' -ForegroundColor Green
  Write-Host $r.choices[0].message.content
} catch {
  Write-Host '[ERROR] El modelo no respondio:' -ForegroundColor Red
  Write-Host $_.Exception.Message
}
Pause
