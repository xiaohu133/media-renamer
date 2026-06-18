# media-renamer

用于管理主路由 `115open/最近接收` 里的影视文件，按**固定硬规则**自动重命名。

## 设计目标

- 严格参考你库里已经规范好的同类文件
- 目录结构和重命名优先按同类样本继承
- 新文件一加入就自动处理
- 先等待文件稳定，避免下载/复制未完成时误改
- 默认安全：自动模式先用 dry-run 验证

## 当前能力

### 0. 中文优先规则
如果配置里存在可靠中文映射，则优先使用中文名；没有映射时保留原名。
另外，如果视频文件名本身没有中文名，会优先参考上级文件夹中的中文标题。
映射文件：`config/title_mappings.yaml`


### 1. 固定命名规则
程序不再依赖复杂样本推断，而是按硬规则执行：

- 电影：`标题 (年份)/标题.年份.ext`
- 剧集：`标题 (年份)/标题.年份.SxxExx.ext`
- 不保留 `Season` 子目录
- 根目录不能有裸视频文件
- 字幕必须和对应视频同基名
- 目录名和文件名标题必须一致
- 只识别视频文件名，不拿文件夹名做英文主识别
- 视频文件名优先识别 `19xx`、`20xx` 作为年份边界；若没有年份且存在 `SxxExx`，则改用 `SxxExx` 作为片名边界，年份取上级目录中的年份
- 如果边界前存在英文标题，则只提取英文部分走 TMDB，并优先改成中文
- 如果视频文件名本身已有中文，则不走 TMDB
- 如果年份和 `SxxExx` 都没有，则参考当前目录下其他剧集视频的命名样式，除当前文件的集数外其余部分尽量照搬（包括季号）；集数取该文件名中已有数字
- 如果 TMDB 没结果，再回退到中文目录名或净化后文件名

### 2. 自动模式
支持常驻 watch：

- 定时扫描新文件
- 判断文件大小/修改时间是否稳定
- 稳定后再生成重命名计划
- 可选择 dry-run 或自动 apply

### 3. 文件类型
- 视频：`.mkv` `.mp4` `.ts`
- 字幕：`.srt` `.ass` `.ssa` `.sup` `.sub`
- ISO：`.iso`

## 命令

### 只看计划
```bash
docker compose run --rm media-renamer plan --recent-hours 24
```

### 单次扫描（预演）
```bash
docker compose run --rm media-renamer scan --recent-hours 24 --dry-run
```

### 单次扫描（正式执行）
```bash
docker compose run --rm media-renamer scan --recent-hours 24 --apply
```

### 常驻自动监听（预演）
```bash
docker compose up -d
```

默认 `compose.yaml` 现在运行的是：

```bash
watch --interval 60 --stable-seconds 120 --apply
```

也就是：
- 每 60 秒检查一次
- 文件稳定 120 秒后才考虑处理
- 默认会 **自动正式改名**

### 如果你想先切回预演模式
把 `compose.yaml` 里的：

```yaml
command: ["watch", "--interval", "60", "--stable-seconds", "120", "--apply"]
```

改成：

```yaml
command: ["watch", "--interval", "60", "--stable-seconds", "120", "--dry-run"]
```

然后启动：

```bash
docker compose up -d
```

## 配置

默认挂载：

- 主机：`/mnt/CloudNAS/115open/最近接收` → 容器：`/media/最近接收`
- 主机：`/mnt/sata2-3/影视` → 容器：`/media/影视`

如果主路由真实路径不同，请改：

- `compose.yaml`
- `config/config.yaml`

## 状态与日志

- 状态：`data/state.json`
- 日志：`data/logs/actions.log`

## 推荐上线步骤

1. `docker compose build`
2. `docker compose run --rm media-renamer plan --recent-hours 24`
3. `docker compose run --rm media-renamer scan --recent-hours 24 --dry-run`
4. `docker compose up -d`
5. 观察日志确认行为符合预期

## 当前限制

- 第一版仍不接 TMDB / 豆瓣
- 不自动猜中文译名
- 主要依赖文件名和现有样本做规范化
- 对无法可靠识别标题/年份的文件会跳过
