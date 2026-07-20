# 题材索引

读取项目 `settings/genre-setting.md` 的 `genre_id`，再读取对应文件。细分题材文件
会声明父题材；使用时先读父题材，再叠加差异。题材知识只改变读者期待、节奏、
世界逻辑和表达选择，不替作者决定剧情。

## 题材注册表

| genre_id | 中文名 | parent |
|---|---|---|
| `xianxia` | 东方仙侠 | - |
| `xuanhuan` | 东方玄幻 | - |
| `xuanhuan-brained` | 玄幻脑洞 | `xuanhuan` |
| `urban` | 都市 | - |
| `urban-daily` | 都市日常 | `urban` |
| `urban-romance` | 都市甜宠 | `urban` |
| `urban-farming` | 都市种田 | `urban` |
| `urban-brained` | 都市脑洞 | `urban` |
| `urban-cultivation` | 都市修真 | `urban-brained` |
| `urban-high-martial` | 都市高武 | `urban-brained` |
| `suspense-crime` | 悬疑犯罪 | - |
| `suspense-paranormal` | 悬疑灵异 | `suspense-crime` |
| `suspense-brained` | 悬疑脑洞 | `suspense-crime` |
| `historical` | 历史 | - |
| `historical-brained` | 历史脑洞 | `historical` |
| `ancient-politics` | 古代权谋 | `historical` |
| `anti-japanese-war` | 抗战谍战 | `historical` |
| `scifi-apocalypse` | 科幻末世 | - |
| `western-fantasy` | 西方奇幻 | - |
| `war-god` | 战神归来 | `urban` |
| `derivative` | 同人衍生 | - |
| `anime-derivative` | 动漫衍生 | `derivative` |
| `male-derivative` | 男频衍生 | `derivative` |
| `game-sports` | 游戏体育 | - |

未注册题材：选择最接近的主类型作为临时参考，并由作者确认真正的读者期待和
禁忌；不要伪装成已有精确规则。

题材画像只给期待、约束和差异，不给固定章型或情节案例。planner 必须从当前人物、
卷目标和资源关系推导事件，不能把题材文件当桥段库。

连载向项目默认叠加 `knowledge/webnovel/fanqie-baseline.md`（与具体 genre_id
正交，不是新的题材编号）。题材画像只改读者期待、节奏、世界逻辑与表达选择，
不替作者决定剧情，不做字段门禁。
