from __future__ import annotations
from typing import Any

GRAPH_FIELD_SEP = "<SEP>"

PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_LANGUAGE"] = "中文"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["DEFAULT_ENTITY_TYPES"] = ["流程", "流程节点", "流程表达式",
                                   "表单", "表单字段",
                                   # "表单", "表单字段", "表单标签页", "表单区域", "表单模块",
                                   # "物料", "物料类型", "物料组", "物料大类",
                                   # "对象",
                                   # "规则", "校验规则", "前段校验项", "提交前校验", "约束项校验", "合规检查", "配置表",
                                   # "功能", "功能按钮",
                                   # "操作", "系统动作", "自动触发动作",
                                   # "角色", "参与者",
                                   ]
PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

PROMPTS["entity_extraction"] = """---目标---
给定一段可能与当前任务相关的文本和一组实体类型，从文本中识别出所有属于这些类型的实体，以及这些实体之间的所有关系。
使用 {language} 作为输出语言。

---步骤---
1. 识别所有实体。对于每个识别出的实体，提取以下信息：
- entity_name：实体名称，使用与输入文本相同的语言。如果为英文，请大写首字母。
- entity_type：实体类型，属于以下类型之一：[{entity_types}]
- entity_description：该实体的属性和活动的全面描述
每个实体的格式如下：("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 在第1步识别出的实体中，找出所有明确相关的 (source_entity, target_entity) 实体对。
对于每一对相关实体，提取以下信息：
- source_entity：源实体名称，来自第1步识别结果
- target_entity：目标实体名称，来自第1步识别结果
- relationship_description：解释为何这两个实体之间存在关系
- relationship_strength：一个表示该关系强度的数值评分
- relationship_keywords：一个或多个总结该关系本质的关键词，聚焦于概念或主题而非细节
每个关系的格式如下：("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. 识别能总结整段文本核心概念、主题或话题的高层级关键词。
这些关键词应反映文本中存在的主要思想。
其格式如下：("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. 将第1步和第2步中识别出的所有实体和关系作为一个列表返回。列表项之间使用 **{record_delimiter}** 分隔。

5. 结束时，输出 {completion_delimiter}

######################
---示例---
######################
{examples}

#############################
---真实数据---
######################
Entity_types: [{entity_types}]
Text:
{input_text}
######################
Output:"""

PROMPTS["entity_extraction_examples"] = [
    """示例 1：

Entity_types: [人物, 技术, 任务, 组织, 地点]
Text:
```
当 Alex 咬紧牙关时，挫败感的嗡嗡声在 Taylor 的专断式笃定背景下显得微不足道。正是这种潜在的竞争暗流让他保持警觉，他与 Jordan 共同致力于探索的信念，仿佛是一种对 Cruz 狭隘控制与秩序观的无声反叛。

然后 Taylor 做了一件意外的事。他们停在 Jordan 身边，片刻间，以近乎虔诚的神情注视着那台装置。“如果这项技术能被理解……”Taylor 声音放轻，“这将改写我们的游戏规则，对我们所有人。”

先前的轻视似乎动摇，取而代之的是对手中之物分量的一丝不情愿的敬意。Jordan 抬起头，在短暂的瞬间，他们的目光与 Taylor 相遇，一场无言的意志较量缓缓软化为勉强的和解。

这是一个微小的转变，几乎难以察觉，但 Alex 内心默默点头注意到了。他们都是从不同的路径被带到这里的。
```

Output:
("entity"{tuple_delimiter}"Alex"{tuple_delimiter}"人物"{tuple_delimiter}"Alex 是一个经历了挫败感并敏锐观察其他角色之间动态的角色。"){record_delimiter}
("entity"{tuple_delimiter}"Taylor"{tuple_delimiter}"人物"{tuple_delimiter}"Taylor 被描绘为具有专断风格的角色，并在一刻间对某装置流露出敬意，显示其态度发生变化。"){record_delimiter}
("entity"{tuple_delimiter}"Jordan"{tuple_delimiter}"人物"{tuple_delimiter}"Jordan 致力于探索，并与 Taylor 围绕装置有重要互动。"){record_delimiter}
("entity"{tuple_delimiter}"Cruz"{tuple_delimiter}"人物"{tuple_delimiter}"Cruz 与一种控制与秩序的观念相关，对其他角色的互动产生影响。"){record_delimiter}
("entity"{tuple_delimiter}"该装置"{tuple_delimiter}"技术"{tuple_delimiter}"该装置是故事的核心，可能带来重大变革，Taylor 对其表示敬意。"){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Taylor"{tuple_delimiter}"Alex 受到 Taylor 专断风格的影响，并观察到其对装置态度的转变。"{tuple_delimiter}"权力关系, 视角变化"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Jordan"{tuple_delimiter}"Alex 与 Jordan 共享探索的信念，与 Cruz 的理念形成对比。"{tuple_delimiter}"共同目标, 反叛"{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"Jordan"{tuple_delimiter}"Taylor 与 Jordan 围绕装置直接互动，形成一种相互尊重和脆弱的停战。"{tuple_delimiter}"冲突解决, 相互尊重"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Jordan"{tuple_delimiter}"Cruz"{tuple_delimiter}"Jordan 对探索的坚持构成了对 Cruz 控制理念的反叛。"{tuple_delimiter}"意识形态冲突, 反叛"{tuple_delimiter}5){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"该装置"{tuple_delimiter}"Taylor 对该装置流露敬意，表明其重要性和潜在影响。"{tuple_delimiter}"敬意, 技术意义"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"权力关系, 意识形态冲突, 探索, 反叛"){completion_delimiter}
#############################""",

    """示例 2：

Entity_types: [公司, 指数, 商品, 市场趋势, 经济政策, 生物]
Text:
```
今日股市大幅下跌，科技巨头出现明显下滑，全球科技指数在午盘交易中下跌了 3.4%。分析师将此次抛售归因于投资者对利率上升和监管不确定性的担忧。

受打击最严重的是 Nexon Technologies，其股价在财报不及预期后暴跌 7.8%。相比之下，Omega Energy 因油价上涨而小幅上涨 2.1%。

与此同时，大宗商品市场情绪复杂。黄金期货上涨 1.5%，达到每盎司 2080 美元，投资者寻求避险资产。原油价格继续上涨，升至每桶 87.60 美元，受供应限制和强劲需求推动。

金融专家密切关注美联储的下一步举措，市场对可能加息的猜测不断升温。即将发布的政策声明预计将影响投资者信心和整体市场稳定性。
```

Output:
("entity"{tuple_delimiter}"全球科技指数"{tuple_delimiter}"指数"{tuple_delimiter}"全球科技指数追踪主要科技股票的表现，今日下跌了 3.4%。"){record_delimiter}
("entity"{tuple_delimiter}"Nexon Technologies"{tuple_delimiter}"公司"{tuple_delimiter}"Nexon Technologies 是一家科技公司，财报不佳导致股价暴跌 7.8%。"){record_delimiter}
("entity"{tuple_delimiter}"Omega Energy"{tuple_delimiter}"公司"{tuple_delimiter}"Omega Energy 是一家能源公司，因油价上涨而股价上涨 2.1%。"){record_delimiter}
("entity"{tuple_delimiter}"黄金期货"{tuple_delimiter}"商品"{tuple_delimiter}"黄金期货上涨 1.5%，表明投资者对避险资产的需求增加。"){record_delimiter}
("entity"{tuple_delimiter}"原油"{tuple_delimiter}"商品"{tuple_delimiter}"原油价格上涨至每桶 87.60 美元，因供应受限和需求强劲。"){record_delimiter}
("entity"{tuple_delimiter}"市场抛售"{tuple_delimiter}"市场趋势"{tuple_delimiter}"市场抛售指的是股价大幅下跌，由投资者对利率和监管担忧所驱动。"){record_delimiter}
("entity"{tuple_delimiter}"美联储政策声明"{tuple_delimiter}"经济政策"{tuple_delimiter}"美联储即将发布的政策声明预计将影响投资者信心与市场稳定。"){record_delimiter}
("relationship"{tuple_delimiter}"全球科技指数"{tuple_delimiter}"市场抛售"{tuple_delimiter}"全球科技指数下跌属于由投资者担忧引发的整体市场抛售的一部分。"{tuple_delimiter}"市场表现, 投资者情绪"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Nexon Technologies"{tuple_delimiter}"全球科技指数"{tuple_delimiter}"Nexon Technologies 的股价下跌加剧了全球科技指数的整体下滑。"{tuple_delimiter}"公司影响, 指数波动"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"黄金期货"{tuple_delimiter}"市场抛售"{tuple_delimiter}"市场抛售期间，黄金价格上涨，反映投资者寻求避险。"{tuple_delimiter}"市场反应, 避险投资"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"美联储政策声明"{tuple_delimiter}"市场抛售"{tuple_delimiter}"对美联储政策变化的猜测引发市场波动和投资者抛售。"{tuple_delimiter}"利率影响, 金融监管"{tuple_delimiter}7){record_delimiter}
("content_keywords"{tuple_delimiter}"市场下跌, 投资者情绪, 商品, 美联储, 股票表现"){completion_delimiter}
#############################"""

    """示例 3：

Entity_types: [经济政策, 运动员, 赛事, 地点, 纪录, 组织机构, 装备]
Text:
```
在东京举行的世界田径锦标赛上，Noah Carter 使用最先进的碳纤维钉鞋打破了 100 米短跑纪录。
```

Output:
("entity"{tuple_delimiter}"世界田径锦标赛"{tuple_delimiter}"赛事"{tuple_delimiter}"世界田径锦标赛是一项全球性的体育赛事，汇聚了顶尖的田径运动员。"){record_delimiter}
("entity"{tuple_delimiter}"东京"{tuple_delimiter}"地点"{tuple_delimiter}"东京是世界田径锦标赛的举办城市。"){record_delimiter}
("entity"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"运动员"{tuple_delimiter}"Noah Carter 是一名短跑选手，在世界田径锦标赛上打破了 100 米短跑纪录。"){record_delimiter}
("entity"{tuple_delimiter}"100 米短跑纪录"{tuple_delimiter}"纪录"{tuple_delimiter}"100 米短跑纪录是田径项目中的重要基准，最近由 Noah Carter 打破。"){record_delimiter}
("entity"{tuple_delimiter}"碳纤维钉鞋"{tuple_delimiter}"装备"{tuple_delimiter}"碳纤维钉鞋是一种先进的短跑鞋，有助于提升速度和抓地力。"){record_delimiter}
("entity"{tuple_delimiter}"世界田径联合会"{tuple_delimiter}"组织机构"{tuple_delimiter}"世界田径联合会是负责监管世界田径锦标赛及其纪录认证的机构。"){record_delimiter}
("relationship"{tuple_delimiter}"世界田径锦标赛"{tuple_delimiter}"东京"{tuple_delimiter}"世界田径锦标赛在东京举办。"{tuple_delimiter}"赛事地点, 国际比赛"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"100 米短跑纪录"{tuple_delimiter}"Noah Carter 在本次锦标赛上打破了 100 米短跑纪录。"{tuple_delimiter}"运动员成就, 打破纪录"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"碳纤维钉鞋"{tuple_delimiter}"Noah Carter 在比赛中使用碳纤维钉鞋来提升表现。"{tuple_delimiter}"运动装备, 性能提升"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"世界田径联合会"{tuple_delimiter}"100 米短跑纪录"{tuple_delimiter}"世界田径联合会负责认证和认可新的短跑纪录。"{tuple_delimiter}"体育监管, 纪录认证"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"田径, 短跑, 打破纪录, 体育科技, 竞赛"){completion_delimiter}
#############################"""
]

PROMPTS[
    "summarize_entity_descriptions"
] = """你是一个负责生成综合摘要的智能助手。

你将根据下面提供的数据，为一个或两个实体生成一个全面的描述。所有描述都与相同的实体或实体组相关。
请将这些描述合并为一段完整连贯的描述，确保整合所有描述中的信息。
如果描述之间存在矛盾，请进行合理的分析与整合，生成一个统一一致的总结性内容。
请使用第三人称书写，并在摘要中包含实体名称，以便读者获得完整语境。
请使用 {language} 作为输出语言。

#######
---数据---
实体：{entity_name}
描述列表：{description_list}
#######
输出：
"""

PROMPTS["entity_continue_extraction"] = """
上一次抽取过程中遗漏了许多实体和关系。

---请回忆以下步骤---

1. 识别所有实体。对于每一个识别出的实体，提取以下信息：
- entity_name：实体名称，使用与输入文本相同的语言；若为英文，则首字母大写。
- entity_type：实体类型，应为以下类型之一：[{entity_types}]
- entity_description：该实体的属性与活动的全面描述
将每个实体的格式写为：
("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 从第 1 步中识别出的实体中，找出所有 *明显存在关联* 的 (source_entity, target_entity) 对。
对于每对相关实体，提取以下信息：
- source_entity：源实体名称，需与第 1 步中识别出的名称一致
- target_entity：目标实体名称，需与第 1 步中识别出的名称一致
- relationship_description：解释你为什么认为这两个实体之间存在关联
- relationship_strength：一个数值，用于表示这对实体之间关系强度
- relationship_keywords：一个或多个关键词，概括这段关系的主要性质，侧重概念或主题而非具体细节
将每个关系的格式写为：
("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. 提取总结整个文本主要概念、主题或话题的高层次关键词。这些关键词应能反映文档中所表达的核心思想。
将内容级别的关键词格式写为：
("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. 使用 {language} 语言输出所有在步骤 1 和步骤 2 中识别出的实体与关系，合并成一个列表，列表项之间使用 **{record_delimiter}** 进行分隔。

5. 最后输出 {completion_delimiter}

---输出---

请使用相同格式将新增内容写在下面：\\n
""".strip()

PROMPTS["entity_if_loop_extraction"] = """
---目标---

看起来仍有一些实体可能被遗漏了。

---输出---

仅回答 `YES` 或 `NO`，表示是否还有实体需要补充。
""".strip()

PROMPTS["fail_response"] = (
    "抱歉，我无法回答该问题。[no-context]"
)

PROMPTS["rag_response"] = """---角色---

你是一个负责回答用户关于以下知识库问题的有帮助的助手。

---目标---

基于知识库生成简明回答，并遵循回应规则，同时考虑对话历史与当前查询。在回答中总结所提供知识库中的所有信息，并结合与知识库相关的一般知识。不允许添加任何不在知识库中的信息。

处理带时间戳的关系时：
1. 每个关系都有一个 "created_at" 时间戳，表示我们获得这条知识的时间
2. 当关系之间存在冲突时，应同时考虑语义内容和时间戳
3. 不要自动优先选择最新的关系——应根据上下文进行判断
4. 对于时间相关的查询，应优先参考内容中的时间信息，再考虑创建时间戳

---对话历史---
{history}

---知识库---
{context_data}

---回应规则---

- 目标格式和长度：{response_type}
- 使用 markdown 格式，并配合适当的标题
- 请使用与用户提问相同的语言作答
- 确保回答与对话历史保持连贯性
- 最多列出 5 条最重要的参考来源，统一在结尾的 “References” 部分标注。明确指明每条来源来自知识图谱（KG）或向量数据（DC），并包含其文件路径，格式如下：[KG/DC] file_path
- 如果你不知道答案，就坦诚说不知道
- 不要编造信息。不要包含知识库中未提供的内容。"""

PROMPTS["keywords_extraction"] = """---角色---

你是一个有帮助的助手，负责识别用户查询和对话历史中的高层级和低层级关键词。

---目标---

给定用户的查询和对话历史，列出高层级和低层级的关键词。高层级关键词聚焦于总体概念或主题，而低层级关键词关注具体实体、细节或具体术语。

---说明---

- 在提取关键词时，请同时考虑当前查询和相关的对话历史
- 输出应为 JSON 格式，将被 JSON 解析器解析，请不要添加任何额外内容
- JSON 中应包含两个键：
  - "high_level_keywords"：用于表示总体概念或主题的关键词
  - "low_level_keywords"：用于表示具体实体或细节的关键词

######################
---示例---
######################
{examples}

#############################
---真实数据---
######################
对话历史：
{history}

当前查询：{query}
######################
输出应为人类可读文本，不应包含 Unicode 字符。请保持与查询相同的语言。
输出：

"""

PROMPTS["keywords_extraction_examples"] = [
    """示例 1:

查询: "国际贸易如何影响全球经济稳定？"
################
输出:
{
  "high_level_keywords": ["国际贸易", "全球经济稳定", "经济影响"],
  "low_level_keywords": ["贸易协定", "关税", "货币兑换", "进口", "出口"]
}
#############################""",
    """示例 2:

查询: "森林砍伐对生物多样性有哪些环境后果？"
################
输出:
{
  "high_level_keywords": ["环境后果", "森林砍伐", "生物多样性丧失"],
  "low_level_keywords": ["物种灭绝", "栖息地破坏", "碳排放", "热带雨林", "生态系统"]
}
#############################""",
    """示例 3:

查询: "教育在减贫中扮演什么角色？"
################
输出:
{
  "high_level_keywords": ["教育", "减贫", "社会经济发展"],
  "low_level_keywords": ["上学机会", "识字率", "职业培训", "收入不平等"]
}
#############################""",
]

PROMPTS["naive_rag_response"] = """---角色---

你是一个负责回答用户关于下方提供的文档片段（Document Chunks）问题的智能助手。

---目标---

基于文档片段生成简洁的回答，并遵循回应规则，综合考虑对话历史和当前查询。总结文档片段中提供的全部信息，并结合与文档片段相关的一般知识。不允许加入文档片段中未提供的信息。

处理带有时间戳的内容时请注意：
1. 每条内容都包含一个 "created_at" 时间戳，表示我们获取该信息的时间；
2. 当遇到相互冲突的信息时，需同时考虑内容本身和其时间戳；
3. 不要盲目偏向时间较新的内容——应根据上下文做出判断；
4. 对于与时间相关的问题，优先依据内容中的时间信息，而非创建时间戳。

---对话历史---
{history}
a
---文档片段---
{content_data}

---回应规则---

- 回答的格式与长度需符合：{response_type}
- 使用 Markdown 格式，并添加适当的章节标题；
- 回答应与用户问题使用相同语言；
- 确保回应与对话历史保持连贯；
- 最多列出 5 个最重要的参考来源，置于 “参考资料（References）” 部分。明确标注每个来源属于知识图谱（KG）还是向量数据（DC），并附带文件路径，格式如下：[KG/DC] file_path；
- 如果你不知道答案，请直接说明；
- 不要编造信息。不要包含文档片段中未提供的内容。"""

PROMPTS[
    "similarity_check"
] = """请分析以下两个问题之间的相似度：

问题 1: {original_prompt}
问题 2: {cached_prompt}

请评估这两个问题在语义上是否相似，以及问题 2 的答案是否可以用于回答问题 1，并直接提供一个 0 到 1 之间的相似度得分。

相似度评分标准：
0：完全不相关，或答案无法复用，包括但不限于以下情况：
   - 两个问题涉及不同主题
   - 问题中提到的地点不同
   - 问题中提到的时间不同
   - 问题中涉及的具体人物不同
   - 问题中涉及的具体事件不同
   - 背景信息不同
   - 问题的关键条件不同
1：完全相同，答案可以直接复用
0.5：部分相关，答案需修改后才能使用

仅返回一个介于 0 到 1 之间的数字，不要添加任何额外内容。
"""

PROMPTS["mix_rag_response"] = """---角色---

你是一个负责回答用户关于下方数据源问题的智能助手。

---目标---

请基于下方提供的数据源生成简洁的回答，并遵循回答规则，考虑对话历史与当前问题。数据源包含两个部分：知识图谱（Knowledge Graph，KG）和文档片段（Document Chunks，DC）。请总结数据源中所有信息，并结合相关的常识进行回答。不要包含数据源中未提供的信息。

处理带有时间戳的信息时：
1. 每条信息（无论是关系还是内容）都包含一个 "created_at" 时间戳，表示我们获取该知识的时间。
2. 当出现信息冲突时，应同时考虑内容/关系和时间戳。
3. 不要默认最近的时间戳信息更准确 —— 应根据上下文进行判断。
4. 针对时间相关的问题，优先考虑内容中提供的时间信息，而不是时间戳。

---对话历史---
{history}

---数据源---

1. 来自知识图谱（KG）：
{kg_context}

2. 来自文档片段（DC）：
{vector_context}

---回答规则---

- 目标格式与长度：{response_type}
- 使用 Markdown 格式，包含合适的小节标题
- 请使用用户提问所用的语言进行回答
- 确保回答与对话历史保持连贯
- 将回答内容组织为多个小节，每个小节聚焦一个主要点
- 使用清晰且具有描述性的小节标题，准确反映内容
- 在“参考文献”部分列出最多 5 条最重要的引用来源。需明确指出每条来源是来自知识图谱（KG）还是文档片段（DC），并附上文件路径，格式如下：[KG/DC] file_path
- 如果你不知道答案，就直接说明
- 不要编造内容，也不要包含数据源中未提供的信息
"""