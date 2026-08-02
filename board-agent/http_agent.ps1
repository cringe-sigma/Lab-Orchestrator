# HTTP Agent Bridge — PowerShell (Windows原生, 零依赖)
# 用法: .\http_agent.ps1 <服务器IP> <板子IP> <用户名> <密码> <TOKEN>
param(
    [string]$Server,
    [string]$BoardIP,
    [string]$BoardUser,
    [string]$BoardPwd,
    [string]$Token
)

if (-not $Server -or -not $BoardIP -or -not $Token) {
    Write-Host "用法: .\http_agent.ps1 <服务器IP> <板子IP> <用户名> <密码> <TOKEN>"
    Write-Host "示例: .\http_agent.ps1 10.65.80.155 10.42.0.174 gjh gejiahao TOKEN"
    exit 1
}

Write-Host "服务器: $Server"
Write-Host "板子:   $BoardUser@$BoardIP"
Write-Host "Token:  $($Token.Substring(0, [Math]::Min(8,$Token.Length)))..."

# 测试连通性
try {
    $health = Invoke-RestMethod -Uri "http://$Server`:8000/api/health" -TimeoutSec 5
    Write-Host "服务器连通 OK: $($health.status)"
} catch {
    Write-Host "无法连接服务器: $_"
    exit 1
}

# 测试SSH
Write-Host "测试SSH..."
$sshTest = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$BoardUser@$BoardIP" "echo SSH_OK" 2>&1
if ($sshTest -match "SSH_OK") {
    Write-Host "SSH连接 OK"
} else {
    Write-Host "SSH连接失败: $sshTest"
    exit 1
}

$BaseUrl = "http://$Server`:8000"

# 注册
Write-Host "注册到服务器..."
$body = @{token=$Token} | ConvertTo-Json
try {
    $reg = Invoke-RestMethod -Uri "$BaseUrl/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
    $BoardId = $reg.board_id
    Write-Host "注册成功: board_id=$BoardId"
} catch {
    Write-Host "注册失败: $_"
    exit 1
}

# 轮询命令
while ($true) {
    try {
        $cmds = Invoke-RestMethod -Uri "$BaseUrl/api/boards/$BoardId/pending-commands" -TimeoutSec 30
        foreach ($cmd in $cmds.commands) {
            $cmdId = $cmd.id
            $command = $cmd.command
            Write-Host "  执行: $($command.Substring(0,[Math]::Min(60,$command.Length)))"

            $output = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$BoardUser@$BoardIP" $command 2>&1 | Out-String

            $result = @{cmd_id=$cmdId; output=$output} | ConvertTo-Json
            Invoke-RestMethod -Uri "$BaseUrl/api/boards/$BoardId/command-result" -Method Post -Body $result -ContentType "application/json" -TimeoutSec 10 | Out-Null
            Write-Host "    结果已回传"
        }
        Start-Sleep -Seconds 2
    } catch {
        Start-Sleep -Seconds 5
    }
}
