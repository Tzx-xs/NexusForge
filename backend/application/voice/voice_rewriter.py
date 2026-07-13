from .voice_models import VoiceFingerprint


class VoiceRewriter:
    """文风重写建议生成器

    提供目标文风对齐的改写提示
    """

    def generate_rewrite_prompt(self, baseline: VoiceFingerprint, target_text: str, drift_dimensions: list[str]) -> str:
        instructions = []

        if "sentence_length_mean" in drift_dimensions and baseline.sentence_length_mean > 0:
            target_len = int(baseline.sentence_length_mean)
            instructions.append(f"调整句子长度，目标平均句长约 {target_len} 字")

        if "dialogue_ratio" in drift_dimensions:
            target_ratio = baseline.dialogue_ratio
            if target_ratio > 0.3:
                instructions.append("增加人物对话，提升对话占比")
            else:
                instructions.append("减少对话，增加叙述和描写")

        if "lexical_richness" in drift_dimensions:
            instructions.append("丰富词汇选择，使用更多样化的表达方式")

        if "function_word_ratio" in drift_dimensions:
            instructions.append("调整虚词使用频率，匹配目标文风的虚词比例")

        if "ngram_overlap" in drift_dimensions:
            instructions.append("注意常用搭配和四字短语的使用习惯")

        if "paragraph_length_mean" in drift_dimensions:
            instructions.append("调整段落长度，与目标文风的段落节奏保持一致")

        if not instructions:
            instructions.append("保持当前文风进行微调优化")

        prompt = "请按照以下风格要求重写文本：\n\n"
        for i, inst in enumerate(instructions, 1):
            prompt += f"{i}. {inst}\n"

        if baseline.signature_phrases:
            prompt += f"\n参考常用表达：{', '.join(baseline.signature_phrases[:5])}"

        prompt += f"\n\n待改写文本：\n{target_text}\n"

        return prompt

    def generate_style_guide(self, fp: VoiceFingerprint) -> str:
        guide = "=== 文风风格指南 ===\n\n"
        guide += "【词汇特征】\n"
        guide += f"- 词汇丰富度: {fp.lexical_richness:.2%}\n"
        guide += f"- 虚词占比: {fp.function_word_ratio:.2%}\n\n"

        guide += "【句式特征】\n"
        guide += f"- 平均句长: {fp.sentence_length_mean:.1f} 字\n"
        guide += f"- 句长标准差: {fp.sentence_length_std:.1f}\n"
        guide += f"- 句式多样性: {fp.sentence_structure_diversity:.2%}\n\n"

        guide += "【段落特征】\n"
        guide += f"- 平均段长: {fp.paragraph_length_mean:.1f} 字\n\n"

        guide += "【内容构成】\n"
        guide += f"- 对话占比: {fp.dialogue_ratio:.2%}\n"
        guide += f"- 叙述占比: {fp.narration_ratio:.2%}\n\n"

        if fp.signature_phrases:
            guide += "【特色表达】\n"
            for phrase in fp.signature_phrases[:5]:
                guide += f"- {phrase}\n"

        return guide
