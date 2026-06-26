# Claude API 快速设置脚本
# 在PowerShell中运行此脚本

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Claude API 快速设置" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 提示用户输入API密钥
$apiKey = Read-Host "请输入您的Anthropic API密钥 (格式: sk-ant-...)"

if ($apiKey -and $apiKey.StartsWith("sk-ant-")) {
    # 设置环境变量
    $env:ANTHROPIC_API_KEY = $apiKey
    Write-Host ""
    Write-Host "✅ API密钥已设置到当前会话" -ForegroundColor Green
    Write-Host ""
    Write-Host "现在可以运行测试:" -ForegroundColor Yellow
    Write-Host "   python test_claude_api.py" -ForegroundColor Yellow
    Write-Host ""
    
    # 询问是否永久设置
    $permanent = Read-Host "是否永久设置到用户环境变量? (Y/n)"
    if ($permanent -ne "n" -and $permanent -ne "N") {
        [System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', $apiKey, 'User')
        Write-Host "✅ 已永久设置到用户环境变量" -ForegroundColor Green
        Write-Host "   注意: 需要重启Cursor才能生效" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "❌ API密钥格式不正确" -ForegroundColor Red
    Write-Host "   正确格式应以 'sk-ant-' 开头" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan







