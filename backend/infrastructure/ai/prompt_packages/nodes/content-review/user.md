请审查以下章节内容的质量：

【小说信息】
标题：{{novel_title}}
类型：{{novel_genre}}

【人物设定】
{{characters}}

【世界观设定】
{{world_settings}}

【前文概要】
{{previous_summary}}

【本章章纲】
{{chapter_outline}}

【章节内容】
{{chapter_content}}

请从以下七个维度进行审查评分（0-100分）：
1. 情节连贯性（plot_coherence）：情节是否流畅，前后是否呼应，节奏是否得当
2. 人物一致性（character_consistency）：人物言行是否符合设定，性格是否统一
3. 设定一致性（setting_consistency）：是否遵守世界观设定，有无前后矛盾
4. 文笔流畅度（writing_quality）：文字是否优美，描写是否生动，对话是否自然
5. 节奏把控（pacing）：节奏张弛是否有度，是否有拖沓或仓促之感
6. 场景画面感（scene_quality）：场景描写是否有画面感，感官描写是否丰富
7. 红线合规度（red_line_compliance）：是否存在写作红线违规问题

输出 JSON 格式，包含以下字段：
- total_score: 总分（0-100），各维度加权平均
- grade: 等级（S/A/B/C/D），S≥90, A≥75, B≥60, C≥40, D<40
- dimension_scores: 各维度分数对象，包含 plot_coherence, character_consistency, setting_consistency, writing_quality, pacing, scene_quality, red_line_compliance
- issues: 问题列表，每个问题包含 dimension(维度), description(描述), severity(严重程度: high/medium/low)
- suggestions: 改进建议列表（3-5条具体建议）
- red_line_violations: 红线违规列表，每项包含 rule(规则名), description(描述), count(出现次数)
- overall_comment: 总体评价（100-200字）

请严格按照以上字段输出，确保 JSON 格式正确。
