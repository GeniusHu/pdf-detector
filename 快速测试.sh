#!/bin/bash

# PDF相似度检测系统 - 快速测试脚本
# 用于验证系统是否正常工作

echo "========================================"
echo "  PDF相似度检测系统 - 快速测试"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python"
    exit 1
fi

echo "✅ Python3 已安装"

# 检查必要的Python包
echo
echo "正在检查依赖包..."

packages=("pdfplumber" "numpy")
missing_packages=()

for package in "${packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "✅ $package 已安装"
    else
        echo "❌ $package 未安装"
        missing_packages+=($package)
    fi
done

# 如果有缺失的包，提示安装
if [ ${#missing_packages[@]} -gt 0 ]; then
    echo
    echo "正在安装缺失的依赖包..."
    pip3 install -r requirements.txt
fi

echo
echo "========================================"
echo "开始快速测试（使用默认参数）"
echo "========================================"
echo

# 运行快速模式测试
python3 main.py 张远向030500马克思主义理论20250717181713.pdf 试验.pdf --fast --main-content-only

echo
echo "========================================"
echo "测试完成！"
echo "========================================"
echo
echo "如果看到上方显示了相似度检测结果，说明系统运行正常。"
echo
echo "查看结果文件："
ls -lh fast_张远向030500马克思主义理论20250717181713_试验_results.txt 2>/dev/null && echo "✅ 结果文件已生成" || echo "❌ 结果文件未生成"
echo
echo "更多使用方法请查看: 使用说明.md"