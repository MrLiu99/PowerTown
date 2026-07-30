
# Generative Agents 电力小镇

## 1. 准备工作

### 1.1 获取代码

### 1.2 配置大语言模型（LLM）

修改配置文件 `generative_agents/data/config.json`：

1. 默认使用 [Ollama](https://ollama.com/) 加载本地量化模型，并提供 OpenAI 兼容 API。需要先拉取量化模型（参考 [Ollama 配置说明](docs/ollama.md)），并确保 `base_url` 和 `model` 与 Ollama 中的配置一致。
2. 如果希望调用其他 OpenAI 兼容 API，需要将 `provider` 改为 `openai`，并根据 API 文档配置 `model`、`api_key` 和 `base_url`。

如需使用 Hugging Face 国内镜像，可在 Windows 命令提示符中执行：

```bat
set HF_ENDPOINT=https://hf-mirror.com
```

### 1.3 安装 Python 依赖

建议先使用 Anaconda 创建并激活虚拟环境：

```bash
conda create -n generative_agents_cn python=3.12
conda activate generative_agents_cn
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 2. 运行虚拟小镇

进入程序目录：

```bash
cd generative_agents
```

创建一个新模拟：

```bash
python start.py --name sim-test --start "20251105-09:30" --step 10 --stride 10
```

开启电力模块：

```bash
python start.py --name power-test --start "20251105-09:30" --step 10 --stride 60 --power on
```

关闭电力模块，只运行基础小镇：

```bash
python start.py --name basic-test --start "20251105-09:30" --step 10 --stride 60 --power off
```

从已有模拟的最近检查点继续运行：

```bash
python start.py --name sim-test --resume --step 10 --stride 10
```

参数说明：

- `--name`：模拟名称。新建模拟时不能与已有模拟重名；恢复模拟时必须填写已有名称。
- `--start`：新模拟的起始时间，格式为 `YYYYMMDD-HH:MM`，默认值为 `20240213-09:30`。
- `--resume`：布尔开关，不接收日期或其他值。启用后从指定模拟的最近检查点继续运行。
- `--step`：本次运行的迭代步数，默认值为 `10`。
- `--stride`：每一步对应的模拟时间（分钟），默认值为 `10`。例如设置为 `10`，模拟时间将依次变为 09:00、09:10、09:20。
- `--power`：是否启用电力模块，可选值为 `on` 或 `off`，默认值为 `on`。该参数只在创建新模拟时生效。
- `--verbose`：日志级别，默认值为 `debug`。
- `--log`：日志文件名；默认不指定，日志将输出到控制台。

恢复运行时，起始时间和电力模块状态从检查点读取，因此无需再次传入 `--start` 或 `--power`。本次运行仍会使用命令行中的 `--stride` 推进模拟时间，建议显式传入与原模拟相同的值。

## 3. 回放

### 3.1 生成回放数据

```bash
python compress.py --name power-town-test3
```

运行结束后，将在 `results/compressed/<simulation-name>` 目录下生成回放数据文件 `movement.json`，同时生成 `simulation.md`，以时间线方式呈现每个智能体的状态及对话内容。

### 3.2 启动回放服务

```bash
python replay.py
```

通过浏览器打开以下地址，可以看到虚拟小镇居民在各个时间段的活动：

`http://127.0.0.1:5000/?name=power-town-test3`

可通过方向键移动画面。回放参数通过 URL 查询参数传递：

- `name`：启动虚拟小镇时设定的模拟名称。
- `step`：回放的起始步数，`0` 表示从第一帧开始，默认值为 `0`。
- `speed`：回放速度，可选范围为 `0`～`5`，`0` 最慢，`5` 最快，默认值为 `2`。
- `zoom`：画面缩放比例，默认值为 `0.8`。

发布版本中内置了名为 `example` 的回放数据（由 `qwen2.5:32b-instruct-q4_K_M` 生成）。以下 URL 表示从头开始、回放速度为 `2`、画面缩放比例为 `0.6`：

`http://127.0.0.1:5000/?name=example&step=0&speed=2&zoom=0.6`

也可直接打开 [simulation.md](generative_agents/results/compressed/example/simulation.md)，查看 `example` 中所有人物活动和对话信息。

## 4. 修改地图

由于 wounderland 项目原作者没有提供 `maze.json` 的生成代码，创建新地图可采用以下方案：

1. 参考原始 Generative Agents 项目中 `maze.py` 的逻辑，修改现有代码，使其兼容 Tiled 编辑器导出的 JSON 和 CSV 数据。
2. 参考现有的 `maze.json` 格式，编写代码合并 Tiled 编辑器导出的 `maze_meta_info.json`、`collision_maze.csv` 和 `sector_maze.csv` 等文件。
3. 使用 [tiled_to_maze.json](https://github.com/jiejieje/tiled_to_maze.json) 地图标注工具。

## 5. 参考资料

[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

[Generative Agents](https://github.com/joonspk-research/generative_agents)

[wounderland](https://github.com/Archermmt/wounderland)
