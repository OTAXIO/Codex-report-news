# GitHub 上传能力核查（2026-10-26）

当前已按用户授权独立实现 codex-upload 并接入制作流程，使用专用 Chrome、字段读回和真实提交回执，不运行参考网页 skill 的人工提交守卫。最新操作以 CODEX_UPLOAD.md 为准；以下保留原调研与其当时的能力边界。

核查方式：GitHub 插件搜索与直接读取上游 README、SKILL、CLI 契约和投稿结构源码。未调用账号 Cookie，未安装后直接发稿，未重复上传今天的视频。

| 仓库 | 已核查能力 | 与本项目的缺口/结论 |
|---|---|---|
| [biliup/biliup](https://github.com/biliup/biliup) | 主仓库有 SKILL.md，CLI 有 login、upload、append、show、list、season；支持 Windows，投稿结构有 copyright、tid、cover、tag、desc、extra_fields | 能做程序化上传，但尚未在本账号实测 AI＋原创多选、双比例封面、News 合集与活动字段。README 有个人学习及禁止商业用途说明，不直接当作创作激励场景的无条件推荐。默认不启用自动投稿 |
| [biliup/biliup-rs](https://github.com/biliup/biliup-rs) | 历史 Rust 上传 CLI | 仓库已归档；研究入口应转当前主仓库，不安装旧版冒充最新 |
| [grapeot/bilibili-upload-skill](https://github.com/grapeot/bilibili-upload-skill) | MIT；可见 Chrome＋独立 profile，Playwright 填视频、双封面、标题、分区、标签、声明等；dry-run、读回校验 | 明确只填到提交前，最终由人点击；元数据只展示单个 creation_statement，需额外核对原创多选、活动与 News。上游也说明从选文件开始的完整流程尚无一次全跑通；不能保证开箱即用。作为辅助填表候选，不当作全自动发布 |
| [haoxiangdong/social-auto-upload](https://github.com/haoxiangdong/social-auto-upload) 的 bilibili-upload skill | sau bilibili login/check/upload-video；自动准备 biliup，登录由用户本地扫码 | 公布的契约只有 file/title/desc/tid/tags/schedule，未涵盖本项目全部双封面和声明要求；因此不选为默认执行器 |
| [Lucas-Qh-Lai/bilibili-publish](https://github.com/Lucas-Qh-Lai/bilibili-publish) | 文档声称使用网页上传 API、CDP 登录态和发布验证 | 不采用通过 CDP 提取登录凭据的路线；Windows 实测也未明确，不能将其视作可靠通用方案 |

## 原调研决策（独立实现前的历史快照）

技术上存在上传 CLI/skill；“存在工具”不等于“本账号与全部字段已经验证”。当前保留人工或现有浏览器协助投稿，Codex 继续负责制作和协助发布；受限时用户从 release 手动上传。

已实现 `uploader_plan.py`：只接受 release 下未发布的目录，核对视频 SHA-256，产出供网页填表 skill 使用的 JSON 与必查清单，**不联网、不读登录态、不提交**。今天的已发布包会被拒绝，防止重复投稿。

若以后接入网页 skill，先安装到独立环境、阅读上游许可/限制，打开它自己的可见 Chrome 让用户扫码。只有用户授权的具体视频才能执行填表；不得连接日常浏览器窃取 Cookie，不得绕过其最终提交守卫。若选 biliup CLI，先在本地独立账号配置中扫码，再校验字段；不在交接包中放登录文件。

News 需求目前仅被记录。今天实际页面只有科技数码一级分区及“加入合集”入口，没有核对到独立 News 分类字段；下次应检查账号是否存在 News 合集，不能将添加一个 News 标签冒充设置稿件分类。

## 固定核查快照

- biliup 主仓库读取时 HEAD：`48a0d234794bb918e211076b357823438e8c109d`，提交时间 2026-10-26T02:31:23Z。
- grapeot/bilibili-upload-skill HEAD：`ec701c14342c626f79dac106016444e50e7b9507`，提交时间 2026-10-23T17:37:20Z。
- [biliup 主 skill](https://github.com/biliup/biliup/blob/48a0d234794bb918e211076b357823438e8c109d/SKILL.md)
- [biliup 投稿结构](https://github.com/biliup/biliup/blob/48a0d234794bb918e211076b357823438e8c109d/crates/biliup/src/uploader/bilibili.rs)
- [网页填表 skill](https://github.com/grapeot/bilibili-upload-skill/blob/ec701c14342c626f79dac106016444e50e7b9507/skills/bilibili-upload/SKILL.md)
- [sau Bilibili CLI 契约](https://github.com/haoxiangdong/social-auto-upload/blob/main/skills/bilibili-upload/references/cli-contract.md)

上述是当日源码核查，不是未来可用性保证；实际接入前刷新版本与字段。
