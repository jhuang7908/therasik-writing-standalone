# DeepSeek API 环境变量设置脚本
# 运行此脚本设置 DEEPSEEK_API_KEY 环境变量

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DeepSeek API 环境变量设置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 检查是否已设置
$currentKey = [System.Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
if ($currentKey) {
    Write-Host "✅ 已找到 DEEPSEEK_API_KEY 环境变量" -ForegroundColor Green
    Write-Host "   密钥: $($currentKey.Substring(0, [Math]::Min(10, $currentKey.Length)))...$($currentKey.Substring($currentKey.Length-4))" -ForegroundColor Gray
    Write-Host ""
    Write-Host "要更新密钥吗？(y/n)" -ForegroundColor Yellow
    $update = Read-Host
    if ($update -ne 'y') {
        Write-Host "✅ 保持现有配置" -ForegroundColor Green
        exit 0
    }
}

# 获取新的API密钥
Write-Host ""
Write-Host "📝 请输入您的 DeepSeek API 密钥：" -ForegroundColor Yellow
Write-Host "   获取地址: https://platform.deepseek.com/" -ForegroundColor Gray
Write-Host ""

$apiKey = Read-Host "API密钥" -AsSecureString
$plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
)

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    Write-Host "❌ 未输入API密钥" -ForegroundColor Red
    exit 1
}

# 设置环境变量
try {
    [System.Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $plainKey, "User")
    Write-Host "✅ 已设置 DEEPSEEK_API_KEY 环境变量（用户级别）" -ForegroundColor Green
    
    # 同时设置进程级别的环境变量，立即生效
    $env:DEEPSEEK_API_KEY = $plainKey
    Write-Host "✅ 已设置当前进程的环境变量" -ForegroundColor Green
    
} catch {
    Write-Host "❌ 设置环境变量失败: $_" -ForegroundColor Red
    exit 1
}

# 测试配置
Write-Host ""
Write-Host "🔧 测试配置..." -ForegroundColor Cyan

# 检查Python和openai库
try {
    $pythonCheck = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python 已安装: $pythonCheck" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Python 可能未正确安装" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  无法检查Python安装" -ForegroundColor Yellow
}

# 创建测试脚本
$testScript = @'
import os
import sys

print("=" * 50)
print("DeepSeek API 配置测试")
print("=" * 50)

api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ 未找到 DEEPSEEK_API_KEY 环境变量")
    sys.exit(1)

print(f"✅ 找到API密钥: {api_key[:10]}...{api_key[-4:]}")
print("✅ 环境变量配置成功")

# 检查openai库
try:
    from openai import OpenAI
    print("✅ openai 库已安装")
    
    # 简单测试（不实际调用API）
    print("📋 配置信息:")
    print(f"   模型: deepseek-chat")
    print(f"   端点: https://api.deepseek.com/v1")
    print(f"   密钥长度: {len(api_key)} 字符")
    
except ImportError:
    print("⚠️  未安装 openai 库")
    print("💡 安装命令: pip install openai")

print("=" * 50)
print("✅ 配置测试完成")
print("=" * 50)
'@

$testScript | Out-File -FilePath "test_deepseek_config.py" -Encoding UTF8
python test_deepseek_config.py

# 清理
Remove-Item "test_deepseek_config.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "下一步操作" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 重启 Cursor 使环境变量生效" -ForegroundColor Yellow
Write-Host "2. 在 Cursor 中配置 DeepSeek Chat:" -ForegroundColor Yellow
Write-Host "   - 按 Ctrl+, 打开设置" -ForegroundColor Gray
Write-Host "   - 搜索 'AI Models'" -ForegroundColor Gray
Write-Host "   - 添加模型:" -ForegroundColor Gray
Write-Host "     Provider: DeepSeek" -ForegroundColor Gray
Write-Host "     Model Name: deepseek-chat" -ForegroundColor Gray
Write-Host "     API Endpoint: https://api.deepseek.com/v1" -ForegroundColor Gray
Write-Host "     API Key: [使用环境变量]" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 或者立即使用 gpt-4o:" -ForegroundColor Yellow
Write-Host "   - 在对话窗口右上角选择 'gpt-4o'" -ForegroundColor Gray
Write-Host "   - 无需额外配置" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ 设置完成！" -ForegroundColor Green


