# v5执行说明

原论文、v4结果、原始栅格均不覆盖。新目录只用于本轮消融。

执行顺序：prepare → calibrate → extract → predict → evaluate → audit.py → report.py。

固定Python：E:\anconda\envs\py310\python.exe；所有运行使用-B防止在旧代码目录生成pycache。

ablation.py复用v4只读engine.py中的数据、面积和得分面实现。原60开发窗和原40探索窗复用v4已有充分统计；新63窗从原始四栅格重新读取并计算。复用整数平移缓存是代数等价计算，不改变搜索集合，也不读取旧成绩来调整新参数。

ablation_frozen.json在新匹配表现计算前保存方案、代码、样区和原矩阵哈希。calibrated_parameters.json只用原60开发窗生成；parameters_locked.json保存其时间和哈希。locked_predictions.csv在evaluate之前写出并锁定。

frozen_parameters.json是复用载入器所需的v4输入路径／格网配置快照；本轮四组消融与统计规则以ablation_frozen.json及PROTOCOL.md为准，不沿用v4选择器的成功标准。

新样区按原候选表的覆盖、组成、分区和中心距离筛选；用户已明确同意低SL占比外推用途。共有63窗、14新分区；不能把它们与原40窗合并作总体推断。全部符合条件的窗口均进入，不按收益筛样。

输出对相同窗口／年份／最终像元偏移无损去重，由raster_manifest.csv链接到各候选、情景和参数制度。共用同一文件不意味着该策略免费获得额外信息，不用于存储成本优势声明。

若需重新执行，请复制代码与冻结记录到新目录，不直接覆盖本次输出。历史日志与异常应完整保存。
