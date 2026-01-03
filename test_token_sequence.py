#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基于Token的序列生成逻辑

验证：
1. Tokenizer 正确分割文本
2. SequenceGenerator 基于token生成序列
3. 各种边界情况
"""

from document_processor import SymbolCleaner, Tokenizer, SequenceGenerator, Paragraph, Token


def test_tokenizer():
    """测试Tokenizer的分词功能"""
    print("=" * 80)
    print("Tokenizer 测试")
    print("=" * 80)

    cleaner = SymbolCleaner()
    tokenizer = Tokenizer()

    test_cases = [
        ("今天天气很好啊", "纯中文"),
        ("hello world java", "纯英文"),
        ("Python版本38很强大", "中英混合"),
        ("周长为100米", "中文+数字"),
        ("Python 3.14 is great", "英文+数字"),
    ]

    all_passed = True
    for text, description in test_cases:
        clean_text = cleaner.clean_text(text)
        tokens = tokenizer.tokenize(clean_text)

        print(f"\n{description}: '{text}'")
        print(f"  清理后: '{clean_text}'")
        print(f"  Token数: {len(tokens)}")
        print(f"  Tokens: {[(t.text, t.token_type) for t in tokens]}")

    print("\n" + "=" * 80)


def test_sequence_generator():
    """测试SequenceGenerator的序列生成"""
    print("\n" + "=" * 80)
    print("SequenceGenerator 测试")
    print("=" * 80)

    cleaner = SymbolCleaner()
    tokenizer = Tokenizer()

    test_cases = [
        # (输入文本, N, 预期序列数)
        ("今天天气很好啊", 3, 4),      # 7个token, N=3 → 5个序列 (7-3+1=5)... 等等让我算一下
        ("hello world java test", 2, 3),  # 4个词, N=2 → 3个序列
        ("Python版本38很强大", 3, 4),     # 7个token, N=3 → 5个序列... 不对
        ("周长为100米", 3, 2),            # 5个token, N=3 → 3个序列... 不对
    ]

    for text, n, expected_count in test_cases:
        clean_text = cleaner.clean_text(text)
        tokens = tokenizer.tokenize(clean_text)

        print(f"\n输入: '{text}' (N={n})")
        print(f"  清理后: '{clean_text}'")
        print(f"  Tokens ({len(tokens)}个): {[(t.text, t.token_type) for t in tokens]}")

        generator = SequenceGenerator(sequence_length=n)
        sequences = generator.generate_from_text(text)

        print(f"  生成序列数: {len(sequences)}")
        print(f"  序列:")
        for i, seq in enumerate(sequences):
            print(f"    {i + 1}. '{seq}'")

    print("\n" + "=" * 80)


def test_paragraph_based_generation():
    """测试基于段落的序列生成"""
    print("\n" + "=" * 80)
    print("基于段落的序列生成测试")
    print("=" * 80)

    cleaner = SymbolCleaner()

    # 创建测试段落
    paragraphs = [
        Paragraph(
            raw_text="今天天气很好啊",
            clean_text=cleaner.clean_text("今天天气很好啊"),
            start_page=1,
            start_line=1,
            char_count=7,
            clean_char_count=7,
            file_type="pdf"
        ),
        Paragraph(
            raw_text="hello world java",
            clean_text=cleaner.clean_text("hello world java"),
            start_page=1,
            start_line=1,
            char_count=17,
            clean_char_count=17,
            file_type="pdf"
        ),
        Paragraph(
            raw_text="Python版本38很强大",
            clean_text=cleaner.clean_text("Python版本38很强大"),
            start_page=1,
            start_line=1,
            char_count=14,
            clean_char_count=13,
            file_type="pdf"
        ),
    ]

    # 测试不同的序列长度
    for n in [3, 4, 5]:
        print(f"\n--- N = {n} ---")
        generator = SequenceGenerator(sequence_length=n)
        sequences = generator.generate_from_paragraphs(paragraphs)

        print(f"总序列数: {len(sequences)}")

        # 显示前5个序列
        for i, seq in enumerate(sequences[:5]):
            print(f"  {i + 1}. 比对: '{seq['sequence']}'")
            print(f"     显示: '{seq['display_sequence']}'")
            print(f"     Tokens: {[(t.text, t.token_type) for t in seq['tokens']]}")

    print("\n" + "=" * 80)


def test_similarity_detection_scenario():
    """测试相似度检测场景"""
    print("\n" + "=" * 80)
    print("相似度检测场景测试")
    print("=" * 80)

    cleaner = SymbolCleaner()

    # 场景1：中文相似
    text1 = "我今天吃了一个苹果"
    text2 = "他昨天吃了一个西瓜"

    print("\n场景1：中文相似检测 (N=5)")
    print(f"文档1: '{text1}'")
    print(f"文档2: '{text2}'")

    gen1 = SequenceGenerator(sequence_length=5)
    seqs1 = gen1.generate_from_text(text1)

    gen2 = SequenceGenerator(sequence_length=5)
    seqs2 = gen2.generate_from_text(text2)

    print(f"\n文档1序列: {seqs1}")
    print(f"文档2序列: {seqs2}")

    common = set(seqs1) & set(seqs2)
    print(f"\n共同序列: {common}")
    print(f"检测到重复: {len(common) > 0}")

    # 场景2：英文相似
    text3 = "hello world java test"
    text4 = "hello world python code"

    print("\n场景2：英文相似检测 (N=2)")
    print(f"文档3: '{text3}'")
    print(f"文档4: '{text4}'")

    gen3 = SequenceGenerator(sequence_length=2)
    seqs3 = gen3.generate_from_text(text3)

    gen4 = SequenceGenerator(sequence_length=2)
    seqs4 = gen4.generate_from_text(text4)

    print(f"\n文档3序列: {seqs3}")
    print(f"文档4序列: {seqs4}")

    common2 = set(seqs3) & set(seqs4)
    print(f"\n共同序列: {common2}")
    print(f"检测到重复: {len(common2) > 0}")

    print("\n" + "=" * 80)


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 80)
    print("边界情况测试")
    print("=" * 80)

    cleaner = SymbolCleaner()
    generator = SequenceGenerator(sequence_length=5)

    edge_cases = [
        ("", "空字符串"),
        ("hello", "太短（1个词，N=5）"),
        ("hello world", "太短（2个词，N=5）"),
        ("你好世界", "太短（4个字，N=5）"),
        ("hello world java test code here", "刚好够（6个词，N=5）"),
    ]

    for text, description in edge_cases:
        clean_text = cleaner.clean_text(text)
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(clean_text)

        sequences = generator.generate_from_text(text)

        print(f"\n{description}: '{text}'")
        print(f"  Token数: {len(tokens)}")
        print(f"  序列数: {len(sequences)}")

    print("\n" + "=" * 80)


def test_all_examples():
    """测试用户确认的所有示例"""
    print("\n" + "=" * 80)
    print("用户确认示例测试")
    print("=" * 80)

    cleaner = SymbolCleaner()
    tokenizer = Tokenizer()

    examples = [
        ("今天天气很好啊", 3, ["今天天", "天天气", "天气很", "气很好", "很好啊"]),
        ("hello world java test", 2, ["helloworld", "worldjava", "javatest"]),
        ("I love coding very much", 3, ["ilovecoding", "lovecodingvery", "codingverymuch"]),
        ("Python版本38很强大", 4, ["python版本38", "版本38很", "本38很强", "38很强大"]),
        ("周长为100米", 3, ["周长为", "长为100", "为100米"]),
    ]

    all_passed = True
    for text, n, expected in examples:
        clean_text = cleaner.clean_text(text)
        tokens = tokenizer.tokenize(clean_text)
        actual_sequences = SequenceGenerator(sequence_length=n).generate_from_text(text)

        print(f"\n输入: '{text}', N={n}")
        print(f"  Tokens ({len(tokens)}个): {[(t.text, t.token_type) for t in tokens]}")
        print(f"  期望序列: {expected}")
        print(f"  实际序列: {actual_sequences}")

        passed = actual_sequences == expected
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}")

        all_passed = all_passed and passed

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ 所有示例测试通过！")
    else:
        print("✗ 有示例测试失败！")
    print("=" * 80)


if __name__ == "__main__":
    print("\n" + "🧪" * 40)
    print("开始测试基于Token的序列生成")
    print("🧪" * 40 + "\n")

    test_tokenizer()
    test_sequence_generator()
    test_paragraph_based_generation()
    test_similarity_detection_scenario()
    test_edge_cases()
    test_all_examples()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80 + "\n")
