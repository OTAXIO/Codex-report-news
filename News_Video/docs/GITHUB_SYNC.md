# GitHub同步范围与验证（2026-10-27）

当前维护三份仓库：OTAXIO/Codex-report-news（制作、规则、手册及生产skill快照）、OTAXIO/Voice_Generate（语音入口与规则）、OTAXIO/codex-upload-video（独立投稿skill权威源码）。用户已明确授权同步全部项目更新，包括skill。

新闻仓库此前整体忽略docs/skills，现改为版本化维护的Markdown手册与skill文本/代码；诊断报告、状态数据库、采集日志、成品、交接ZIP、参考音频、模型、字体、账号和浏览器认证均不入Git。工作区入口/DSH提示词在workspace-context保留快照，路径仍相对工作区根目录。

本次推送前在现有科学Python环境完成新闻105项、语音22项、投稿核心11项回归。上传器源码、生产快照、已安装skill逐文件一致，指纹50e849b331e833d2b713516624f4b9e81fc6e54f5daff1ba2d8dac1d5c26ab99。Chrome表单5项测试全部通过、无跳过，使用未登录本地fixture并拦截网络，不能当成新的真实平台投稿。脚本化扫描待提交文件未发现匹配的凭据模式或大于5MB文件；这不是完整安全审计声明。

推送使用现有main分支、普通fast-forward，不强推；推送后以远端分支提交ID与本地HEAD相等为验收。真实远端提交信息以Git历史和实际推送回执为准，不能由本文预先声明成功。此次同步不生成、不编辑或上传B站视频，不修改模型和登录状态。
