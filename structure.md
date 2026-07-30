***  1. 环境 ***
 fronted
    static
        assets
            agents
                ***用于定义不同智能体的角色背景以及个性特征，以及定义其行为空间认知。例如，当前*在家，*知道的地点包括..，下面想去什么地方**
                ... **目前共25个agent**
                ***
                sprite.json **智能体在小镇中移动时的动画效果设置**
            equipment
                ***用于定义不同智能体的设备**
            tilemap
            maze.json
        css
        libs
    templates  **前端界面代码**
        base.html
        index.html  **回放展示界面**
        main_script.html  **主要界面，包含前端的各类元素代码编写**

***  2.prompt ***
data
    prompts
        base_desc.txt **基础个人信息描述，以及当前时间及状态**
        decide_chat_terminate.txt **根据<对话记录>和<判断逻辑>分析，${agent} 和 ${another} 的对话是否已经告一段落**
        decide_chat.txt **根据上述背景判断，${agent} 是否有可能主动与 ${another} 对话**
        decide_wait.txt **现在是什么时间，目前状态是...，从给定选项中给出下一步动作**
        decide_wait_example.txt
        describe_emoji.txt **将动作转换为表情符**
        describe_event.txt **将输入内容转换为主谓宾结构**
        describe_object.txt **用短句描述某人身边物品的状态**
        determine_arena.txt **在区域选项中，为当前任务选择一个合适的区域**
        determine_object.txt **从选项列表中，为当前活动选择最相关的对象**
        determine_sector.txt **在区域选项中，为当前任务选择一个合适的区域**
        generate_chat.txt **基于状态和对话记录，生成对话内容**
        generate_chat_check_repeat.txt **判断新对话是否出现过**
        poignancy_chat.txt **对 对话 进行打分**
        poignancy_event.txt **对事件进行打分**
        reflect_chat_memory.txt  **描述对话中最有趣的地方**
        reflect_chat_planing.txt **根据对话记录确定agent是否需要记住自己的计划**
        reflect_focus.txt **基于参考信息，给出高质量的高级问题**
        reflect_insights.txt **基于参考信息，汇总高端简洁，并说明其参考信息序号**
        retrieve_currently.txt **描述现在的状态**
        retrieve_plan.txt **制定某天的计划时需要记住什么**
        retrieve_thought.txt **总结当前agent的想法和感受**
        schudule_daily.txt **生成当天每个小时计划**
        schudule_decompose.txt **将计划进行分解**
        schudule_init.txt **输出今日的大致计划**
        schudule_revise.txt **如果原计划发生错乱，需要重新制定剩下的计划**
        summarize_chats.txt **总结对话**
        summarize_relation.txt **总结agent与其他人的关系**
        wake_up.txt **输出起床时间**
        select_appliances_for_activity.txt **根据当前活动，选择最相关的设备（有一个2开头的，两个一个是涉及到分时电价的，一个是不涉及的）**
    config.json **LLM api 设置**

*** 3.功能模块 ***
modules
    memory
        action.py **定义了智能体的行动(Action)类,是GenerativeAgents项目中记录和管理智能体行为的核心数据结构**
        associate.py **定义concept类（代表agent记忆中的一个记忆片段）和associate类（管理agent的全部记忆，提供存储和检索功能）**
        event.py  **定义了Event类,表示"事件"的基础数据结构。它用主谓宾结构来描述智能体的所有行为和观察**
        schedule.py **定义了Schedule类,用于管理智能体的每日日程安排，是控制智能体时间行为的核心模块**
        spatial.py **定义了Spatial类,用于管理智能体的空间认知和地理知识，是处理"地点"的核心模块。**
    model
        llm_model.py **轻量级、可扩展的LLM统一调用库，专为generative agents设计。它把 OpenAI 官方接口 与 本地 Ollama 服务 封装成同一套 API，并附带简单统计、容错、输出解析等常用功能，方便上层业务“即插即用”。**
    power
        agent_power.py **智能体用电行为集成模块**
        consumption.py **用电量计算和跟踪模块**
        equipment.py **用电设备管理模块**
        predictor.py **电力预测模块**
    prompt
        scratch.py **是提示词(Prompt)管理系统,负责构建所有与LLM交互的提示词。这是整个项目的"大脑接口",连接智能体的行为逻辑和语言模型。**
    storage
        index.py **是向量数据库封装,用于实现智能体的长期记忆存储和检索。它基于LlamaIndex框架,提供了向量化存储、语义检索等功能**
    utils
        arguments.py **是GenerativeAgents项目的字典工具库,提供了一系列操作字典(dict)的实用函数,用于配置管理、数据持久化和调试输出**
        log.py
        namespace.py
        timer.py
    init.py
    agent.py
    game.py
    maze.py