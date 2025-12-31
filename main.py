#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF相似序列检测主程序
用于检测两个PDF文件中的相似序列
"""

import sys
import os
import time
import argparse
from pathlib import Path

# 导入我们的模块
from duplicate_detector import DuplicateDetector
from optimized_duplicate_detector import OptimizedSimilarSequenceDetector, fast_similarity_detection
from enhanced_pdf_extractor import EnhancedPDFTextExtractor, TextExtractionConfig, create_default_main_content_extractor


def check_pdf_files(pdf1_path: str, pdf2_path: str) -> bool:
    """
    检查PDF文件是否存在和可读

    Args:
        pdf1_path: 第一个PDF文件路径
        pdf2_path: 第二个PDF文件路径

    Returns:
        bool: 文件检查是否通过
    """
    # 检查文件1
    if not os.path.exists(pdf1_path):
        print(f"错误: 文件1不存在: {pdf1_path}")
        return False

    if not os.path.isfile(pdf1_path):
        print(f"错误: 文件1不是有效的文件: {pdf1_path}")
        return False

    if not pdf1_path.lower().endswith('.pdf'):
        print(f"警告: 文件1可能不是PDF文件: {pdf1_path}")

    # 检查文件2
    if not os.path.exists(pdf2_path):
        print(f"错误: 文件2不存在: {pdf2_path}")
        return False

    if not os.path.isfile(pdf2_path):
        print(f"错误: 文件2不是有效的文件: {pdf2_path}")
        return False

    if not pdf2_path.lower().endswith('.pdf'):
        print(f"警告: 文件2可能不是PDF文件: {pdf2_path}")

    # 检查文件大小
    size1 = os.path.getsize(pdf1_path)
    size2 = os.path.getsize(pdf2_path)

    print(f"文件1: {pdf1_path} ({size1 / 1024 / 1024:.1f} MB)")
    print(f"文件2: {pdf2_path} ({size2 / 1024 / 1024:.1f} MB)")

    if size1 == 0 or size2 == 0:
        print("错误: 其中一个文件为空")
        return False

    return True


def get_output_filename(pdf1_path: str, pdf2_path: str) -> str:
    """
    生成输出文件名

    Args:
        pdf1_path: 第一个PDF文件路径
        pdf2_path: 第二个PDF文件路径

    Returns:
        str: 输出文件名
    """
    # 获取文件名（不含扩展名）
    name1 = Path(pdf1_path).stem
    name2 = Path(pdf2_path).stem

    # 生成输出文件名
    output_filename = f"duplicate_{name1}_{name2}_results.txt"

    # 确保文件名不会太长
    if len(output_filename) > 100:
        output_filename = f"duplicate_results_{int(time.time())}.txt"

    return output_filename


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="检测两个PDF文件中的相似序列",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py file1.pdf file2.pdf
  python main.py file1.pdf file2.pdf --no-save
  python main.py file1.pdf file2.pdf --similarity 0.8
  python main.py file1.pdf file2.pdf --output custom_results.txt

快速模式（推荐用于大文件）:
  python main.py file1.pdf file2.pdf --fast
  python main.py file1.pdf file2.pdf --fast --similarity 0.9
  python main.py file1.pdf file2.pdf --ultra-fast
  python main.py file1.pdf file2.pdf --fast --processes 8 --max-sequences 3000

注意:
  - 检测8字连续序列的相似度（默认≥0.75）
  - 支持大文件处理（20万字以上）
  - 标准模式可能较慢，建议使用 --fast 选项
  - 快速模式使用多进程并行处理，大幅提升速度
  - 超快模式更严格但速度最快
  - 相似度范围：0.0-1.0，越高越相似
        """
    )

    parser.add_argument('pdf1', help='第一个PDF文件路径')
    parser.add_argument('pdf2', help='第二个PDF文件路径')
    parser.add_argument('--no-save', action='store_true', help='不保存结果到文件')
    parser.add_argument('--output', '-o', help='指定输出文件名')
    parser.add_argument('--similarity', '-s', type=float, default=0.75,
                       help='相似度阈值 (0.0-1.0，默认0.75)')
    parser.add_argument('--exact', action='store_true', help='只检测完全匹配（不使用相似度）')

    # 优化相关选项
    parser.add_argument('--fast', '-f', action='store_true', help='使用快速模式（多进程+智能优化）')
    parser.add_argument('--processes', '-p', type=int, default=None,
                       help='并行进程数（默认自动检测）')
    parser.add_argument('--max-sequences', '-m', type=int, default=5000,
                       help='每个文件的最大序列数（默认5000，用于控制性能）')
    parser.add_argument('--ultra-fast', action='store_true', help='超快模式（更严格的限制）')

    # 内容过滤选项
    parser.add_argument('--main-content-only', action='store_true', default=True,
                       help='只对比正文内容，过滤引用、批注、页眉页脚等（默认启用）')
    parser.add_argument('--include-references', action='store_true',
                       help='包含参考文献')
    parser.add_argument('--include-citations', action='store_true',
                       help='包含引文引用')
    parser.add_argument('--include-footnotes', action='store_true',
                       help='包含脚注')
    parser.add_argument('--include-headers', action='store_true',
                       help='包含页眉页脚')
    parser.add_argument('--min-line-length', type=int, default=10,
                       help='最小行长度（默认10字符，过滤短行）')
    parser.add_argument('--sequence-length', type=int, default=8,
                       help='序列长度（默认8字符，可设为4-20）')

    # 页码范围选项
    parser.add_argument('--page-range1', type=str, default=None,
                       help='文件1的页码范围，格式: 1-146 (只比对1-146页)')
    parser.add_argument('--page-range2', type=str, default=None,
                       help='文件2的页码范围，格式: 1-169 (只比对1-169页)')

    parser.add_argument('--version', action='version', version='PDF相似序列检测器 v2.1')

    args = parser.parse_args()

    # 验证相似度阈值
    if not 0.0 <= args.similarity <= 1.0:
        print("错误: 相似度阈值必须在0.0-1.0之间")
        sys.exit(1)

    # 处理优化模式参数
    max_sequences = args.max_sequences
    similarity_threshold = args.similarity

    if args.ultra_fast:
        print("⚡ 超快模式启用")
        similarity_threshold = 0.9  # 更严格的相似度
        # 只有用户没指定max_sequences时才覆盖
        if max_sequences == 5000:  # 默认值
            max_sequences = 2000
        print(f"配置: 相似度≥{similarity_threshold}, 最大序列数={max_sequences}")

    elif args.fast:
        print("🚀 快速模式启用")
        similarity_threshold = 0.8  # 更严格的相似度
        # 只有用户没指定max_sequences时才覆盖
        if max_sequences == 5000:  # 默认值
            max_sequences = 5000
        print(f"配置: 相似度≥{similarity_threshold}, 最大序列数={max_sequences}")

    # 解析页码范围
    def parse_page_range(range_str: str):
        """解析页码范围字符串，如 '1-146' -> (1, 146)"""
        if not range_str:
            return None
        try:
            parts = range_str.split('-')
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        except:
            pass
        return None

    page_range1 = parse_page_range(args.page_range1)
    page_range2 = parse_page_range(args.page_range2)

    # 创建内容过滤配置（两个文件分别配置）
    content_config1 = TextExtractionConfig(
        include_references=args.include_references,
        include_footnotes=args.include_footnotes,
        include_citations=args.include_citations,
        include_page_numbers=args.include_headers,
        include_headers_footers=args.include_headers,
        include_annotations=False,
        min_line_length=args.min_line_length,
        remove_duplicate_lines=True,
        page_range=page_range1
    )

    content_config2 = TextExtractionConfig(
        include_references=args.include_references,
        include_footnotes=args.include_footnotes,
        include_citations=args.include_citations,
        include_page_numbers=args.include_headers,
        include_headers_footers=args.include_headers,
        include_annotations=False,
        min_line_length=args.min_line_length,
        remove_duplicate_lines=True,
        page_range=page_range2
    )

    # 使用一个通用的配置用于显示
    content_config = content_config1

    # 显示欢迎信息
    print("=" * 80)
    print("PDF相似序列检测器 v2.1 - 正文内容对比版")
    print("=" * 80)

    seq_len = args.sequence_length
    if args.exact:
        print(f"功能: 检测两个PDF文件中完全相同的{seq_len}字序列")
    elif args.ultra_fast:
        print(f"功能: 超快模式检测相似度≥{similarity_threshold:.2f}的{seq_len}字序列")
    elif args.fast:
        print(f"功能: 快速模式检测相似度≥{similarity_threshold:.2f}的{seq_len}字序列")
    else:
        print(f"功能: 检测两个PDF文件中相似度≥{args.similarity:.2f}的{seq_len}字序列")

    print("规则: 过滤标点符号，英文单词算一个字，中文逐字计算，数字整体算一个字")
    print("输出: 相似序列及在两个文件中的位置信息和差异说明")

    # 显示内容过滤设置
    print("\n📄 内容过滤设置:")
    if args.main_content_only:
        print("✅ 只对比正文内容（过滤: 引用、批注、页眉页脚等）")
    else:
        print("⚠️  包含所有内容（可能影响检测精度）")

    if args.include_references:
        print("✅ 包含参考文献")
    if args.include_citations:
        print("✅ 包含引文引用")
    if args.include_footnotes:
        print("✅ 包含脚注")
    if args.include_headers:
        print("✅ 包含页眉页脚")

    print(f"📏 最小行长度: {args.min_line_length} 字符")

    if args.fast or args.ultra_fast:
        print(f"\n🚀 性能优化:")
        print(f"   多进程处理 (进程数: {args.processes or '自动'})")
        print(f"   每文件最多{max_sequences:,}个序列")

    print("=" * 80)

    # 检查文件
    if not check_pdf_files(args.pdf1, args.pdf2):
        print("\n文件检查失败，请检查文件路径")
        sys.exit(1)

    try:
        # 运行检测
        if args.fast or args.ultra_fast:
            # 使用优化版检测器
            print(f"\n🚀 使用优化版检测器（正文内容对比）...")
            print(f"📏 序列长度: {args.sequence_length} 字符")
            optimized_detector = OptimizedSimilarSequenceDetector(
                args.pdf1, args.pdf2, similarity_threshold, args.processes, max_sequences, args.sequence_length
            )

            # 设置内容过滤配置
            if args.main_content_only:
                # 使用增强版PDF提取器
                enhanced_extractor1 = EnhancedPDFTextExtractor(content_config1, args.pdf1)
                enhanced_extractor2 = EnhancedPDFTextExtractor(content_config2, args.pdf2)

                # 替换检测器中的提取器
                optimized_detector.extractor1 = enhanced_extractor1
                optimized_detector.extractor2 = enhanced_extractor2
                print("✅ 已启用正文内容过滤")

            print(f"📝 内容提取配置:")
            print(f"   参考文献: {'包含' if content_config.include_references else '过滤'}")
            print(f"   引文引用: {'包含' if content_config.include_citations else '过滤'}")
            print(f"   页眉页脚: {'包含' if content_config.include_headers_footers else '过滤'}")
            print(f"   最小行长度: {content_config.min_line_length} 字符")

            # 设置输出文件名
            if not args.no_save:
                if args.output:
                    output_file = args.output
                else:
                    if args.ultra_fast:
                        output_file = get_output_filename(args.pdf1, args.pdf2).replace("duplicate_", "ultra_fast_")
                    else:
                        output_file = get_output_filename(args.pdf1, args.pdf2).replace("duplicate_", "fast_")

                # 修改检测器的保存方法
                original_save_method = optimized_detector.save_results_optimized
                def save_with_custom_filename(similar_sequences, filename=output_file):
                    original_save_method(similar_sequences, filename)
                optimized_detector.save_results_optimized = save_with_custom_filename

            # 运行优化版检测
            similar_sequences = optimized_detector.run_detection_optimized(
                save_to_file=not args.no_save,
                show_max_results=30,
                show_progress=True
            )

            result_count = len(similar_sequences)
            result_type = f"相似度≥{similarity_threshold:.2f}"

        else:
            # 使用标准版检测器
            print(f"\n🔍 使用标准版检测器...")
            detector = DuplicateDetector(args.pdf1, args.pdf2, args.similarity)

            # 设置输出文件名
            if not args.no_save:
                if args.output:
                    output_file = args.output
                else:
                    if args.exact:
                        output_file = get_output_filename(args.pdf1, args.pdf2).replace("duplicate_", "exact_match_")
                    else:
                        output_file = get_output_filename(args.pdf1, args.pdf2).replace("duplicate_", f"similarity_{args.similarity:.2f}_")

                # 修改检测器的保存方法
                original_save_method = detector.similarity_detector.save_results
                def save_with_custom_filename(similar_sequences, filename=output_file):
                    original_save_method(similar_sequences, filename)
                detector.similarity_detector.save_results = save_with_custom_filename

            # 运行检测
            if args.exact:
                print(f"\n开始检测完全相同的8字序列...")
                repeated_sequences = detector.run_detection(save_to_file=not args.no_save)
                result_count = len(repeated_sequences)
                result_type = "完全相同"
            else:
                print(f"\n开始检测相似8字序列...")
                print("⚠️  标准模式可能较慢，建议使用 --fast 选项")
                similar_sequences = detector.run_similarity_detection(save_to_file=not args.no_save)
                result_count = len(similar_sequences)
                result_type = f"相似度≥{args.similarity:.2f}"

        # 显示简要结果
        print("\n" + "=" * 80)
        print("检测完成!")
        print(f"找到 {result_count} 个{result_type}的{args.sequence_length}字序列")

        if not args.no_save:
            print(f"详细结果已保存到: {output_file}")

        if args.fast or args.ultra_fast:
            print("🎉 优化模式成功加速检测!")
        else:
            print("💡 提示：下次可以尝试 --fast 选项以获得更快的速度")

        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n用户中断检测过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n检测过程中发生错误: {e}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        sys.exit(1)


def check_dependencies():
    """检查依赖包是否安装"""
    required_packages = ['pdfplumber']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("错误: 缺少必要的依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请使用以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        sys.exit(1)


if __name__ == "__main__":
    # 检查依赖
    check_dependencies()

    # 运行主程序
    main()